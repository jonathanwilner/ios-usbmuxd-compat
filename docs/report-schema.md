# Versioned reports

`check` and `devices` emit the diagnostic report defined in
[`schemas/diagnostic-v1.schema.json`](../schemas/diagnostic-v1.schema.json).
The public `diagnose()` and `diagnose_selected()` APIs return the same structure.
Consumers must check `schema_version == 1` and tolerate additional fields.

- `status` is the aggregate actionable result. A single failing device prevents
  `ready`. `ready` requires pairing and read-only lockdown success.
- `device_connected` is supported by an iOS-candidate USB device or transport ID.
- `daemon_healthy` reflects socket access and daemon conflicts, not iOS protocol
  compatibility. Lack of hardware can coexist with an inactive service.
- `usbmux_transport`, `pairing` and `application_protocol` record progression.
  `not_tested` must never be interpreted as successful.
- `host` includes distribution, architecture, package versions, process
  executables, systemd properties, socket and USB observations. Inaccessible
  process details or journal information remain unavailable.
- `devices` has per-report labels such as `device-1`. Labels are not stable device
  identifiers. Each item has pairing, protocol and named-probe results.
- `recommended_action`, `requires_admin` and `message` guide the UI. They are
  informational. Never execute their contents or use them to authorize privilege.

`pair`, `repair`, `rollback`, `status` and `host-check` use operation-specific
objects, not the full diagnostic schema. They include a `status` and relevant
state or result fields. A repair may include a nested diagnostic report. Check
the operation's exit code and fields; do not feed its envelope to the diagnostic
schema validator.

Default reports omit UDIDs and raw tool/journal output. Custom probe names and
messages are controlled by the integrating application; use fixed, non-sensitive
names. The framework retains probe names and statuses, not custom messages.
`--verbose` prints sanitized context to stderr and leaves JSON on stdout.
