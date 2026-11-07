#!/bin/sh
set -eu
image=${1:-debian:12}
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
docker run --rm -v "$root:/work" -w /work "$image" sh -ec '
 export DEBIAN_FRONTEND=noninteractive
 apt-get update
 apt-get install -y build-essential autoconf automake libtool pkg-config python3 ca-certificates patchelf libusb-1.0-0-dev libgnutls28-dev libgcrypt20-dev libcurl4-gnutls-dev
 python3 scripts/build-daemon-candidate.py
'
