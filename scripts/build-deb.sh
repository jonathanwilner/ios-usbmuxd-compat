#!/bin/sh
set -eu
# Build in a disposable copy; never rewrite a developer's debian/ directory.
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT HUP INT TERM
mkdir "$build/source"
tar -C "$root" --exclude=.git --exclude=dist --exclude=result --exclude=__pycache__ --exclude='*.egg-info' -cf - . | tar -C "$build/source" -xf -
cp -a "$build/source/packaging/debian" "$build/source/debian"
(cd "$build/source" && dpkg-buildpackage -us -uc -b) || { find "$build/source/debian" -maxdepth 6 -type f; exit 1; }
mkdir -p "$root/dist"
find "$build" -maxdepth 1 -type f \( -name '*.deb' -o -name '*.buildinfo' -o -name '*.changes' \) -exec cp {} "$root/dist/" \;
(cd "$root/dist" && sha256sum ./*.deb > SHA256SUMS)
