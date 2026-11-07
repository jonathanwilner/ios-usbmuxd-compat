# Vysor integration verification

Date: 7 Nov 2026.

Input: Vysor 5.0.7 amd64 Debian package, SHA-256
`adf4a88c8d87d25d2e0ca6382afeea69712336668909250e2bb9a40d733cec77`.
This is the package referenced by the existing Vysor Nix packaging work.
All 1,299 compared extracted Electron files match the input archive. The
integration preserves this vendor package; no modified upstream Vysor code or
validated patched usbmuxd was identified in that source.

Passed:

- 68 framework tests, Python lint/compile checks and shell syntax checks.
- Debian 12 and Ubuntu 24.04 amd64: actual Vysor installer installation, repeated installation,
  integration upgrade, removal and purge in a clean container.
- Native runtime library resolution for the actual Vysor executable.
- No-phone diagnostics and no default daemon override.
- Original Vysor executable and desktop file byte comparison.
- Preservation of pairing fixture records.
- Safe rejection of an administrator-owned desktop diversion.
- Installer bundle SHA-256 verification.

The framework's 68-test native package lifecycle also passed on Ubuntu 24.04.
The public CI runs the
Vysor adapter with a synthetic vendor package across the five target distributions;
that fixture carries no proprietary code and does not prove Vysor runtime support.

Not exercised: graphical Vysor launch, iPhone mirroring/control, hardware pairing,
live systemd activation or PolicyKit UI. No updated daemon is approved or bundled.
The wrapper's lockdown query is not a Vysor mirroring acceptance test.
