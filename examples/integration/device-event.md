# Deferred device events

Depending on `ios-usbmuxd-compat` installs its shared udev-to-systemd integration.
Use the installed `ios-usbmuxd-compat-check@.service` to obtain generic diagnostics.
It executes outside udev and has a fixed timeout. It does not launch a GUI or
run an application's custom probe as root.

For an application-specific background check, adapt the package's udev rule and
service under a unique application name. Run the check as an unprivileged system
user with only the access it needs. Keep `SYSTEMD_WANTS` activation and a bounded
oneshot. Do not add `RUN+=` commands that wait for Trust. Do not interpolate device
identifiers into shell commands. A service instance can use a kernel USB path
for scheduling, but the library itself enumerates devices.

Desktop notifications belong in your user-session application. Let the next
application startup or explicit Refresh action obtain a new report. A system
service cannot safely assume which desktop session should receive a dialog.
