#!/bin/sh
set -eu
# Optional upstream baseline, deliberately NOT an approved repair.
# Run inside a native Debian/Ubuntu build environment with the documented deps.
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT HUP INT TERM
python3 - "$root" "$build" <<'PY'
import hashlib, json, pathlib, sys, urllib.request
root, build = map(pathlib.Path, sys.argv[1:])
lock = json.loads((root/'packaging/daemon/source.json').read_text())
assert lock['patches'] == [], 'Review and implement a pinned patch recipe before changing patch list'
assert lock['validated'] is False, 'Building source cannot confer hardware validation'
data = urllib.request.urlopen(lock['url'], timeout=60).read()
assert hashlib.sha256(data).hexdigest() == lock['sha256'], 'Upstream source checksum mismatch'
(build/'source.tar.gz').write_bytes(data)
PY
mkdir "$build/source"
tar --no-same-owner -xzf "$build/source.tar.gz" --strip-components=1 -C "$build/source"
export SOURCE_DATE_EPOCH=1590451200
export LC_ALL=C.UTF-8 TZ=UTC
(cd "$build/source" && ./autogen.sh --prefix=/usr && make -j2)
stage="$build/package"
mkdir -p "$stage/DEBIAN" "$stage/usr/lib/ios-usbmuxd-compat/daemon" "$stage/usr/share/doc/ios-usbmuxd-compat-daemon"
install -m755 "$build/source/src/usbmuxd" "$stage/usr/lib/ios-usbmuxd-compat/daemon/usbmuxd"
cp "$build/source/COPYING.GPLv2" "$build/source/COPYING.GPLv3" "$stage/usr/share/doc/ios-usbmuxd-compat-daemon/"
cat > "$stage/usr/share/doc/ios-usbmuxd-compat-daemon/copyright" <<'COPYRIGHT'
Upstream: https://github.com/libimobiledevice/usbmuxd
Source commit: 79c8b38d1488a6b07e1e68f39d8caec3f1a45622
Copyright: the upstream authors named in the corresponding source archive.
The daemon's main.c and preflight.c offer GNU GPL version 2 OR version 3.
See COPYING.GPLv2, COPYING.GPLv3 and each source file for exact notices.
This separately built daemon is not licensed under the framework's MIT license.
COPYRIGHT
cp "$root/packaging/daemon/source.json" "$stage/usr/share/doc/ios-usbmuxd-compat-daemon/source.json"
python3 - "$stage" <<'PY'
import hashlib, json, pathlib, platform, sys
stage = pathlib.Path(sys.argv[1])
base = stage/'usr/lib/ios-usbmuxd-compat/daemon'
manifest = {'schema_version': 1, 'validated': False, 'architecture': platform.machine(),
    'provenance': 'Unpatched upstream 1.1.1, commit 79c8b38d1488a6b07e1e68f39d8caec3f1a45622; NOT a validated modern-iPhone fix',
    'sha256': {'usbmuxd': hashlib.sha256((base/'usbmuxd').read_bytes()).hexdigest()}}
(base/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
PY
# Compute target ABI dependencies with Debian tooling, never copy Nix binaries.
mkdir "$build/debian"
cp "$root/packaging/debian/control" "$build/debian/control"
deps=$(cd "$build" && dpkg-shlibdeps -O -e"$stage/usr/lib/ios-usbmuxd-compat/daemon/usbmuxd" | sed -n 's/^shlibs:Depends=//p')
cat > "$stage/DEBIAN/control" <<CONTROL
Package: ios-usbmuxd-compat-daemon
Version: 1.1.1+reference.1
Architecture: $(dpkg --print-architecture)
Maintainer: ios-usbmuxd-compat contributors <maintainers@example.invalid>
Depends: ios-usbmuxd-compat, $deps
Section: utils
Priority: optional
Description: unvalidated isolated usbmuxd baseline for developer validation
 This optional artifact has no compatibility patch and is never activated
 automatically. It does not replace a distribution-owned executable.
CONTROL
# Package removal first disables only the framework-owned override.
cat > "$stage/DEBIAN/prerm" <<'PRERM'
#!/bin/sh
set -e
case "$1" in remove|deconfigure|upgrade) /usr/lib/ios-usbmuxd-compat/helper rollback;; esac
exit 0
PRERM
chmod 755 "$stage/DEBIAN/prerm"
mkdir -p "$root/dist"
dpkg-deb --root-owner-group --build "$stage" "$root/dist/ios-usbmuxd-compat-daemon_1.1.1+reference.1_$(dpkg --print-architecture).deb"
cp "$build/source.tar.gz" "$root/dist/usbmuxd-1.1.1-source.tar.gz"
(cd "$root/dist" && sha256sum ./*.deb ./*-source.tar.gz > SHA256SUMS)
