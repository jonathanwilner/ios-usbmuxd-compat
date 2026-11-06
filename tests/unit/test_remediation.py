import hashlib
import json
import platform
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ios_usbmuxd_compat.remediation.engine import Engine, RepairError, digest, select
from ios_usbmuxd_compat.remediation.helper import main

UNIT = '[Service]\nUser=usbmux\nExecStart=/usr/sbin/usbmuxd --user usbmux --systemd\n'
HOST = {'distribution': {'id': 'debian', 'version_id': '12'}, 'socket': 'missing', 'packages': {'usbmuxd': '1.1.1'}}


def report(status='daemon_failure'):
    return {'status': status, 'host': HOST, 'daemon_healthy': status != 'daemon_failure'}


class Repairs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.calls = []
        self.results = [report(), report('ready')]
        self.engine = Engine(root / 'state', root / 'systemd' / '50-ios-usbmuxd-compat.conf', root / 'lib', self.host_run, self.diagnose, False)

    def host_run(self, args):
        self.calls.append(args)
        if args[1] == 'cat':
            return UNIT
        if args[1] == 'show' and args[-1] == '--property=ActiveState,Result,MainPID':
            return 'ActiveState=active\nResult=success\nMainPID=123'
        if args[1] == 'show':
            return 'FragmentPath=/lib/systemd/system/usbmuxd.service\nDropInPaths=\nUser=usbmux\n'
        return ''

    def diagnose(self, **kwargs):
        return self.results.pop(0)

    def candidate(self, kind='daemon'):
        folder = self.engine.base / kind
        folder.mkdir(parents=True)
        names = ['usbmuxd'] if kind == 'daemon' else ['bin/idevice_id', 'bin/idevicepair', 'bin/ideviceinfo']
        hashes = {}
        for name in names:
            path = folder / name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(b'\x7fELF\x02\x01' + bytes(12) + (62 if platform.machine() == 'x86_64' else 183).to_bytes(2, 'little'))
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        data = {'schema_version': 1, 'validated': True, 'architecture': platform.machine(), 'distribution': 'debian', 'release': '12', 'repair_statuses': ['daemon_failure', 'client_library_incompatible'], 'provenance': 'fixture only', 'hardware_validation': 'fixture only', 'package_versions': HOST['packages'], 'sha256': hashes, 'stock_unit_sha256': digest(UNIT.encode()), 'failure_match': {'socket': HOST['socket'], 'packages': HOST['packages']}}
        (folder / 'manifest.json').write_text(json.dumps(data))
        return folder

    def test_stock_healthy_no_change(self):
        self.results = [report('ready')]
        self.assertFalse(self.engine.repair()['changed'])
        self.assertFalse(self.calls)

    def test_pending_and_trust_no_change(self):
        for state in ('pending_device', 'awaiting_trust', 'locked', 'permission_denied', 'preflight_failure'):
            self.results = [report(state)]
            self.assertFalse(self.engine.repair()['changed'])
        self.assertFalse(self.calls)

    def test_unknown_candidate_fails_closed(self):
        with self.assertRaises(FileNotFoundError):
            self.engine.repair()
        self.assertFalse(self.engine.dropin.exists())

    def test_validated_replacement_and_rollback(self):
        self.candidate()
        self.assertEqual(self.engine.repair()['status'], 'ready')
        content = self.engine.dropin.read_text()
        self.assertIn('--user usbmux --systemd', content)
        self.assertNotIn('User=', content)
        self.assertEqual(self.engine.rollback()['status'], 'rolled_back')
        self.assertFalse(self.engine.dropin.exists())

    def test_failed_replacement_rolls_back(self):
        self.candidate()
        self.results = [report(), report()]
        self.assertTrue(self.engine.repair()['rolled_back'])
        self.assertFalse(self.engine.dropin.exists())

    def test_unplug_is_pending_validation(self):
        self.candidate()
        self.results = [report(), report('pending_device')]
        self.assertEqual(self.engine.repair()['status'], 'pending_device')
        self.assertTrue(self.engine.dropin.exists())

    def test_private_client_repair(self):
        self.candidate('client')
        self.results = [report('client_library_incompatible'), report('ready')]
        self.assertEqual(self.engine.repair()['strategy'], 'private_client')
        self.assertFalse(self.calls)

    def test_admin_override_rejected(self):
        self.candidate()
        original = self.engine.run
        self.engine.run = lambda args: 'FragmentPath=/lib/systemd/system/usbmuxd.service\nDropInPaths=/etc/admin.conf' if args[1] == 'show' else original(args)
        with self.assertRaises(RepairError):
            self.engine.repair()

    def test_distribution_upgrade_rejects_stale_unit(self):
        folder = self.candidate()
        path = folder / 'manifest.json'
        data = json.loads(path.read_text())
        data['stock_unit_sha256'] = 'stale'
        path.write_text(json.dumps(data))
        with self.assertRaises(RepairError):
            self.engine.repair()

    def test_concurrency(self):
        with self.engine.lock():
            with self.assertRaises(RepairError):
                with self.engine.lock():
                    pass

    def test_interrupted_operation_restored(self):
        self.engine.state.mkdir()
        self.engine.save({'phase': 'prepared'})
        self.assertEqual(self.engine.repair()['status'], 'rolled_back')
        self.assertFalse(self.calls)

    def test_modified_override_preserved(self):
        self.candidate()
        self.engine.repair()
        self.engine.dropin.write_text('administrator change')
        with self.assertRaises(RepairError):
            self.engine.rollback()
        self.assertEqual(self.engine.dropin.read_text(), 'administrator change')

    def test_bad_manifest_paths(self):
        folder = self.candidate()
        path = folder / 'manifest.json'
        data = json.loads(path.read_text())
        data['sha256']['../elsewhere'] = 'x'
        path.write_text(json.dumps(data))
        with self.assertRaises(RepairError):
            self.engine.repair()

    def test_corrupt_binary(self):
        folder = self.candidate()
        (folder / 'usbmuxd').write_text('wrong')
        with self.assertRaises(RepairError):
            self.engine.repair()

    def test_helper_misuse(self):
        for args in ([], ['repair', '/tmp/malware'], ['sh'], ['--help'], ['repair\nrollback']):
            self.assertEqual(main(args), 2)
        with patch('os.geteuid', return_value=1000):
            self.assertEqual(main(['repair']), 3)

    def test_no_version_only_repair(self):
        self.assertEqual(select(report('ready'))['strategy'], 'none')

    def test_unplug_clean_inactive_not_rollback(self):
        self.candidate()
        self.results = [report(), report('pending_device')]
        self.results[-1]['daemon_healthy'] = False
        original = self.engine.run
        self.engine.run = lambda args: 'ActiveState=inactive\nResult=success\nMainPID=0' if args[-1] == '--property=ActiveState,Result,MainPID' else original(args)
        self.assertEqual(self.engine.repair()['status'], 'pending_device')
        self.assertTrue(self.engine.dropin.exists())

    def test_failed_service_with_unplug_rolls_back(self):
        self.candidate()
        self.results = [report(), report('pending_device')]
        original = self.engine.run
        self.engine.run = lambda args: 'ActiveState=failed\nResult=exit-code\nMainPID=0' if args[-1] == '--property=ActiveState,Result,MainPID' else original(args)
        self.assertTrue(self.engine.repair()['rolled_back'])

    def test_malformed_manifest(self):
        folder = self.candidate()
        (folder / 'manifest.json').write_text('[]')
        with self.assertRaises(RepairError):
            self.engine.repair()

    def test_unlisted_library_rejected(self):
        folder = self.candidate('client')
        (folder / 'untracked.so').write_bytes(b'untracked')
        self.results = [report('client_library_incompatible')]
        with self.assertRaises(RepairError):
            self.engine.repair()

    def test_client_failure_preserves_active_daemon_journal(self):
        self.candidate()
        self.engine.repair()
        original = self.engine.read()
        self.results = [report('client_library_incompatible')]
        with self.assertRaises(RepairError):
            self.engine.repair()
        self.assertEqual(self.engine.read(), original)
        self.assertEqual(self.engine.rollback()['status'], 'rolled_back')

    def test_verified_protocol_failure_rolls_back(self):
        self.candidate()
        self.results = [report(), report('pairing_protocol_error')]
        self.assertTrue(self.engine.repair()['rolled_back'])

    def test_selected_private_without_device_stays_pending(self):
        from ios_usbmuxd_compat.remediation.engine import diagnose_selected
        with patch('ios_usbmuxd_compat.diagnose', return_value=report('pending_device')):
            with patch('ios_usbmuxd_compat.remediation.engine.status', return_value={'phase': 'private_client'}):
                self.assertEqual(diagnose_selected()['status'], 'pending_device')

    def test_pkexec_fixed_arguments(self):
        from ios_usbmuxd_compat.remediation.engine import rollback
        from types import SimpleNamespace
        with patch('os.geteuid', return_value=1000), patch('subprocess.run', return_value=SimpleNamespace(stdout='{"status":"rolled_back"}')) as call:
            self.assertEqual(rollback()['status'], 'rolled_back')
            self.assertEqual(call.call_args.args[0], ['/usr/bin/pkexec', '/usr/lib/ios-usbmuxd-compat/helper', 'rollback'])

    def test_unmanaged_single_daemon_blocks_activation(self):
        self.candidate()
        self.results[0] = {**report(), 'host': {**HOST, 'processes': [{'pid': 123, 'executable': '/usr/sbin/usbmuxd'}]}}
        with self.assertRaisesRegex(RepairError, 'unmanaged'):
            self.engine.repair()
        self.assertFalse(self.engine.dropin.exists())

    def test_public_status_excludes_effective_configuration(self):
        self.candidate()
        self.engine.repair()
        self.assertEqual((self.engine.state / 'state.json').stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.engine.state / 'public.json').stat().st_mode & 0o777, 0o644)
        public = self.engine.public_status()
        self.assertEqual(set(public), {'status', 'phase', 'schema_version'})
        self.assertNotIn('effective_unit', public)
        self.assertEqual(public['phase'], 'active')

    def test_private_client_abi_environment_change_rejected(self):
        self.candidate('client')
        self.results = [{**report('client_library_incompatible'), 'host': {**HOST, 'packages': {'usbmuxd': 'upgraded'}}}]
        with self.assertRaisesRegex(RepairError, 'environment changed'):
            self.engine.repair()
