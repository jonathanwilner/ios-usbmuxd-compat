# Private client integration

An application can use its own trusted client directory without changing the
system daemon or the global dynamic linker configuration:

```python
from ios_usbmuxd_compat import diagnose
report = diagnose(client_dir="/usr/lib/my-application/ios/bin")
```

The path is application configuration. Do not obtain it from an untrusted report,
URL or device. This API runs as the application user. The privileged helper does
not accept a path and uses only `/usr/lib/ios-usbmuxd-compat/client`.

A private package's layout can be:

```text
/usr/lib/ios-usbmuxd-compat/client/
  manifest.json
  bin/idevice_id
  bin/idevicepair
  bin/ideviceinfo
  lib/<required shared libraries, installed under their exact SONAMEs>
```

Build in the target distro image with pinned source revisions and dependencies.
Link executables with `-Wl,-rpath,'$ORIGIN/../lib'`; ensure each privately bundled
library can also resolve its own private dependencies. Preserve the literal
`$ORIGIN` when passing it through the build system. Inspect each ELF using
`readelf -h`, `readelf -d` and `readelf -l`. Reject an unexpected architecture,
Nix interpreter, absolute build-directory RUNPATH, or dependency outside the
approved private/system inventory. Do not run `ldd` on an untrusted executable.

The framework's strict trusted-resource checks reject symbolic links. Install
regular files under the exact required SONAMEs and hash every installed file.
Do not place licenses or unrelated data inside the hashed runtime directory;
put license/provenance files under `/usr/share/doc/<your-package>/`.

Use [the private manifest template](private-client-manifest.example.json) as a
schema example, not an approved component. Fill in the actual SHA-256 inventory,
distribution, release, architecture and exact `host.packages` result. Record
source/build provenance and hardware evidence. Keep `validated` false until the
publisher reproduces the original client failure and confirms the new client's
real application protocol result on that target.

Use `dpkg-shlibdeps` to generate target runtime dependency declarations. Do not
place private libraries under `/usr/lib` globally, change `/etc/ld.so.conf`, or
set system-wide `LD_LIBRARY_PATH`. Package updates invalidate the manifest's
package fingerprint until revalidated. Rollback clears the selected private
bundle without touching the distribution client stack.
