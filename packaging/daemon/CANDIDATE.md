# Current upstream candidate

The candidate pins usbmuxd `3ded00c9985a5108cfc7591a309f9a23d57a8cba`
and libplist 2.8.1, libimobiledevice-glue 1.3.3, libusbmuxd 2.1.1,
libtatsu 1.1.0, and libimobiledevice 1.4.0. Every source has an immutable commit and SHA-256
in `candidate-sources.json`. These are upstream sources without local patches.

Build on a Docker host:

```sh
./scripts/build-candidate-container.sh debian:12
# Or ubuntu:24.04; archive dist/candidate before building another target.
```

The native Debian package contains an ELF daemon and private shared libraries
under `/usr/lib/ios-usbmuxd-compat/daemon`. Each ELF has a relative RUNPATH.
The daemon retains `/var/lib/lockdown`, `/run/usbmuxd`, preflight support,
and the distribution service account/arguments at activation. No system
library, distribution executable, udev rule or service unit is replaced.
Client tools in `daemon/bin` are for candidate validation; the wrapper does
not automatically inject them into Vysor's Electron process.

The build checks runtime library resolution. It emits corresponding source
archives, the source lock, build recipe, license notices and checksums.
The build requires native Debian tooling; the resulting package needs no Nix.
Source revisions are pinned. Distribution build dependencies come from the
selected container's repositories, so byte-identical rebuilds additionally
require pinning that container and an apt snapshot.

## Evidence and activation gate

Upstream issue [281](https://github.com/libimobiledevice/usbmuxd/issues/281)
remains open. A user reported pairing an iPhone 14 running iOS 26.6 with
this daemon revision, after restarting the phone once. That report is a reason
to test the candidate. It does not approve our package for automatic repair.
`--no-preflight` is not enabled. No invented retry patch is shipped.

Every candidate manifest starts with `validated: false`. Installation stores
files only. The privileged helper rejects activation until a maintainer has
completed the hardware plan in `docs/hardware-test-plan.md` and issued a
reviewed manifest for the exact target distribution, stock unit, installed
package versions, failure signature, architecture and binary inventory. See
`docs/security-model.md` and `src/ios_usbmuxd_compat/remediation/engine.py` for the enforced checks.
Do not change the flag alone: it is insufficient and bypasses the intended review.

Build the Vysor bundle using `integrations/vysor/build-installer.py --daemon`
with the candidate `.deb`. Include `candidate-corresponding-source.tar.gz`
and its checksums alongside every distributed installer containing this daemon.
Do not publicly redistribute the proprietary Vysor input without permission.

## Nix development build

`nix build .#usbmuxd-candidate` builds the same daemon commit using dependencies
from the committed nixpkgs lock. The native Debian recipe pins its own six-source
stack separately. Nix output is for Nix development and declarative NixOS use;
never copy it into a Debian installer. Both x86_64-linux and aarch64-linux are
exposed. Only a successful build on an architecture counts as build verification.
