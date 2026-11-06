# Troubleshooting

Start with `iphone-connectivity-demo check --json` and
`iphone-connectivity-demo status`. Keep the `schema_version` and normalized
state when reporting a problem. Do not post raw pairing records or device IDs.

| State | Next action |
|---|---|
| `ready` | Continue using the existing stack. |
| `pending_device` | Connect an iPhone with a data cable and check again. |
| `awaiting_trust` | Unlock the phone, inspect its Trust dialog, then use `pair` if needed. |
| `permission_denied` | Ask the administrator to inspect USB/socket access policy. |
| `client_library_incompatible` | Inspect supported private-client package availability. |
| `daemon_failure` | Inspect service state, socket and conflicting processes; dry-run repair. |
| `manual_intervention_required` | Follow the report's evidence; no approved automatic repair exists. |
| `repair_failed` | Inspect recorded rollback state before retrying. |

A phone visible in USB but absent from usbmuxd is insufficient evidence for a
specific daemon patch. Check the cable, USB mode, service journal and preflight
messages. A timeout or device loss can occur during disconnect; reconnect and
repeat the bounded check before drawing a compatibility conclusion.

A PolicyKit dialog authorizes only the package-installed helper's fixed action.
If no desktop authentication agent is running, use an administrator session to
configure authorization. The framework reports the approval requirement; it
does not bypass policy or silently install executables.

For device-event diagnostics, inspect:

```sh
systemctl list-units 'ios-usbmuxd-compat*'
journalctl --no-pager -u 'ios-usbmuxd-compat*'
systemctl cat usbmuxd.service
```

The service journal can contain host-generated sensitive information. Review
it locally before sharing. The framework never deletes `/var/lib/lockdown`.
