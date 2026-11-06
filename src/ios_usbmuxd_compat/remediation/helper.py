"""Fixed-action privileged entrypoint. No paths, commands, JSON, or plugins accepted."""
import json
import os
import sys
from .engine import ENV, Engine, RepairError


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1 or args[0] not in ('repair', 'rollback', 'status', 'host-check'):
        print(json.dumps({'status': 'manual_intervention_required', 'message': 'Exactly one supported action required'}))
        return 2
    if os.geteuid() != 0:
        print(json.dumps({'status': 'manual_intervention_required', 'message': 'Administrator authorization required'}))
        return 3
    os.environ.clear()
    os.environ.update(ENV)
    os.umask(0o022)
    os.chdir('/')
    try:
        engine = Engine()
        if args[0] == 'host-check':
            from ios_usbmuxd_compat import inspect_host
            result = {'status': 'pending_device', 'host': inspect_host()}
        else:
            result = engine.public_status() if args[0] == 'status' else getattr(engine, args[0])()
    except (RepairError, OSError, ValueError) as exc:
        result = {'status': 'manual_intervention_required', 'message': str(exc)}
    print(json.dumps(result, sort_keys=True))
    return 1 if result.get('status') in ('repair_failed', 'manual_intervention_required') else 0


if __name__ == '__main__':
    sys.exit(main())
