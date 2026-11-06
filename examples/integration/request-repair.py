#!/usr/bin/env python3
"""Example application action triggered by the user's Repair button."""
import subprocess


def request_repair():
    # The installed CLI requests PolicyKit authorization for its fixed helper.
    # Never interpolate report fields or accept a caller's executable path.
    try:
        result = subprocess.run(["/usr/bin/iphone-connectivity-demo", "repair"],
                                timeout=120, check=False)
    except subprocess.TimeoutExpired:
        return "Repair timed out. Check status before retrying."
    if result.returncode:
        return "Repair needs attention. Review diagnostics and administrator approval."
    return "Repair action completed. Check the iPhone connection again."


if __name__ == "__main__":
    print(request_repair())
