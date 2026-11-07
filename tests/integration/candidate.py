"""Isolated container smoke test. Never run on a user's live usbmuxd host."""
import hashlib
import json
from pathlib import Path
import plistlib
import socket
import struct
import subprocess
import time
from ios_usbmuxd_compat.remediation.engine import Engine, RepairError

base = Path('/usr/lib/ios-usbmuxd-compat/daemon')
manifest = json.loads((base / 'manifest.json').read_text())
assert manifest['validated'] is False
for name, digest in manifest['sha256'].items():
    assert hashlib.sha256((base / name).read_bytes()).hexdigest() == digest
try:
    Engine().manifest('daemon', {})
except RepairError as exc:
    assert 'No independently validated' in str(exc), str(exc)
else:
    raise AssertionError('Unvalidated candidate accepted')
assert not Path('/run/usbmuxd').exists(), 'Refuse to disturb an existing socket'
with open('/tmp/candidate.log', 'w') as log:
    proc = subprocess.Popen([str(base / 'usbmuxd'), '--foreground', '--user', 'usbmux'], stdout=log, stderr=log)
    try:
        for _ in range(50):
            if Path('/run/usbmuxd').exists():
                break
            assert proc.poll() is None, Path('/tmp/candidate.log').read_text()
            time.sleep(0.1)
        with socket.socket(socket.AF_UNIX) as conn:
            conn.settimeout(5)
            conn.connect('/run/usbmuxd')
            body = plistlib.dumps({'MessageType': 'ListDevices', 'ClientVersionString': 'compat-candidate-test', 'ProgName': 'candidate-test', 'kLibUSBMuxVersion': 3})
            conn.sendall(struct.pack('<IIII', len(body) + 16, 1, 8, 1) + body)
            def read(n):
                data = b''
                while len(data) < n:
                    chunk = conn.recv(n - len(data))
                    assert chunk, 'Unexpected EOF'
                    data += chunk
                return data
            length, version, message, tag = struct.unpack('<IIII', read(16))
            assert 16 <= length <= 1024 * 1024
            assert version == 1 and message == 8 and tag == 1
            assert plistlib.loads(read(length - 16))['DeviceList'] == []
        result = subprocess.run([str(base / 'bin/idevice_id'), '-l'], capture_output=True, text=True, timeout=10, check=True)
        assert not result.stdout.strip()
    finally:
        proc.terminate()
        proc.wait(timeout=10)
print('PASS: native daemon startup, standard socket protocol, private client enumeration, manifest integrity and unvalidated activation rejection. No hardware validation.')
