import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
from ios_usbmuxd_compat import diagnose, ProbeResult, pair_devices
from ios_usbmuxd_compat.cli import main
from ios_usbmuxd_compat.system import CommandResult, enumerate_usb, run_command

DEVICE = '0123456789abcdef0123456789abcdef01234567'


def host(connected=True, **changes):
    result = {'socket':'working', 'conflicting_daemons':False,
              'usb_devices':[{'ios_candidate':True,'usb_access':False}] if connected else [],
              'systemd':{},'packages':{},'processes':[], 'preflight_pending_signature':False}
    result.update(changes)
    return result


class Runner:
    def __init__(self, ids=DEVICE, pair=None, info=None, listing=None):
        self.ids, self.pair, self.info, self.listing = ids, pair, info, listing
        self.calls = []

    def __call__(self, argv, timeout=8):
        self.calls.append((argv,timeout))
        name=Path(argv[0]).name
        if name == 'idevice_id':
            return self.listing or CommandResult(0,self.ids+'\n')
        if name == 'idevicepair':
            return self.pair or CommandResult(0,'SUCCESS: Validated pairing with device '+DEVICE)
        if name == 'ideviceinfo':
            return self.info or CommandResult(0,'26.1\n')
        raise AssertionError(argv)


class DiagnosticsTests(unittest.TestCase):
    def check(self, runner=None, **changes):
        return diagnose(runner=runner or Runner(),host=host(**changes),retries=0)

    def test_working_stock_daemon(self):
        runner=Runner()
        result=self.check(runner)
        self.assertEqual(result['status'],'ready')
        self.assertEqual(result['application_protocol'],'working')
        self.assertTrue(any(call[0][-2:]==['-k','ProductVersion'] for call in runner.calls))
        self.assertTrue(all(call[0][-1]!='pair' for call in runner.calls))

    def test_no_connected_device(self):
        result=self.check(Runner(ids=''),connected=False,socket='missing')
        self.assertEqual(result['status'],'pending_device')
        self.assertFalse(result['requires_admin'])

    def test_new_device_after_installation(self):
        runner=Runner(ids='')
        self.assertEqual(self.check(runner,connected=False)['status'],'pending_device')
        runner.ids=DEVICE
        self.assertEqual(self.check(runner)['status'],'ready')

    def test_usb_visible_transport_invisible_unknown(self):
        self.assertEqual(self.check(Runner(ids=''))['status'],'manual_intervention_required')

    def test_usb_visible_transport_daemon_failure(self):
        self.assertEqual(self.check(Runner(ids=''),socket='missing')['status'],'daemon_failure')

    def test_trust_states(self):
        for message,state in [('Please pair with the device','pairing_required'),
                              ('Pairing dialog response pending (-19)','awaiting_trust'),
                              ('LOCKDOWN_E_PAIRING_DIALOG_RESPONSE_PENDING (-8)','awaiting_trust'),
                              ('User denied pairing','trust_rejected'),
                              ('Device is locked','device_locked'),
                              ('Password protected','device_locked'),
                              ('No device found','device_lost'),
                              ('Invalid host ID','pairing_required'),
                              ('Unknown lockdown error','pairing_protocol_error')]:
            with self.subTest(message=message):
                result=self.check(Runner(pair=CommandResult(1,stderr=message)))
                self.assertEqual(result['status'],state)
                self.assertEqual(result['application_protocol'],'not_tested')

    def test_preflight_timeout(self):
        self.assertEqual(self.check(Runner(pair=CommandResult(124,timed_out=True)))['status'],'preflight_timeout')

    def test_preflight_signature_not_automatic_daemon_repair(self):
        result=self.check(Runner(ids=''),preflight_pending_signature=True)
        self.assertEqual(result['status'],'preflight_failure')
        self.assertEqual(result['recommended_action'],'retry_after_trust')

    def test_client_abi_failure(self):
        result=self.check(Runner(listing=CommandResult(127,stderr='symbol lookup error: undefined symbol: x')))
        self.assertEqual(result['status'],'client_library_incompatible')
        self.assertTrue(result['requires_admin'])

    def test_private_client_mode(self):
        runner=Runner()
        self.assertEqual(diagnose(runner=runner,host=host(),client_mode='private')['status'],'ready')
        self.assertTrue(all(c[0][0].startswith('/usr/lib/ios-usbmuxd-compat/client/bin/') for c in runner.calls))
        with self.assertRaises(ValueError):
            diagnose(client_mode='../../bin')

    def test_multiple_devices(self):
        report=self.check(Runner(ids=DEVICE+'\n'+DEVICE+'a'))
        self.assertEqual(len(report['devices']),2)
        self.assertEqual(report['pairing'],'per_device')
        self.assertNotIn(DEVICE,json.dumps(report))

    def test_usb_permission_is_not_required_when_daemon_works(self):
        self.assertEqual(self.check()['status'],'ready')

    def test_missing_socket_permission(self):
        self.assertEqual(self.check(socket='permission_denied')['status'],'permission_denied')

    def test_multiple_daemons(self):
        self.assertEqual(self.check(conflicting_daemons=True)['status'],'manual_intervention_required')

    def test_missing_utility(self):
        self.assertEqual(self.check(Runner(listing=CommandResult(127)))['status'],'manual_intervention_required')

    def test_exit_zero_empty_query_is_not_connectivity(self):
        self.assertNotEqual(self.check(Runner(info=CommandResult(0,'')))['status'],'ready')

    def test_plugin_success_and_failure(self):
        class Custom:
            name='example'
            def run(self,device_id,runner,tools):
                self_seen.append(device_id)
                return ProbeResult('working','safe')
        self_seen=[]
        report=diagnose(host=host(),runner=Runner(),probes=[Custom()])
        self.assertEqual(report['status'],'ready')
        self.assertEqual(self_seen,[DEVICE])
        class Failing:
            name='failure'
            def run(self,*args):
                raise RuntimeError('private value')
        report=diagnose(host=host(),runner=Runner(),probes=[Failing()])
        self.assertEqual(report['status'],'application_protocol_failure')
        self.assertNotIn('private value',json.dumps(report))

    def test_explicit_pair_uses_no_shell_and_preserves_records(self):
        runner=Runner()
        result=pair_devices(runner=runner)
        self.assertEqual(result['devices'][0]['pairing'],'paired')
        self.assertEqual(runner.calls[-1][0],['idevicepair','-u',DEVICE,'pair'])
        self.assertNotIn(DEVICE,json.dumps(result))

    def test_malformed_transport_lines_are_ignored(self):
        result=self.check(Runner(ids='--help\n../../etc/passwd\n'+DEVICE))
        self.assertEqual(len(result['devices']),1)

    def test_transport_is_capped(self):
        runner=Runner(ids='\n'.join(f'{i:040x}' for i in range(20)))
        self.assertEqual(self.check(runner)['status'],'manual_intervention_required')
        self.assertEqual(len(runner.calls),1)

    def test_sysfs_filters_keyboard(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name,product,pid in [('1','iPhone','12a8'),('2','Apple Keyboard','0250')]:
                d=root/name
                d.mkdir()
                (d/'idVendor').write_text('05ac')
                (d/'product').write_text(product)
                (d/'idProduct').write_text(pid)
            self.assertEqual([d['ios_candidate'] for d in enumerate_usb(root)],[True,False])

    def test_missing_executable(self):
        self.assertEqual(run_command(['/nonexistent/ios-test']).code,127)

    def test_schema_required_keys(self):
        schema=json.loads((Path(__file__).parents[2]/'schemas/diagnostic-v1.schema.json').read_text())
        self.assertTrue(set(schema['required']).issubset(self.check()))
        self.assertIn(self.check()['status'],schema['properties']['status']['enum'])

    def test_cli_json_pending_success(self):
        stream=io.StringIO()
        with patch('ios_usbmuxd_compat.cli.diagnose',return_value=self.check(Runner(ids=''),connected=False)), redirect_stdout(stream):
            self.assertEqual(main(['check','--json']),0)
        self.assertEqual(json.loads(stream.getvalue())['status'],'pending_device')

    def test_pair_failure_propagates(self):
        result = pair_devices(runner=Runner(pair=CommandResult(1, stderr="User denied pairing")))
        self.assertEqual(result['status'], 'trust_rejected')

    def test_pair_attached_permission_failure(self):
        result = pair_devices(runner=Runner(listing=CommandResult(1,stderr="Permission denied")), host=host())
        self.assertEqual(result['status'], 'permission_denied')

    def test_pair_without_hardware(self):
        self.assertEqual(pair_devices(runner=Runner(ids=''),host=host(connected=False))['status'],'pending_device')

    def test_jsonschema_validation(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest('Optional jsonschema package is unavailable')
        schema = json.loads((Path(__file__).parents[2] / 'schemas/diagnostic-v1.schema.json').read_text())
        for report in (self.check(), self.check(Runner(ids=''), connected=False),
                       self.check(Runner(pair=CommandResult(1,stderr='Pairing dialog response pending')))):
            jsonschema.validate(report, schema)

    def test_pair_over_limit_does_not_silently_pair_subset(self):
        runner = Runner(ids='\n'.join(f'{i:040x}' for i in range(17)))
        self.assertEqual(pair_devices(runner=runner)['status'],'manual_intervention_required')
        self.assertEqual(len(runner.calls),1)

    def test_cli_stock_status_success(self):
        with patch('ios_usbmuxd_compat.remediation.status', return_value={'phase':'stock','status':'stock'}), redirect_stdout(io.StringIO()):
            self.assertEqual(main(['status']),0)

    def test_launch_without_arguments_checks_connectivity(self):
        report = self.check(Runner(ids=''), connected=False)
        with patch('ios_usbmuxd_compat.cli.diagnose', return_value=report) as check, redirect_stdout(io.StringIO()):
            self.assertEqual(main([]), 0)
        check.assert_called_once_with()
