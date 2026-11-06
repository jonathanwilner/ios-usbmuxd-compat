# Installation and removal

Use a Debian or Ubuntu system with Python 3.10 or later. Runtime dependencies are
provided by the native package manager. Use the README's `dpkg-buildpackage`
wrapper for a normal Debian build. A minimal container can use the provided
container build script, which installs build dependencies in the container.

Required binary packages:

- `ios-usbmuxd-compat`: library, diagnostic CLI, fixed privileged helper,
  PolicyKit definition, systemd check unit and udev rule.
- `iphone-connectivity-demo`: example command using the reusable library.

The distro provides usbmuxd and libimobiledevice utilities. The default package
does not contain a replacement daemon. Optional private clients and validated
daemon components require separate build and validation. No maintainer script
downloads or compiles executable code.

Installation does a bounded, best-effort host inspection and registers future
USB checks. It never waits for a phone, pairing, Trust or protocol success.
The device-event service runs unprivileged. Full checks run at CLI/application
launch, after a USB attachment, or on explicit request.

After installing, use `iphone-connectivity-demo check`. Connect a phone later
and repeat the command to see current results. Review service-event output with
`journalctl -u 'ios-usbmuxd-compat-check@*'`. A rootless service may have less
journal access than an administrator; unavailable evidence is reported.

Upgrade with the normal package manager. A changed distribution unit requires
revalidation before any new fallback activation. Run check after updates. Do
not hand-edit the package-owned drop-in.

Remove using:

```sh
iphone-connectivity-demo rollback  # If a fallback was activated; may prompt.
sudo apt-get remove iphone-connectivity-demo ios-usbmuxd-compat
sudo apt-get purge iphone-connectivity-demo ios-usbmuxd-compat
```

Removal invokes the guarded rollback path. It refuses to discard a changed
administrator-owned override. Resolve that conflict before continuing removal.
Pairing data under `/var/lib/lockdown` is preserved on removal and purge. Repair
audit state is also preserved so a conflict cannot silently lose recovery data.
