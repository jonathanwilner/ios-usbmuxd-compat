"""Bounded host inspection; this module never changes system state."""
from dataclasses import dataclass
import os
from pathlib import Path
import platform
import shutil
import socket
import stat
import subprocess
import tempfile


@dataclass(frozen=True)
class CommandResult:
    code: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False


def run_command(argv, timeout=8):
    """Run an argv without a shell, with a timeout and capped retained output."""
    try:
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            try:
                proc = subprocess.run(list(argv), stdout=out, stderr=err, timeout=timeout,
                                      env={**os.environ, "LC_ALL": "C"}, check=False)
                code, timed_out = proc.returncode, False
            except subprocess.TimeoutExpired:
                code, timed_out = 124, True
            out.seek(0)
            err.seek(0)
            return CommandResult(code, out.read(65536).decode(errors="replace"),
                                 err.read(65536).decode(errors="replace"), timed_out)
    except FileNotFoundError:
        return CommandResult(127, stderr="utility unavailable")
    except PermissionError:
        return CommandResult(126, stderr="permission denied")


def _read(path):
    try:
        return Path(path).read_text().strip()
    except (OSError, UnicodeError):
        return ""


def enumerate_usb(root=Path("/sys/bus/usb/devices")):
    devices = []
    for path in sorted(root.glob("*")):
        if _read(path / "idVendor").lower() != "05ac":
            continue
        product = _read(path / "product")
        product_id = _read(path / "idProduct").lower()
        # Apple also makes keyboards and hubs. Do not call those an iPhone.
        candidate = any(name in product.lower() for name in ("iphone", "ipad", "ipod"))
        candidate = candidate or product_id.startswith("12")
        bus, dev = _read(path / "busnum"), _read(path / "devnum")
        node = Path(f"/dev/bus/usb/{int(bus):03d}/{int(dev):03d}") if bus.isdigit() and dev.isdigit() else None
        devices.append({"product_id": product_id, "ios_candidate": candidate,
                        "usb_access": bool(node and os.access(node, os.R_OK | os.W_OK))})
    return devices


def inspect_host(runner=None):
    runner = runner or run_command
    release = {}
    for line in _read("/etc/os-release").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            if key in ("ID", "VERSION_ID", "PRETTY_NAME"):
                release[key.lower()] = value.strip('"')
    properties = ("ActiveState", "SubState", "ExecStart", "User", "Group", "FragmentPath",
                  "DropInPaths", "Result", "MainPID")
    unit = runner(["systemctl", "show", "usbmuxd.service", *[f"--property={p}" for p in properties]], timeout=4)
    systemd = dict(line.split("=", 1) for line in unit.stdout.splitlines() if "=" in line)
    packages = runner(["dpkg-query", "-W", "-f=${binary:Package}\t${Version}\t${db:Status-Status}\n", "usbmuxd",
                       "libusbmuxd*", "libimobiledevice*", "libplist*"], timeout=4)
    package_versions = {}
    for line in packages.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[2] == "installed":
            package_versions[parts[0]] = parts[1]
    processes = []
    for proc in Path("/proc").glob("[0-9]*"):
        if _read(proc / "comm") == "usbmuxd":
            try:
                executable = os.readlink(proc / "exe")
            except OSError:
                executable = "unavailable"
            processes.append({"pid": int(proc.name), "executable": executable})
    socket_status = "missing"
    try:
        if stat.S_ISSOCK(Path("/run/usbmuxd").stat().st_mode):
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(1)
                connection.connect("/run/usbmuxd")
            socket_status = "working"
        else:
            socket_status = "invalid"
    except PermissionError:
        socket_status = "permission_denied"
    except FileNotFoundError:
        pass
    except OSError:
        socket_status = "unreachable"
    journal = runner(["journalctl", "-u", "usbmuxd.service", "--since=-2min", "-n", "80", "--no-pager", "-o", "cat"], timeout=4)
    # Retain signatures, never raw logs containing device identifiers.
    log = journal.stdout.lower()
    preflight = "preflight" in log and ("response_pending" in log or "lockdown error -8" in log)
    daemon_help = runner(["/usr/sbin/usbmuxd", "--help"], timeout=2) if Path("/usr/sbin/usbmuxd").is_file() else CommandResult(127)
    udev_rules = sorted({p.name for directory in ("/usr/lib/udev/rules.d", "/lib/udev/rules.d", "/etc/udev/rules.d")
                         for p in Path(directory).glob("*usbmuxd*")})
    return {"distribution": release, "architecture": platform.machine(), "packages": package_versions,
            "systemd": systemd, "systemd_available": unit.code == 0, "processes": processes,
            "socket": socket_status, "usb_devices": enumerate_usb(), "udev_rules": udev_rules,
            "tools": {name: shutil.which(name) for name in ("idevice_id", "idevicepair", "ideviceinfo")},
            "preflight_pending_signature": preflight, "journal_available": journal.code == 0,
            "conflicting_daemons": len(processes) > 1,
            "no_preflight_option_supported": None if daemon_help.code == 127 else "--no-preflight" in (daemon_help.stdout + daemon_help.stderr)}
