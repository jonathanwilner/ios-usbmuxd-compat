# Optional daemon source recipe

`source.json` pins upstream usbmuxd 1.1.1 by Git commit and archive SHA-256.
No patch is shipped. This baseline demonstrates packaging and **does not fix or
claim to fix issue 281**. Its manifest has `validated: false`; the repair helper
rejects activation. The MIT license applies to this framework. The independently
built upstream daemon retains its GPL version 2 or version 3 licenses, included in its package. Distribute
the corresponding source archive with any distributed daemon binary.

Inside a clean Debian 12 build VM or container:

```sh
apt-get update
apt-get install -y ca-certificates build-essential autoconf automake libtool pkg-config python3 \
  dpkg-dev libusb-1.0-0-dev libplist-dev libimobiledevice-dev
./scripts/build-daemon-reference.sh
```

The output is `dist/ios-usbmuxd-compat-daemon_1.1.1+reference.1_ARCH.deb` and the
corresponding source archive. No maintainer script downloads or compiles code.
The package installs only a private binary, manifest, provenance and license files.
It does not install upstream udev rules, service units, users or shared libraries.
Runtime ABI dependencies come from `dpkg-shlibdeps` in the target build environment.

The recipe fixes source, version, timestamps and patch list. Distribution compiler
and dependency versions still affect binary bytes. Record a build-image digest and
apt package versions for a release; bit-for-bit cross-distribution identity is not
claimed. Build separately on each target architecture. Nix development builds are
not the source of Debian runtime binaries.

To adapt this recipe to a real repair, review and pin the patch and its license,
apply it explicitly, change the output version, and follow
[daemon validation](../../docs/daemon-validation.md). Hardware evidence, exact
stock unit hash and failure signature are mandatory before a separate reviewed
package may set `validated: true`. A package builder must never infer validation
from a successful compile. Daemon upgrades must be followed by fresh verification;
a changed binary hash fails the previous approval.

The Nix `usbmuxd-reference` derivation builds the same pinned source against the
locked Nixpkgs libraries. Modern libplist introduces enum constants that collide
with upstream 1.1.1 names. Its transparent `postPatch` prefixes usbmuxd's local
`PLIST_FORMAT_` constants with `USBMUXD_` in every C source/header. This is a
build-only namespace adjustment, with no preflight or pairing behavior change.
The native Debian 12 recipe builds without that adjustment. Neither artifact is
a validated compatibility replacement.

For the newer pinned upstream source and its private dependency stack, use the
[current candidate recipe](CANDIDATE.md). The older baseline above remains an
educational reference. Both require independent hardware validation.
