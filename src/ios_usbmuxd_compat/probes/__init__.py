"""Application probes are trusted application code, never privileged plugins."""
from dataclasses import dataclass
from typing import Protocol, Callable


@dataclass(frozen=True)
class ProbeResult:
    status: str
    message: str


class Probe(Protocol):
    name: str

    def run(self, device_id: str, runner: Callable, tools: dict) -> ProbeResult:
        """Use bounded runner calls; never include device identifiers in messages."""
        ...


def classify_error(result):
    text = (result.stdout + " " + result.stderr).lower()
    if "permission denied" in text or "access denied" in text:
        return "permission_denied"
    if any(s in text for s in ("password protected", "password_protected", "device locked", "device is locked", "enter the passcode")):
        return "device_locked"
    if any(s in text for s in ("pairing dialog response pending", "pairing_dialog_response_pending", "please accept the trust")):
        return "awaiting_trust"
    if any(s in text for s in ("user denied", "user_denied", "trust denied", "trust rejected")):
        return "trust_rejected"
    if any(s in text for s in ("not paired", "invalid host", "invalid_host", "pairing required", "please pair")):
        return "pairing_required"
    if any(s in text for s in ("symbol lookup error", "undefined symbol", "version mismatch", "error while loading shared libraries")):
        return "client_library_incompatible"
    if any(s in text for s in ("no device found", "device disconnected", "device lost")):
        return "device_lost"
    if result.timed_out:
        return "preflight_timeout"
    if result.code == 127:
        return "utility_missing"
    return "pairing_protocol_error"


class LockdownProbe:
    name = "lockdown"

    def run(self, device_id, runner, tools):
        result = runner([tools["ideviceinfo"], "-u", device_id, "-k", "ProductVersion"], timeout=8)
        # Exit status alone is not enough: this query must return a version value.
        import re
        if result.code == 0 and re.fullmatch(r"\d+(?:\.\d+){1,3}", result.stdout.strip()):
            return ProbeResult("working", "Read ProductVersion through iOS lockdown.")
        return ProbeResult(classify_error(result), "Lockdown query did not complete; inspect pairing status.")
