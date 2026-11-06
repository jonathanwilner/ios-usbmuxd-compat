#!/usr/bin/env python3
"""Read a versioned diagnostic result from stdin. Never execute report contents."""
import json
import sys


def notification(report):
    if report.get("schema_version") != 1:
        raise ValueError("Unsupported diagnostics schema version")
    messages = {
        "ready": "iPhone connection is ready.",
        "pending_device": "Connect an iPhone when you need this feature.",
        "awaiting_trust": "Unlock your iPhone and accept its Trust prompt.",
        "permission_denied": "An administrator must review USB or socket permissions.",
    }
    return messages.get(report.get("status"), "Open connection diagnostics for the next action.")


if __name__ == "__main__":
    try:
        data = sys.stdin.read(1024 * 1024 + 1)
        if len(data) > 1024 * 1024:
            raise ValueError("Report exceeds size limit")
        print(notification(json.loads(data)))
    except (ValueError, TypeError, AttributeError) as error:
        sys.exit(str(error))
