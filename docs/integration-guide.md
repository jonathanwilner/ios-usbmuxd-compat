# Integrate the framework

## Stable API

Install `ios-usbmuxd-compat` as a Debian dependency or install the Python project
in an application environment. Python 3.10 or later is required.

```python
from ios_usbmuxd_compat import inspect_host, ProbeResult
from ios_usbmuxd_compat.remediation import diagnose_selected

class MyProbe:
    name = "my-application"

    def run(self, device_id, runner, tools):
        result = runner([tools["ideviceinfo"], "-u", device_id,
                         "-k", "ProductType"], timeout=5)
        if result.code == 0 and result.stdout.strip().startswith("iPhone"):
            return ProbeResult("working", "Application query completed.")
        return ProbeResult("application_protocol_failure", "Application query failed.")

report = diagnose_selected(probes=[MyProbe()])
if report["status"] == "ready":
    pass  # Enable the feature requiring iPhone access.
```

The sample uses a read-only lockdown operation. Replace it with your service's
actual protocol test. Return `working` only after the expected protocol response.
Probes run as trusted application code in the caller's process. They receive the
real device ID for protocol access; never log that ID or return it in messages.
Use the supplied runner and an explicit timeout for subprocesses. Pure Python
network probes must set their own socket timeouts. A malicious or blocking probe
is not sandboxed by this library. The privileged helper never loads custom probes.

`inspect_host()` returns context only. `diagnose_selected(probes=...)` honors a
previously verified private-client selection. Plain `diagnose()` always starts
with system tools by default and is useful for a stock-stack baseline. `diagnose(probes=...)` always includes the
framework's lockdown probe and adds application probes. Reports use schema
version 1. Application-specific failures must not authorize a daemon replacement.
Repair and rollback are separate operations. The public remediation module
exposes `select(report)`, `repair(dry_run=True)`, `status()` and `rollback()`.
`pair_selected()` explicitly pairs using the approved client selection and
requires the phone's Trust decision. Host-mutating methods require authorization; normal apps should invoke the installed
CLI's fixed `repair` action and let PolicyKit request it.

## Files to reuse and files to adapt

| Example | Reuse |
|---|---|
| `examples/integration/debian-control.fragment` | Merge the dependency into your package; retain your package name. |
| `examples/integration/postinst.fragment` | Keep the rule that installation never waits for a phone; merge with your hooks. |
| `examples/integration/startup.py` | Copy the control flow; replace the application probe. |
| `examples/integration/device-event.md` | Use the shared integration or adapt unique unit names and service user. |
| `examples/integration/consume-json.py` | Copy the schema gate and status mapping; adapt user messages. |
| `examples/integration/request-repair.py` | Copy fixed-action invocation; adapt UI notifications. |
| `packaging/systemd/` and `packaging/udev/` | Installed by the library package; avoid duplicate event registration. |

Keep installation, diagnosis and authorization separate. No extra terminal sudo
command is required for ordinary diagnostics. Repair can prompt for an
administrator through PolicyKit. Missing authorization is a reportable state.

## Private clients and daemon fallback

See the [concrete private-client layout and manifest example](../examples/integration/private-clients.md).

Use an application-private client directory and relative ELF RUNPATH for updated
libraries. Do not set global loader paths or overwrite distribution libraries.
The repair engine accepts only its documented fixed resource location, reviewed
manifest and validated executables. See [daemon-validation.md](daemon-validation.md)
for the exact trust record and ABI requirements.

Fallback is disabled when no validated component is installed. This repository
ships no trusted replacement. To enable it, an administrator must install a
separately reviewed component with the fixed manifest and matching evidence.
Then run dry-run before requesting repair. To disable an active fallback, run
`iphone-connectivity-demo rollback`, verify stock service recovery, and remove
the optional component. Keep pairing records untouched.

## Include in CI

Run `./scripts/test.sh` for the framework and add fixtures
for your probe's success, timeout, malformed response and missing-device cases.
Build your package using the native Debian workflow. Reuse the lifecycle matrix
in `.github/workflows/build-deb.yml` for installation with no attached hardware,
upgrade, removal and purge. CI fixtures must never imply hardware validation.

Before advertising support, complete [the hardware test plan](hardware-test-plan.md)
with the application's actual probe. Record the tested matrix and retain the
validation evidence for any fallback binary.
