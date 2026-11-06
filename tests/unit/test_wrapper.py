import unittest
from unittest.mock import patch
from ios_usbmuxd_compat import wrapper


class WrapperTests(unittest.TestCase):
    def test_ready_does_not_repair(self):
        with patch.object(wrapper, 'diagnose_selected', return_value={'status': 'ready'}), patch.object(wrapper, 'repair') as fix:
            self.assertEqual(wrapper.prepare(allow_repair=True)['status'], 'ready')
            fix.assert_not_called()

    def test_repair_rechecks_with_application_probe(self):
        probe = object()
        with patch.object(wrapper, 'diagnose_selected', side_effect=[{'status': 'daemon_failure'}, {'status': 'ready'}]) as check, patch.object(wrapper, 'repair', return_value={'status': 'ready'}) as fix:
            self.assertEqual(wrapper.prepare(probes=[probe], allow_repair=True)['status'], 'ready')
            fix.assert_called_once_with()
            self.assertEqual(check.call_count, 2)
            check.assert_called_with(probes=[probe])

    def test_user_states_never_repair(self):
        for state in ('pending_device', 'awaiting_trust', 'device_locked', 'permission_denied', 'application_protocol_failure'):
            with self.subTest(state=state), patch.object(wrapper, 'diagnose_selected', return_value={'status': state}), patch.object(wrapper, 'repair') as fix:
                wrapper.prepare(allow_repair=True)
                fix.assert_not_called()

    def test_repair_is_opt_in(self):
        with patch.object(wrapper, 'diagnose_selected', return_value={'status': 'daemon_failure'}), patch.object(wrapper, 'repair') as fix:
            wrapper.prepare()
            fix.assert_not_called()

    @patch.object(wrapper.os, 'geteuid', return_value=1000)
    def test_blocked_states_never_launch(self, uid):
        for state in ('pending_device', 'awaiting_trust', 'repair_failed', 'daemon_failure'):
            with patch.object(wrapper, 'prepare', return_value={'status': state}), patch.object(wrapper.os, 'execvpe') as launch:
                self.assertEqual(wrapper.main(['--', '/app']), 75)
                launch.assert_not_called()

    @patch.object(wrapper.os, 'geteuid', return_value=1000)
    def test_launch_preserves_argv_without_shell(self, uid):
        with patch.object(wrapper, 'prepare', return_value={'status': 'ready'}), patch.object(wrapper.os, 'execvpe') as launch:
            wrapper.main(['--', '/app', '$(touch /tmp/unsafe)', '--flag'])
            executable, argv, env = launch.call_args.args
            self.assertEqual(executable, '/app')
            self.assertEqual(argv, ['/app', '$(touch /tmp/unsafe)', '--flag'])
            self.assertEqual(env['IOS_USBMUXD_COMPAT_STATUS'], 'ready')

    @patch.object(wrapper.os, 'geteuid', return_value=1000)
    def test_explicit_no_device_launch(self, uid):
        with patch.object(wrapper, 'prepare', return_value={'status': 'pending_device'}), patch.object(wrapper.os, 'execvpe') as launch:
            wrapper.main(['--allow-pending-device', '--', '/app'])
            self.assertEqual(launch.call_args.args[2]['IOS_USBMUXD_COMPAT_STATUS'], 'pending_device')

    @patch.object(wrapper.os, 'geteuid', return_value=0)
    def test_root_wrapper_refused(self, uid):
        with patch.object(wrapper, 'prepare') as check:
            self.assertEqual(wrapper.main(['--', '/app']), 77)
            check.assert_not_called()
