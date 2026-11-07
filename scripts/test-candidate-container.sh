#!/bin/sh
set -eu
image=${1:-debian:12}
framework=${2:?Pass framework .deb path}
daemon=${3:?Pass candidate .deb path}
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
docker run --rm -v "$root:/work:ro" -w /work "$image" sh -ec '
 export DEBIAN_FRONTEND=noninteractive
 apt-get update
 apt-get install -y "$1" "$2"
 sha256sum /usr/sbin/usbmuxd > /tmp/stock.sha256
 mkdir -p /var/lib/lockdown
 printf fixture > /var/lib/lockdown/candidate-lifecycle-fixture
 python3 tests/integration/candidate.py
 apt-get install -y --reinstall "$2"
 dpkg-deb -R "$2" /tmp/upgrade
 sed -i "/^Version:/s/$/+test1/" /tmp/upgrade/DEBIAN/control
 dpkg-deb --root-owner-group --build /tmp/upgrade /tmp/candidate-upgrade.deb
 apt-get install -y /tmp/candidate-upgrade.deb
 apt-get remove -y ios-usbmuxd-compat-daemon
 dpkg --purge ios-usbmuxd-compat-daemon
 sha256sum -c /tmp/stock.sha256
 test -f /var/lib/lockdown/candidate-lifecycle-fixture
 test ! -e /etc/systemd/system/usbmuxd.service.d/50-ios-usbmuxd-compat.conf
 echo "PASS: candidate reinstall, upgrade, remove and purge preserve stock daemon and pairing records."
' sh "/work/$framework" "/work/$daemon"
