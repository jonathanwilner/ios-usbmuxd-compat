# Validating optional repair components

The default release contains no validated patched daemon. Upstream issue
[usbmuxd #281](https://github.com/libimobiledevice/usbmuxd/issues/281) reports a
first-pair preflight failure and suggests retrying pending Trust responses. A
comment reports `--no-preflight` use, but explicitly says the original failure was
not reproduced. These reports do not establish a generally safe Debian/Ubuntu fix.
The framework does not automatically add that option or claim a patch exists.

A distributor may build an independently reviewed patch through the optional
source-build recipe. Record the immutable source revision, source archive hash,
patch hashes, build environment, dependency versions and resulting SHA-256.
Validate license obligations separately: this project's MIT license does not
relicense usbmuxd or its dependencies. Build in the target Debian/Ubuntu environment,
never copy a Nix-linked daemon into a Debian package.

Install a candidate only into `/usr/lib/ios-usbmuxd-compat/daemon/usbmuxd` with a
root-owned `manifest.json` beside it. The manifest schema is:

```json
{
  "schema_version": 1,
  "validated": false,
  "architecture": "x86_64",
  "distribution": "debian",
  "release": "12",
  "repair_statuses": ["daemon_failure"],
  "provenance": "immutable source revision, archive and patch hashes, build record",
  "hardware_validation": "test record location and precise reproduced failure",
  "sha256": {"usbmuxd": "REPLACE_WITH_BINARY_SHA256"},
  "stock_unit_sha256": "SHA256_OF_EXACT_SYSTEMCTL_CAT_OUTPUT",
  "failure_match": {
    "socket": "unreachable",
    "packages": {"REPLACE": "exact diagnostics.host.packages object"}
  }
}
```

Only the publisher may set `validated` true after reproducing the failure and
passing the manual hardware plan with the candidate. A fresh package or service
unit update invalidates the match. Review and repeat validation before publishing
an updated manifest. Merely setting this field is not validation.

Verify foreground/systemd behavior, service account, `/run/usbmuxd`, udev device
activation, USB unplug/replug, Trust acceptance and denial, locked devices,
multiple devices, app protocol operation and rollback. An active candidate must
have the expected executable in `/proc/MainPID/exe`. The original stock executable
and pairing records must remain unchanged.

Private clients use `/usr/lib/ios-usbmuxd-compat/client/bin/{idevice_id,idevicepair,ideviceinfo}`
and `client/manifest.json`. The same schema applies without the daemon unit/failure
fields. Include `package_versions` with the exact diagnostics `host.packages`
object. A change in those package versions invalidates private bundle reuse. Set `repair_statuses` to `client_library_incompatible`, include hashes for
all tools and bundled libraries, and use ELF `$ORIGIN` RUNPATH. Validate actual
protocol success, ABI and dynamic dependencies on each supported release.

The state API reports `private_client` after successful verification. Applications
select the fixed validated bundle for future probes; rootless applications may
also explicitly pass their own trusted `client_dir`. A failed private-client probe
leaves system tools and saved selection unchanged. Rollback clears selection.

At build review, inspect each ELF without executing it:

```sh
readelf -h -d path/to/binary
readelf --version-info path/to/binary
```

Confirm ELF machine/class matches the package architecture. Inspect `NEEDED`,
`RUNPATH` and symbol-version requirements for every binary and bundled library.
Private libraries should resolve from a package-owned `$ORIGIN` path. Reject
writable directories, absolute build directories, `/nix/store`, and dependencies
missing from the target release. Then run the native tools in the target container
and complete hardware testing on a matching host. Header/hash checks performed by
the helper do not replace the publisher's ABI and loader-path review.
