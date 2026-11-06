# Security model

Diagnostics are unprivileged. Pairing uses `idevicepair` and requires the user's
Trust decision on the iPhone. The framework never deletes pairing records.

The installed helper accepts exactly one fixed action: `repair`, `rollback`,
`status`, or `host-check`. It accepts no executable paths, destinations, shell
commands, JSON manifests, configuration contents, or plugin names. The launcher
uses Python isolated mode, and the helper replaces its environment with a fixed
PATH and locale before inspection. PolicyKit requires administrator authorization.
The CLI invokes PolicyKit directly, so an ordinary user does not type `sudo`.
An unavailable authorization agent produces an explicit approval requirement.
Installing the package does not grant every local user unrestricted repair rights.

Application probes run in the calling application's unprivileged process. The
helper never loads application plugins or executes a caller-selected probe.
Applications must treat plugin code as trusted code and enforce their own timeouts.

Repair components must be installed by an administrator under the fixed package
directory. Every manifest and binary has root ownership and no group/other writable
or symlink ancestor. Binary hashes, architecture, distribution, release, recorded
hardware validation and provenance are checked. The daemon additionally requires
an exact effective stock unit hash and an exact observed package/socket failure
match. This is a publisher's validation contract, not proof derived from a version
number. No replacement binary or validated manifest ships in the default package.

Transactions use a nonblocking `flock` and an atomic, fsynced journal under
`/var/lib/ios-usbmuxd-compat`. Undo information is written before creating the
package's uniquely named drop-in. A subsequent repair recovers an interrupted
prepared/activating transaction by removing only that exact recorded override.
An externally modified override is preserved and requires administrator review.

A single unmanaged usbmuxd process also blocks activation: the observed daemon PID
must match systemd MainPID. The process inventory is refreshed before mutation.

Existing administrator drop-ins and unsupported `ExecStart` syntax stop daemon
repair. The replacement changes only the executable in the discovered command.
The original arguments, User, Group, service type and other distribution settings
remain in effect. Health checks inspect service result, process executable,
socket health and real device diagnostics. A verified failure rolls back. A phone
that disappears leaves hardware validation pending when the service exited cleanly.

Private client tools use application-relative loader paths from their package.
The framework never changes `/etc/ld.so.conf`, system libraries, `/usr/sbin/usbmuxd`,
USB permissions, or `/var/lib/lockdown`. A package publisher must inspect ELF ABI,
architecture, dynamic dependencies, licenses and RUNPATH before marking a bundle
validated. Root ownership protects the full installed bundle; hash inventories
must include every bundled library.

The trust boundary assumes the kernel, distribution Python, systemd, installed
packages and administrator are trusted. A malicious root user is outside scope.
Normal reports suppress device identifiers and raw command output. The journal
uses mode 0600 and records service configuration, never pairing certificates or
iPhone secrets. A separate mode-0644 public state file contains only the schema
version and a fixed phase value. Public status never exposes effective unit text.
Private client manifests must match the exact installed stack package versions;
a package upgrade requires a newly validated manifest before private reuse.
