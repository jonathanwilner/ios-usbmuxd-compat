# Architecture

The reusable `ios_usbmuxd_compat` library has three boundaries:

- Inspection reads OS/package metadata, USB sysfs, daemon processes, the systemd
  unit and the usbmuxd socket. It uses bounded subprocess calls with no shell.
- Diagnostics combine USB presence, transport enumeration, pairing validation
  and a real lockdown operation. Application probes extend the last step.
- Remediation selects the smallest supported change. The privileged helper
  accepts a fixed action vocabulary and independently validates local evidence.

The example's default invocation runs diagnostics. Each stack check has a
60-second command budget. A selected private stack can require a second check;
the deferred systemd task has its own 90-second limit. Package installation performs
only lightweight host checks. A udev event asks systemd to run a bounded deferred
check. systemd owns the work outside the udev process. Device reconnects start a
new validation opportunity. Application launch and explicit `check` remain
available regardless of the device-event integration.

A `ready` result requires actual protocol success. Installed package versions
are contextual evidence. USB Apple vendor detection is a candidate-device
signal: Apple peripherals may not be iPhones, and transport evidence is needed.
Device errors are reported individually; aggregate status does not hide a
failing phone behind a successful one.

The library can be used without Debian integration. The Debian packages install
entry points, runtime resources, service units and authorization policy. Nix is
an optional build/development environment; Debian packages use the target
system's Python and libraries.

Reports carry `schema_version: 1`. Additive fields may appear within the same
version. Consumers must reject unsupported major schema versions and tolerate
unknown fields. Error text is normalized; normal reports omit raw UDIDs and
pairing contents. See the JSON schema shipped with the source and
[integration-guide.md](integration-guide.md).

Daemon fallback is a separate trust decision. This repository ships its guarded
activation mechanism, not a proven iPhone compatibility patch. Source pinning,
ABI and host compatibility, unit fingerprints and hardware evidence belong to
the optional component's validation record.
