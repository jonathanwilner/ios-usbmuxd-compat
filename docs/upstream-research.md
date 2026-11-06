# First-pairing research

Reviewed 6 November 2026:
[usbmuxd issue 281](https://github.com/libimobiledevice/usbmuxd/issues/281),
[preflight.c](https://github.com/libimobiledevice/usbmuxd/blob/master/src/preflight.c),
[main.c](https://github.com/libimobiledevice/usbmuxd/blob/master/src/main.c), and
[upstream service template](https://github.com/libimobiledevice/usbmuxd/blob/master/systemd/usbmuxd.service.in).
These are research references, not pinned build inputs.

The reporter associates a late first-time Trust dialog with a failed handshake
and a subsequent device drop. The proposal is bounded retry when the handshake
returns `LOCKDOWN_E_PAIRING_DIALOG_RESPONSE_PENDING`. A later commenter reports
using `--no-preflight`, but explicitly states that the original failure was not
reproduced. That observation does not prove a fix across distributions or
applications. Numeric error codes differ between APIs and releases; diagnosis
prefers named errors and context instead of interpreting any bare negative
integer as a daemon defect.

The implementation leaves preflight enabled. It recognizes pending Trust and
preflight evidence without treating either as proof that a daemon replacement
will work. Explicit pairing and bounded subsequent checks allow the user to
complete Trust. A source-level retry must account for device removal, denial,
thread lifetime and maximum waiting time before it can be promoted as a patch.
No such patch has been hardware-validated by this project.

`--no-preflight` must be confirmed against the installed executable's help before
any administrator considers a manual experiment. The framework reports support
where available and does not add the flag automatically. Do not use broad
`pkill` commands, delete pairing records, or run competing daemon instances.

A future validated workaround should match exact host and daemon evidence,
include a reproducible package, and pass the same rollback gates as a replacement.
Until then, an unsupported preflight failure requires manual investigation.
