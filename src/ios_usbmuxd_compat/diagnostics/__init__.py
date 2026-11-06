"""Version 1 diagnostic API. Inspection does not pair or change the host."""
import re
import time
from ..system import inspect_host, run_command
from ..probes import LockdownProbe, classify_error

ACTIONS = {
    "ready": ("none", "iOS lockdown and all application probes succeeded."),
    "pending_device": ("connect_device", "Connect an unlocked iPhone with a data-capable USB cable."),
    "awaiting_trust": ("accept_trust", "Accept Trust on the iPhone, then run pair and check again."),
    "device_locked": ("unlock_device", "Unlock the iPhone and repeat the check."),
    "pairing_required": ("pair_device", "Run iphone-connectivity-demo pair and accept Trust on the iPhone."),
    "trust_rejected": ("accept_trust", "Reconnect the iPhone and explicitly approve Trust when you are ready."),
    "permission_denied": ("review_permissions", "Review distribution USB and socket permissions; administrator approval may be required."),
    "client_library_incompatible": ("client_remediation", "Try a validated private client bundle; preserve system libraries."),
    "daemon_failure": ("daemon_remediation", "Inspect daemon startup and socket health. Replacement requires a validated compatible artifact."),
    "preflight_failure": ("retry_after_trust", "A recent preflight pending signature was observed. Accept Trust, reconnect, and retry; this is not proof of a daemon defect."),
    "device_lost": ("reconnect_device", "The device disappeared during initialization. Reconnect and repeat the check."),
    "preflight_timeout": ("retry_after_trust", "The operation timed out. Unlock the phone, review Trust, and retry."),
    "manual_intervention_required": ("inspect_system", "Inspect the reported host and device state before changing the daemon."),
    "application_protocol_failure": ("inspect_application", "The application probe failed after lockdown connectivity succeeded."),
    "pairing_protocol_error": ("inspect_pairing", "Pairing validation failed with an unrecognized protocol error; preserve pairing records."),
}


def enumerate_transport(runner, tools):
    result = runner([tools["idevice_id"], "-l"], timeout=5)
    ids = [line.strip() for line in result.stdout.splitlines()
           if re.fullmatch(r"[A-Fa-f0-9-]{16,64}", line.strip())]
    return result, list(dict.fromkeys(ids)) if result.code == 0 else []


def diagnose(*, probes=(), runner=None, host=None, client_dir=None, client_mode="system", retries=1, budget_seconds=60):
    """Inspect up to 16 devices; one bounded transport retry by default.

    client_dir is trusted application configuration, never accepted by the root helper.
    Plug-ins execute in the caller process and must use bounded I/O.
    """
    from pathlib import Path
    if client_mode not in ("system", "private"):
        raise ValueError("client_mode must be system or private")
    if client_mode == "private":
        client_dir = "/usr/lib/ios-usbmuxd-compat/client/bin"
    underlying_runner = runner or run_command
    deadline = time.monotonic() + min(max(budget_seconds, 1), 120)
    def runner(argv, timeout=8):
        from ..system import CommandResult
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return CommandResult(124, timed_out=True)
        return underlying_runner(argv, timeout=min(timeout, remaining))
    host = inspect_host(runner) if host is None else host
    tools = {name: str(Path(client_dir) / name) if client_dir else name
             for name in ("idevice_id", "idevicepair", "ideviceinfo")}
    report = {"schema_version": 1, "status": "pending_device", "device_connected": False,
              "daemon_healthy": host.get("socket") == "working" and not host.get("conflicting_daemons", False),
              "usbmux_transport": "not_tested", "pairing": "not_tested",
              "application_protocol": "not_tested", "recommended_action": "connect_device",
              "requires_admin": False, "message": "", "host": host, "devices": []}
    usb_present = any(d.get("ios_candidate") for d in host.get("usb_devices", []))
    result, ids = enumerate_transport(runner, tools)
    if usb_present and not ids and result.code == 0 and retries:
        time.sleep(0.2)
        result, ids = enumerate_transport(runner, tools)
    report["device_connected"] = usb_present or bool(ids)
    if not report["device_connected"]:
        status = "pending_device"
    elif len(ids) > 16:
        report["usbmux_transport"] = "working"
        report["device_limit_exceeded"] = True
        status = "manual_intervention_required"
    elif host.get("conflicting_daemons"):
        status = "manual_intervention_required"
    elif host.get("socket") == "permission_denied" or (result.code and classify_error(result) == "permission_denied"):
        status = "permission_denied"
    elif not ids:
        report["usbmux_transport"] = "unavailable"
        if result.code and classify_error(result) == "client_library_incompatible":
            status = "client_library_incompatible"
        elif result.code == 127:
            status = "manual_intervention_required"
        elif host.get("preflight_pending_signature"):
            status = "preflight_failure"
        elif host.get("socket") in ("missing", "unreachable", "invalid"):
            status = "daemon_failure"
        else:
            status = "manual_intervention_required"
    else:
        report["usbmux_transport"] = "working"
        for index, device_id in enumerate(ids, 1):
            pairing = runner([tools["idevicepair"], "-u", device_id, "validate"], timeout=8)
            pair_status = "paired" if pairing.code == 0 and "SUCCESS" in pairing.stdout else classify_error(pairing)
            device = {"id": f"device-{index}", "pairing": pair_status, "application_protocol": "not_tested", "probes": []}
            device["status"] = pair_status if pair_status != "paired" else "ready"
            if pair_status == "paired":
                for probe in (LockdownProbe(), *probes):
                    try:
                        outcome = probe.run(device_id, runner, tools)
                        # Plugin messages are application-owned; do not log them automatically.
                        device["probes"].append({"name": probe.name, "status": outcome.status})
                        if outcome.status != "working":
                            device["status"] = outcome.status if probe.name == "lockdown" else "application_protocol_failure"
                            break
                    except Exception:
                        device["status"] = "application_protocol_failure"
                        device["probes"].append({"name": probe.name, "status": "probe_error"})
                        break
                device["application_protocol"] = "working" if device["status"] == "ready" else "failed"
            if device["status"] not in ACTIONS:
                device["status"] = "manual_intervention_required"
            report["devices"].append(device)
        status = next((d["status"] for d in report["devices"] if d["status"] != "ready"), "ready")
        report["pairing"] = report["devices"][0]["pairing"] if len(ids) == 1 else "per_device"
        report["application_protocol"] = report["devices"][0]["application_protocol"] if len(ids) == 1 else ("working" if status == "ready" else "per_device")
    report["status"] = status
    report["recommended_action"], report["message"] = ACTIONS[status]
    report["requires_admin"] = status in ("daemon_failure", "permission_denied", "client_library_incompatible")
    return report


def pair_devices(*, runner=None, host=None, client_mode="system"):
    """Explicitly request pairing. Never erase records or bypass Trust."""
    from pathlib import Path
    runner = runner or run_command
    if client_mode not in ("system", "private"):
        raise ValueError("client_mode must be system or private")
    tools = {name: str(Path("/usr/lib/ios-usbmuxd-compat/client/bin") / name) if client_mode == "private" else name
             for name in ("idevice_id", "idevicepair")}
    listing, ids = enumerate_transport(runner, tools)
    if len(ids) > 16:
        return {"schema_version": 1, "status": "manual_intervention_required", "devices": [],
                "message": "More than 16 devices are attached. Disconnect extra devices before pairing."}
    if not ids:
        inspected = inspect_host(runner) if host is None else host
        attached = any(d.get("ios_candidate") for d in inspected.get("usb_devices", []))
        if not attached:
            state = "pending_device"
        elif listing.code:
            state = classify_error(listing)
            if state == "utility_missing":
                state = "manual_intervention_required"
        else:
            state = "manual_intervention_required"
        return {"schema_version": 1, "status": state, "devices": [],
                "message": ACTIONS.get(state, ACTIONS["manual_intervention_required"])[1]}
    results = []
    deadline = time.monotonic() + 60
    for index, device_id in enumerate(ids, 1):
        from ..system import CommandResult
        remaining = deadline - time.monotonic()
        result = runner([tools["idevicepair"], "-u", device_id, "pair"], timeout=min(15, remaining)) if remaining > 0 else CommandResult(124, timed_out=True)
        state = "paired" if result.code == 0 and "SUCCESS" in result.stdout else classify_error(result)
        results.append({"id": f"device-{index}", "pairing": state})
    state = next((d["pairing"] for d in results if d["pairing"] != "paired"), "pairing_requested")
    return {"schema_version": 1, "status": state, "devices": results}
