import unittest
from unittest.mock import patch
from ios_usbmuxd_compat.remediation import pair_selected


class SelectedPairingTests(unittest.TestCase):
    def test_selected_clients_are_revalidated_before_pairing(self):
        report = {'status': 'client_library_incompatible'}
        with patch('ios_usbmuxd_compat.remediation.engine.status', return_value={'phase':'private_client'}), \
             patch('ios_usbmuxd_compat.diagnose', return_value=report), \
             patch('ios_usbmuxd_compat.remediation.engine.Engine.manifest') as validate, \
             patch('ios_usbmuxd_compat.pair_devices', return_value={'status':'pairing_requested'}) as pair:
            self.assertEqual(pair_selected()['status'], 'pairing_requested')
            validate.assert_called_once_with('client', report)
            pair.assert_called_once_with(client_mode='private')

    def test_stock_pairing_does_not_load_a_bundle(self):
        with patch('ios_usbmuxd_compat.remediation.engine.status', return_value={'phase':'stock'}), \
             patch('ios_usbmuxd_compat.remediation.engine.Engine.manifest') as validate, \
             patch('ios_usbmuxd_compat.pair_devices', return_value={'status':'pending_device'}) as pair:
            self.assertEqual(pair_selected()['status'], 'pending_device')
            validate.assert_not_called()
            pair.assert_called_once_with()
