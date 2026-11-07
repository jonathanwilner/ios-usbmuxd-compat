# Vysor installer integration

This installer adds managed iPhone USB checks to an existing native Vysor Debian
package. It preserves the supplied Vysor package byte for byte. It does not
include proprietary Vysor source in the public toolkit repository.

## Install

Use a bundle built for your distribution and architecture. Extract the complete
bundle, open a terminal in it, then run:

```sh
sudo ./install.sh
```

This is the one privileged installation step. APT installs Vysor, the framework,
the Vysor launcher integration, and an optional supplied daemon component.
Distribution runtime dependencies may be downloaded by APT. No installer script
downloads an executable or compiles source. The checksums detect accidental
bundle changes; they are not a publisher signature. Obtain the bundle through a
trusted channel. No phone is required during installation.

Open **Vysor** from the application menu as your ordinary user. A terminal shows
connectivity or authorization messages, then Vysor opens when the stack is ready
or no iPhone is attached. Unlock and accept Trust when requested, then relaunch.
A supported repair can request PolicyKit approval. Without an attached iPhone,
Vysor still opens, including for Android use. If an attached iPhone is locked or
needs Trust, the managed launcher waits for that issue to be resolved on a later
launch. To use Android independently, launch `/opt/Vysor/vysorapp` directly.

The original desktop file is preserved using a package-owned `dpkg-divert`.
Removing `vysor-usb-compat` restores it. The original executable and Electron
sandbox settings are unchanged. The launcher does not add `--no-sandbox`.

```sh
sudo apt-get remove vysor-usb-compat
# Optional, after reviewing other framework consumers:
# ios-usbmuxd-compat rollback
# sudo apt-get remove ios-usbmuxd-compat-daemon ios-usbmuxd-compat
```

## Build for your application delivery

First build the framework natively on the target Debian/Ubuntu release using
`scripts/build-deb.sh`. Then run from this repository:

```sh
python3 integrations/vysor/build-installer.py \
  --vysor /path/to/your/Vysor-linux.deb \
  --framework dist/ios-usbmuxd-compat_0.1.0_all.deb \
  --output dist/vysor-installer
```

For a verified replacement, additionally pass
`--daemon /path/to/ios-usbmuxd-compat-daemon.deb`. Follow
`docs/daemon-validation.md` before approving the component. The reference daemon
in this repository is unvalidated and does not provide an automatic fix.
The installer must not manufacture approval for an unknown daemon.

The builder requires `python3` and `dpkg-deb`. It validates package names,
architectures and the known `/opt/Vysor/vysorapp` layout. It accepts your modified
Vysor package when it retains that layout. The integration pins its dependency to
the exact supplied Vysor version; rebuild the bundle for Vysor upgrades. Include
all files in the output folder when handing off the installer. Check Vysor's
redistribution terms before sharing its package. Publish toolkit source alone
on GitHub; generated bundles stay out of Git.

## Verification boundary

Package and container checks can prove installation and launcher wiring. They
cannot establish Electron desktop launch, iPhone mirroring, device control, live
systemd activation, or a validated usbmuxd fix. Run the hardware plan with the
actual Vysor build before claiming those outcomes.
