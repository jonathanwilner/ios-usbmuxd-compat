#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
if [ "$(id -u)" -ne 0 ]; then
  echo 'Install once with: sudo ./install.sh' >&2
  exit 77
fi
# The initial installer is trusted administrator input. No phone is required.
sha256sum -c SHA256SUMS
. /etc/os-release
case "$ID:$VERSION_ID" in
 debian:12|debian:13|ubuntu:22.04|ubuntu:24.04|ubuntu:26.04) ;;
 *) echo 'This installer targets Debian 12/13 and Ubuntu 22.04/24.04/26.04.' >&2; exit 1;;
esac
if [ "$(dpkg --print-architecture)" != "$(cat ARCHITECTURE)" ]; then
 echo 'Installer architecture does not match this machine.' >&2
 exit 1
fi
set -- ./vysor.deb ./framework.deb ./integration.deb
if [ -f ./daemon.deb ]; then set -- "$@" ./daemon.deb; fi
apt-get install --reinstall -y "$@"
echo 'Installed. Open Vysor from the application menu as your ordinary user.'
echo 'Connect and unlock the iPhone, accept Trust, then retry Vysor if prompted.'
echo 'No validated daemon component means daemon replacement remains unavailable.'
