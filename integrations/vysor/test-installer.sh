#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
bundle=${1:?Usage: test-installer.sh BUNDLE_DIRECTORY [IMAGE]}
bundle=$(CDPATH= cd -- "$bundle" && pwd)
image=${2:-debian:12}
case "$image" in debian:12|debian:13|ubuntu:22.04|ubuntu:24.04|ubuntu:26.04) ;; *) exit 2;; esac
docker run --rm -v "$bundle:/bundle:ro" -v "$root/integrations/vysor:/tests:ro" "$image" sh -ec '
 export DEBIAN_FRONTEND=noninteractive
 apt-get update
 apt-get install -y file
 sh /bundle/install.sh
 test "$(dpkg-divert --listpackage /usr/share/applications/vysorapp.desktop)" = vysor-usb-compat
 grep -q "Exec=/usr/bin/vysor-usb" /usr/share/applications/vysorapp.desktop
 grep -q "Exec=/opt/Vysor/vysorapp" /usr/share/applications/vysorapp.desktop.distrib
 test ! -e /etc/systemd/system/usbmuxd.service.d/50-ios-usbmuxd-compat.conf
 /usr/bin/ios-usbmuxd-compat check --json > /tmp/report.json
 python3 -c '\''import json; assert json.load(open("/tmp/report.json"))["status"] == "pending_device"'\''
 mkdir /tmp/vendor
 dpkg-deb -x /bundle/vysor.deb /tmp/vendor
 cmp /tmp/vendor/opt/Vysor/vysorapp /opt/Vysor/vysorapp
 if file /opt/Vysor/vysorapp 2>/dev/null | grep -q ELF; then
  ldd /opt/Vysor/vysorapp > /tmp/vysor-libraries
  if grep "not found" /tmp/vysor-libraries; then exit 1; fi
 fi
 sh /bundle/install.sh
 apt-get install -y --reinstall /bundle/integration.deb
 dpkg-deb -R /bundle/integration.deb /tmp/upgrade
 sed -i "s/^Version: .*/Version: 0.1.1/" /tmp/upgrade/DEBIAN/control
 dpkg-deb --root-owner-group --build /tmp/upgrade /tmp/upgrade.deb
 apt-get install -y /tmp/upgrade.deb
 mkdir -p /var/lib/lockdown
 printf fixture > /var/lib/lockdown/vysor-installer-fixture
 apt-get remove -y vysor-usb-compat
 cmp /tmp/vendor/usr/share/applications/vysorapp.desktop /usr/share/applications/vysorapp.desktop
 test -z "$(dpkg-divert --listpackage /usr/share/applications/vysorapp.desktop)"
 dpkg --purge vysor-usb-compat
 test -f /var/lib/lockdown/vysor-installer-fixture
 # Reject an administrator-owned diversion without changing it.
 dpkg-divert --local --add --rename --divert /usr/share/applications/vysorapp.desktop.admin /usr/share/applications/vysorapp.desktop
 if dpkg -i /bundle/integration.deb; then echo "Unexpected override of admin diversion"; exit 1; fi
 test "$(dpkg-divert --listpackage /usr/share/applications/vysorapp.desktop)" = LOCAL
 cmp /tmp/vendor/usr/share/applications/vysorapp.desktop /usr/share/applications/vysorapp.desktop.admin
 echo "PASS: actual Vysor install/reinstall/upgrade/remove/purge; original executable/desktop/pairing preserved; admin diversion rejected. GUI and iPhone untested."
'
