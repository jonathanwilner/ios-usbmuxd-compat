#!/bin/sh
set -eu
image=${1:-debian:12}
case "$image" in debian:12|debian:13|ubuntu:22.04|ubuntu:24.04|ubuntu:26.04) ;; *) echo 'Unsupported test image' >&2; exit 2;; esac
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
out="$root/dist/$(printf %s "$image" | tr : -)"
mkdir -p "$out"
docker run --rm -v "$root:/source:ro" -v "$out:/artifacts" "$image" sh -ec '
 export DEBIAN_FRONTEND=noninteractive
 apt-get update
 apt-get install -y --no-install-recommends build-essential debhelper dh-python python3-all python3-setuptools python3-wheel python3-jsonschema pybuild-plugin-pyproject
 cp -a /source /work
 cd /work
 rm -rf dist
 ./scripts/build-deb.sh
 cp dist/*.deb dist/*.buildinfo dist/*.changes dist/SHA256SUMS /artifacts/
 dpkg-query -W > /artifacts/BUILD_PACKAGES
 apt-get install -y ./dist/ios-usbmuxd-compat_*.deb ./dist/iphone-connectivity-demo_*.deb
 python3 tests/integration/lifecycle.py
 # Reinstall exercises idempotent configure, then a distinct version exercises upgrade.
 apt-get install -y --reinstall ./dist/ios-usbmuxd-compat_*.deb ./dist/iphone-connectivity-demo_*.deb
 sed -i "1s/(0.1.0)/(0.1.1)/" packaging/debian/changelog
 rm -rf dist
 ./scripts/build-deb.sh
 apt-get install -y ./dist/ios-usbmuxd-compat_*.deb ./dist/iphone-connectivity-demo_*.deb
 mkdir -p /var/lib/lockdown
 printf fixture > /var/lib/lockdown/compat-lifecycle-fixture
 apt-get remove -y iphone-connectivity-demo ios-usbmuxd-compat
 test -f /var/lib/lockdown/compat-lifecycle-fixture
 dpkg --purge iphone-connectivity-demo ios-usbmuxd-compat
 test -f /var/lib/lockdown/compat-lifecycle-fixture
 test ! -e /etc/systemd/system/usbmuxd.service.d/50-ios-usbmuxd-compat.conf
 printf "LIFECYCLE PASS: build install reinstall upgrade remove purge; no systemd or hardware acceptance\n" | tee /artifacts/TEST_RESULT
'

docker image inspect "$image" --format '{{json .RepoDigests}}' > "$out/BUILD_IMAGE"
