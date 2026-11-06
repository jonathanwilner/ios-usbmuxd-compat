"""Example command-line application. Privilege is restricted to repair helper."""
import argparse
import json
import sys
from . import inspect_host
from .remediation import diagnose_selected as diagnose, pair_selected as pair_devices


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect real iPhone USB connectivity without replacing a healthy daemon.")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "devices", "pair", "repair", "status", "rollback", "host-check"):
        sub = commands.add_parser(command)
        sub.add_argument("--verbose", action="store_true", help="Show sanitized host and probe details on stderr")
        sub.add_argument("--json", action="store_true", help="Emit a versioned JSON result without device identifiers")
        if command == "repair":
            sub.add_argument("--dry-run", action="store_true")
    arguments = sys.argv[1:] if argv is None else argv
    args = parser.parse_args(arguments or ["check"])
    try:
        if args.command in ("check", "devices"):
            result = diagnose()
        elif args.command == "host-check":
            result = {"schema_version": 1, "status": "host_inspected", "host": inspect_host()}
        elif args.command == "pair":
            result = pair_devices()
        else:
            from . import remediation
            if args.command == "repair":
                result = remediation.repair(dry_run=args.dry_run)
            else:
                result = getattr(remediation, args.command)()
    except (OSError, ValueError, RuntimeError) as exc:
        # Paths and exception text may contain private state. Show type only.
        result = {"schema_version": 1, "status": "manual_intervention_required",
                  "message": f"Operation could not complete ({type(exc).__name__}); inspect the installation."}
    result.setdefault("schema_version", 1)
    if args.command == "status" and result.get("phase") in ("prepared", "activating"):
        result["message"] = "An interrupted repair needs recovery. Run iphone-connectivity-demo rollback."
    if args.verbose:
        print(json.dumps({"host": result.get("host", {}), "devices": result.get("devices", []),
                          "limits": {"diagnostic_budget_seconds": 60, "maximum_devices": 16},
                          "privacy": "Raw device IDs and protocol logs are omitted."}, indent=2), file=sys.stderr)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Status: {result.get('status', 'unknown')}")
        if result.get("message"):
            print(result["message"])
        if result.get("recommended_action"):
            print(f"Next action: {result['recommended_action']}")
        host = result.get("host", {})
        for daemon in host.get("processes", []):
            print(f"Daemon: {daemon['executable']} (PID {daemon['pid']})")
        if host:
            print(f"usbmuxd socket: {host.get('socket', 'unknown')}")
        for package, version in sorted(host.get("packages", {}).items()):
            print(f"Package: {package} {version}")
        for device in result.get("devices", []):
            print(f"{device['id']}: pairing={device.get('pairing', 'unknown')}, protocol={device.get('application_protocol', 'not_tested')}")
        if args.command in ("repair", "rollback", "status"):
            print(json.dumps(result, indent=2, sort_keys=True))
    benign = {"ready", "pending_device", "awaiting_trust", "device_locked", "pairing_required", "pairing_requested",
              "stock", "private_client", "host_inspected", "no_change", "dry_run", "rolled_back", "idle", "active", "success", "not_needed"}
    return 0 if result.get("status") in benign else 1


if __name__ == "__main__":
    raise SystemExit(main())
