"""Installed-package checks in an isolated, hardware-free Debian/Ubuntu container."""
import json
import pathlib
import re
import subprocess

report = json.loads(subprocess.check_output(["iphone-connectivity-demo", "check", "--json"], text=True))
assert report["schema_version"] == 1
assert report["status"] == "pending_device", report
assert pathlib.Path("/usr/lib/ios-usbmuxd-compat/helper").is_file()
assert pathlib.Path("/lib/udev/rules.d/79-ios-usbmuxd-compat.rules").is_file()
assert not pathlib.Path("/etc/systemd/system/usbmuxd.service.d/50-ios-usbmuxd-compat.conf").exists()
subprocess.run(["iphone-connectivity-demo", "repair", "--dry-run"], check=True)
subprocess.run(["iphone-connectivity-demo", "status"], check=True)
# Confirm package payload is native Python, with no unresolved Nix runtime paths.
for package in ("ios-usbmuxd-compat", "iphone-connectivity-demo"):
    for name in subprocess.check_output(["dpkg-query", "-L", package], text=True).splitlines():
        path = pathlib.Path(name)
        if path.is_file() and (name.startswith("/usr/bin/") or name.startswith("/usr/lib/")) and path.suffix != ".pyc":
            assert not re.search(rb"/nix/store/[a-z0-9]{32}-", path.read_bytes()), name
print("Installed CLI, no-device behavior, payload and safe default checks passed")
