# ios-usbmuxd-compat

A reusable Python framework, example application and Debian packaging reference
for diagnosing iPhone USB connectivity on Linux. MIT licensed. Pre-1.0.

**Hardware compatibility has not been validated by this project. No patched
daemon is shipped or enabled by default.** Automated tests exercise diagnostic
classification, repair safeguards and package lifecycle behavior. See the
[actual test matrix](docs/compatibility.md) and [hardware plan](docs/hardware-test-plan.md).

## What this project does

A phone can be visible on USB while pairing or an iOS protocol still fails.
This framework tests each stage and gives applications a versioned JSON report:

1. Host, distribution packages, daemon process and systemd configuration.
2. Apple USB device enumeration and usbmuxd transport visibility.
3. Pairing validation, Trust prompts, lock state and initialization errors.
4. A real read-only lockdown query, plus optional application-specific probes.

The system **usbmuxd daemon** owns USB communication and its standard socket.
**Client libraries and tools** talk to that socket and implement iOS protocols.
Updating client tools can solve a client ABI or protocol issue without replacing
the daemon. A higher version number alone is never proof that either is needed.

The default is to preserve a working distribution stack. Missing hardware gives
`pending_device`. Installation finishes without an attached phone. Device events
schedule a bounded systemd check outside udev; application startup and CLI checks
provide additional validation opportunities.

## Quick start

Build in a Debian or Ubuntu VM. The resulting `.deb` files do not need Nix.

```sh
git clone https://github.com/<owner>/ios-usbmuxd-compat.git
cd ios-usbmuxd-compat
sudo apt-get update
sudo apt-get install build-essential debhelper dh-python python3-all \
  python3-setuptools python3-wheel python3-jsonschema pybuild-plugin-pyproject
./scripts/test.sh
./scripts/build-deb.sh
sudo apt-get install ./dist/ios-usbmuxd-compat_*.deb \
  ./dist/iphone-connectivity-demo_*.deb
```

The library package includes the diagnostic CLI and shared integration. The demo
package adds `iphone-connectivity-demo`. Optional validated client/daemon
components are separate and are not dependencies. See
[installation](docs/installation.md).

For a disposable container build and install/reinstall/upgrade/remove/purge test:

```sh
./scripts/container-deb-test.sh debian:12
# Also: debian:13, ubuntu:22.04, ubuntu:24.04, ubuntu:26.04
```

Containers do not prove live systemd/udev activation or hardware compatibility.
The generated package and build metadata are retained under `dist/`.

Nix development and rootless application builds:

```sh
nix develop
./scripts/test.sh
nix flake check
nix build .#iphone-connectivity-demo
./result/bin/iphone-connectivity-demo check
```

The flake supports `x86_64-linux` and `aarch64-linux`. Nix packages install rootless
entry points. Debian packages install the target distribution's privilege and
device-event integration. The [NixOS module example](examples/nixos/module.nix)
uses `services.usbmuxd.package` with an independently validated derivation. The
framework never changes NixOS configuration.

## Test an iPhone

```sh
iphone-connectivity-demo check
iphone-connectivity-demo check --json
iphone-connectivity-demo devices
iphone-connectivity-demo pair
iphone-connectivity-demo repair --dry-run
iphone-connectivity-demo repair
iphone-connectivity-demo status
iphone-connectivity-demo rollback
```

Launching `iphone-connectivity-demo` without arguments also runs `check`.

`ready` means the pairing validation and real lockdown query succeeded, along
with any registered application probes. `pending_device` means the app is ready
to test when a phone is attached. For `awaiting_trust`, unlock the phone and
accept its Trust prompt. `pair` explicitly requests pairing; normal `check`
does not pair or delete records. A locked phone, rejected Trust, permissions
failure and missing hardware are separate from a demonstrated daemon failure.

Device labels are local to a report and do not expose UDIDs. Multiple phones
have individual results. Use JSON for integrations; human output lists daemon
and package context. [Troubleshooting](docs/troubleshooting.md) explains states.

## How automated repairs work

1. **Test the existing stack.** A working stack remains unchanged.
2. **Try compatible private clients.** Only installed, validated tools and
   application-scoped libraries may be selected. System libraries remain intact.
3. **Recognize configuration and preflight failures.** Guide Trust completion
   and retry. No universal preflight workaround is enabled.
4. **Activate a verified replacement only when necessary.** A separately
   installed component must match the host, failure evidence and stock unit.
   A package-owned systemd drop-in changes the executable while retaining the
   distribution unit's arguments and account configuration.
5. **Verify and recover.** Check startup, socket and device protocol results.
   Verified activation failure restores the original service configuration.
   Missing hardware remains pending validation. Rollback and interrupted-repair
   recovery use a locked, durable journal.

This repository implements replacement infrastructure and fixture tests.
It deliberately provides **no approved current-iPhone patch**. An unknown
binary, hash mismatch, unsupported unit or administrator override blocks repair.
See [daemon validation](docs/daemon-validation.md) and
[upstream issue research](docs/upstream-research.md).

## Integrating into another application

```python
from ios_usbmuxd_compat import ProbeResult
from ios_usbmuxd_compat.remediation import diagnose_selected

class ApplicationProbe:
    name = "my-product-query"

    def run(self, device_id, runner, tools):
        result = runner([tools["ideviceinfo"], "-u", device_id,
                         "-k", "ProductType"], timeout=5)
        ok = result.code == 0 and result.stdout.strip().startswith("iPhone")
        return ProbeResult("working" if ok else "application_protocol_failure",
                           "Application probe completed.")

report = diagnose_selected(probes=[ApplicationProbe()])
if report["status"] == "ready":
    print("Enable the iPhone feature")
```

Replace the sample's read-only query with the actual service your app needs.
The core library remains unchanged. Read the [integration guide](docs/integration-guide.md)
and [copyable examples](examples/integration/) for Debian dependencies, startup,
device events, JSON consumption, repair notifications and CI.

## Security and limitations

Diagnostics run without root. Initial Debian installation requires administrator
authorization to install system integration. Later repair uses a fixed helper
through PolicyKit and may prompt for administrator approval. The helper accepts
only predefined actions, independently rechecks evidence, and cannot accept
arbitrary commands, paths, configuration text or application probes.

The framework cannot bypass iPhone Trust, unlock a phone, or circumvent Linux
USB permissions. It never overwrites `/usr/sbin/usbmuxd`, installs global shared
libraries, or deletes pairing records. Private client and replacement packages
must satisfy their own licensing, ABI and validation obligations.

The diagnostic JSON contract is documented in [report schema](docs/report-schema.md).

See [security model](docs/security-model.md), [security reporting](SECURITY.md),
[architecture](docs/architecture.md), [contributing](CONTRIBUTING.md) and
[attribution](NOTICE.md).

## Builds and releases

GitHub Actions run unit checks, lint and Debian lifecycle builds. Build artifacts
include `.deb` files and checksums. The manual release workflow produces a
candidate and records its source commit and build-image digest; it does not
publish a release or assert hardware support. See [release process](docs/releases.md).
