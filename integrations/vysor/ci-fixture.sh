#!/bin/sh
# Synthetic Vysor package for public CI. No vendor assets or hardware claims.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
fixture=$(mktemp -d)
trap 'rm -rf "$fixture"' EXIT HUP INT TERM
mkdir -p "$fixture/DEBIAN" "$fixture/opt/Vysor" "$fixture/usr/share/applications"
cat > "$fixture/DEBIAN/control" <<CONTROL
Package: vysor
Version: 5.0.7
Architecture: $(dpkg --print-architecture)
Maintainer: Test Fixture <test@example.invalid>
Description: Synthetic Vysor layout for installer testing only
CONTROL
printf '#!/bin/sh\nexit 0\n' > "$fixture/opt/Vysor/vysorapp"
chmod +x "$fixture/opt/Vysor/vysorapp"
printf '[Desktop Entry]\nName=Vysor Fixture\nType=Application\nExec=/opt/Vysor/vysorapp\n' > "$fixture/usr/share/applications/vysorapp.desktop"
mkdir -p "$root/dist"
dpkg-deb --root-owner-group --build "$fixture" "$root/dist/vysor-fixture.deb"
python3 "$root/integrations/vysor/build-installer.py" \
 --vysor "$root/dist/vysor-fixture.deb" --framework "$1" --output "$root/dist/vysor-fixture-installer"
"$root/integrations/vysor/test-installer.sh" "$root/dist/vysor-fixture-installer" "${2:-debian:12}"
