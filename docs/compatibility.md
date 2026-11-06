# Compatibility and verification

This is a reference implementation. No physical iPhone has been tested for this
project. No patched daemon is approved. A successful fixture or build result is
not a hardware compatibility claim.

Verification date: 6 Nov 2026. All 60 automated tests passed on each native
Debian/Ubuntu target. Lint and the x86_64 Nix build/check passed.

## Target matrix

| Target | Architecture | Native package lifecycle | Hardware and live systemd/udev |
|---|---|---|---|
| Debian 12 | amd64 | Passed | Not run |
| Debian 13 | amd64 | Passed | Not run |
| Ubuntu 22.04 | amd64 | Passed | Not run |
| Ubuntu 24.04 | amd64 | Passed | Not run |
| Ubuntu 26.04 | amd64 | Passed | Not run |
| Nix development | x86_64-linux | Framework build/check passed | Rootless host inspection only |
| Nix development | aarch64-linux | Derivation evaluation passed; no native build | Not run |

Native package tests run in Docker without a phone or systemd as PID 1. They
build the actual `.deb`, install it with native dependencies, run its installed
CLI, reinstall, upgrade to a fixture version, remove and purge. They verify that
pairing fixtures survive and that the default install adds no daemon override.
Package payload checks reject Nix store references in installed code.

Unit fixtures cover working stock, no device, later attachment, USB-only
visibility, Trust/pairing/lock errors, timeout/drop, permissions, multiple devices,
client ABI failure, private-client repair, validated daemon activation, failed
activation rollback, administrator overrides, unit/package changes, interrupted
transactions, concurrency and malformed helper/component inputs. These are
synthetic tests, not protocol emulators or physical validation.

The optional upstream 1.1.1 baseline has a deliberately unvalidated manifest.
Its Nix build and Debian 12 package build passed. These results prove build and package isolation only. It cannot be activated
by the repair engine as shipped. See [the recipe](../packaging/daemon/README.md).

Known limits:

- Live systemd authorization, USB event retriggering, ownership and rollback need
  VM/hardware acceptance. Containers cannot prove these behaviors.
- Rootless journal/process access may be restricted by host security policy.
- Utility error text can change. Unknown failures remain manual investigation.
- The built-in command budget is 60 seconds per stack check and the device limit is 16. Trusted
  custom probes must implement their own bounded I/O or use the supplied runner.
- Private bundle and daemon ABI validation belongs to the component publisher.
- No automatic `--no-preflight` workaround or source-level pairing patch is enabled.

Each native build output includes `BUILD_IMAGE` with the container image digest,
`BUILD_PACKAGES`, `TEST_RESULT`, Debian build metadata, and `SHA256SUMS`.
Run `scripts/container-deb-test.sh <image>` to repeat the lifecycle test.
