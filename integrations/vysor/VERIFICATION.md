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
live systemd activation or PolicyKit UI. The original stock-only bundles contain no updated daemon. The candidate bundles
described below include an unapproved updated daemon that remains inactive.
The wrapper's lockdown query is not a Vysor mirroring acceptance test.

## Pinned upstream candidate installer

Source: usbmuxd `3ded00c9985a5108cfc7591a309f9a23d57a8cba`, with six pinned
upstream sources recorded in `packaging/daemon/candidate-sources.json`.
All candidate manifests remain `validated: false`.

Passed in this implementation session:

- Native Debian 12 and Ubuntu 24.04 amd64 package builds with private libraries.
- Debian 12 and Ubuntu 24.04: daemon startup, standard socket ListDevices reply,
  private client enumeration, complete manifest hashes and rejection of
  unvalidated activation. Candidate package reinstall, upgrade, removal and purge
  preserve stock daemon bytes and pairing records.
- Debian 12 and Ubuntu 24.04: actual Vysor installer with candidate package, repeated installation,
  companion upgrade, removal/purge, stock desktop and pairing preservation,
  and administrator diversion rejection.
- Nix x86_64-linux candidate build; aarch64-linux derivation evaluation only.
- 68 framework unit tests.

Corresponding source accompanies each candidate installer. No Vysor assets are
committed to the public repository. No connected iPhone was available on
Armstrong or Goran. Live systemd replacement, Trust, Vysor GUI and mirroring
remain NOT RUN. The original daemon remains untouched on both hosts.
