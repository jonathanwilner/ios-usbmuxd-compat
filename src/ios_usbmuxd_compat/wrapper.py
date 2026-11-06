"""Unprivileged app-launch adapter. Application argv never enters the helper."""
import argparse
import os
import sys

from .remediation import diagnose_selected, repair, select


def prepare(*, probes=(), allow_repair=False):
    """Check an app's stack, optionally request fixed-action repair, then recheck.

    Custom probes remain in this process and never authorize privileged repair.
    The helper independently diagnoses the stock stack before making changes.
    """
    report = diagnose_selected(probes=probes)
    if allow_repair and select(report)['strategy'] in ('private_client', 'validated_daemon'):
        outcome = repair()
        report = diagnose_selected(probes=probes)
        report['repair_result'] = outcome
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description='Check iPhone connectivity and launch your app as the current user.')
    parser.add_argument('--repair', action='store_true', help='Request a supported repair through PolicyKit when needed')
    parser.add_argument('--allow-pending-device', action='store_true', help='Also launch without a phone; app must recheck after attachment')
    parser.add_argument('command', nargs=argparse.REMAINDER, help='-- /path/to/your-app [arguments]')
    args = parser.parse_args(argv)
    command = args.command
    if command[:1] == ['--']:
        command = command[1:]
    if not command or not command[0]:
        parser.error('Supply an application after --')
    # Never make a desktop app run as root because its launcher was elevated.
    if os.geteuid() == 0:
        print('Run the app wrapper as your ordinary user. Repair uses PolicyKit separately.', file=sys.stderr)
        return 77
    try:
        report = prepare(allow_repair=args.repair)
    except (OSError, ValueError, RuntimeError):
        print('Compatibility check could not complete. Run ios-usbmuxd-compat check --json.', file=sys.stderr)
        return 70
    state = report.get('status', 'unknown')
    permitted = state == 'ready' or (state == 'pending_device' and args.allow_pending_device)
    if not permitted:
        print(f'iPhone connectivity: {state}. Run ios-usbmuxd-compat check for guidance.', file=sys.stderr)
        return 75
    env = os.environ.copy()
    env['IOS_USBMUXD_COMPAT_STATUS'] = state
    # argv is executed directly, without a shell or privileged helper.
    try:
        os.execvpe(command[0], command, env)
    except OSError:
        print('Application could not be launched. Check its installed path and permissions.', file=sys.stderr)
        return 69


if __name__ == '__main__':
    raise SystemExit(main())
