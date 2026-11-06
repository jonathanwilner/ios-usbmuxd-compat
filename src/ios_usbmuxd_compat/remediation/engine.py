"""Conservative repair transactions. No replacement is shipped or trusted by default."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import stat
import subprocess
import tempfile

BASE = Path('/usr/lib/ios-usbmuxd-compat')
STATE = Path('/var/lib/ios-usbmuxd-compat')
DROPIN = Path('/etc/systemd/system/usbmuxd.service.d/50-ios-usbmuxd-compat.conf')
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C', 'LC_ALL': 'C', 'HOME': '/root'}


class RepairError(RuntimeError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def run(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=20, env=ENV, cwd='/', check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RepairError('Required host operation failed or timed out') from exc
    if result.returncode:
        raise RepairError('Host operation failed: ' + args[0])
    if len(result.stdout) > 262144:
        raise RepairError('Host operation returned excessive output')
    return result.stdout


def trusted(path):
    """Require root ownership and no writable/symlink ancestor, including the leaf."""
    for part in [path, *path.parents]:
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise RepairError('Unsafe ownership or permissions on installed repair resource')
    if not path.is_file():
        raise RepairError('Repair resource is not a regular file')


def atomic(path, value, mode=0o644):
    data = value.encode() if isinstance(value, str) else (json.dumps(value, sort_keys=True) + '\n').encode()
    fd, temporary = tempfile.mkstemp(prefix='.compat-', dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Engine:
    """Dependency injection is for library tests, never accepted by the helper."""
    def __init__(self, state=STATE, dropin=DROPIN, base=BASE, runner=run, diagnose=None, check_owner=True):
        self.state, self.dropin, self.base = Path(state), Path(dropin), Path(base)
        self.run, self.check_owner = runner, check_owner
        if diagnose is None:
            from ios_usbmuxd_compat import diagnose
        self.diagnose = diagnose

    def read(self):
        path = self.state / 'state.json'
        if not path.exists():
            return {'phase': 'stock', 'schema_version': 1}
        if self.check_owner:
            trusted(path)
        try:
            value = json.loads(path.read_text())
            if not isinstance(value, dict) or value.get('schema_version') != 1:
                raise ValueError()
            return value
        except (ValueError, OSError) as exc:
            raise RepairError('Repair journal is invalid; administrator review required') from exc

    @contextmanager
    def lock(self):
        if self.check_owner and os.geteuid() != 0:
            raise RepairError('Administrator authorization required')
        self.state.mkdir(mode=0o755, parents=True, exist_ok=True)
        if self.check_owner:
            # Validate directory without relaxing the regular-file check in trusted().
            for parent in [self.state, *self.state.parents]:
                info = parent.lstat()
                if stat.S_ISLNK(info.st_mode) or info.st_uid or info.st_mode & 0o022:
                    raise RepairError('Unsafe repair state directory')
        descriptor = os.open(self.state / 'lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RepairError('Another repair is running') from exc
            yield
        finally:
            os.close(descriptor)

    def save(self, value):
        value['schema_version'] = 1
        atomic(self.state / 'state.json', value, mode=0o600)
        # Publish only the fixed selection state, never captured unit contents.
        atomic(self.state / 'public.json', {'schema_version': 1, 'phase': value['phase']})

    def public_status(self):
        path = self.state / 'public.json'
        if not path.exists():
            return {'schema_version': 1, 'phase': 'stock', 'status': 'stock'}
        if self.check_owner:
            trusted(path)
        try:
            data = json.loads(path.read_text())
            phases = ('stock', 'private_client', 'prepared', 'activating', 'active', 'rolled_back')
            if not isinstance(data, dict) or data.get('schema_version') != 1 or data.get('phase') not in phases:
                raise ValueError('Invalid public state')
            return {'schema_version': 1, 'phase': data['phase'], 'status': data['phase']}
        except (OSError, ValueError) as exc:
            raise RepairError('Public repair state invalid; administrator review required') from exc

    def unit(self):
        effective = self.run(['/usr/bin/systemctl', 'cat', 'usbmuxd.service'])
        properties = self.run(['/usr/bin/systemctl', 'show', 'usbmuxd.service', '--property=FragmentPath,DropInPaths,User,Group,Type,MainPID,ActiveState'])
        values = dict(line.split('=', 1) for line in properties.splitlines() if '=' in line)
        if values.get('DropInPaths', '').strip():
            raise RepairError('Existing systemd overrides require administrator review')
        if not values.get('FragmentPath', '').startswith(('/lib/systemd/system/', '/usr/lib/systemd/system/')):
            raise RepairError('Service is not a distribution unit')
        starts = re.findall(r'^ExecStart=(.+)$', effective, flags=re.M)
        if len(starts) != 1 or any(c in starts[0] for c in '\\%$\n\r;'):
            raise RepairError('Unsupported service command syntax')
        args = shlex.split(starts[0])
        if not args or args[0] not in ('/usr/sbin/usbmuxd', '/usr/bin/usbmuxd'):
            raise RepairError('Unexpected stock daemon executable')
        if any(not re.fullmatch(r'[A-Za-z0-9_./:=+-]+', arg) for arg in args):
            raise RepairError('Unsupported service arguments')
        return effective, values, args

    def manifest(self, kind, report):
        folder = self.base / kind
        path = folder / 'manifest.json'
        if self.check_owner:
            trusted(path)
        manifest = json.loads(path.read_text())
        if not isinstance(manifest, dict):
            raise RepairError('Invalid component manifest')
        if manifest.get('schema_version') != 1 or manifest.get('validated') is not True:
            raise RepairError('No independently validated repair component installed')
        if manifest.get('architecture') != platform.machine():
            raise RepairError('Repair component architecture mismatch')
        host = report.get('host', {})
        distro = host.get('distribution', host.get('distro', ''))
        release = host.get('release', host.get('version_id', ''))
        if isinstance(distro, dict):
            release = distro.get('version_id', release)
            distro = distro.get('id', '')
        if manifest.get('distribution') != distro or manifest.get('release') != release or not distro or not release:
            raise RepairError('Repair component distribution mismatch')
        if not isinstance(manifest.get('repair_statuses'), list) or report.get('status') not in manifest['repair_statuses']:
            raise RepairError('Component has no validation evidence for this failure')
        if kind == 'client' and (not host.get('packages') or manifest.get('package_versions') != host['packages']):
            raise RepairError('Private client package environment changed; revalidation required')
        if not manifest.get('provenance') or not manifest.get('hardware_validation'):
            raise RepairError('Component lacks provenance or hardware validation')
        files = manifest.get('sha256', {})
        required = {'usbmuxd'} if kind == 'daemon' else {'bin/idevice_id', 'bin/idevicepair', 'bin/ideviceinfo'}
        if not isinstance(files, dict) or not required.issubset(files) or len(files) > 100:
            raise RepairError('Incomplete component manifest')
        inventory = {str(item.relative_to(folder)) for item in folder.rglob('*') if item.is_file() and item != path}
        if inventory != set(files):
            raise RepairError('Manifest must cover every bundled file')
        for relative, expected in files.items():
            if not isinstance(relative, str) or not isinstance(expected, str) or not re.fullmatch(r'[a-f0-9]{64}', expected):
                raise RepairError('Invalid component checksum')
            if not re.fullmatch(r'[A-Za-z0-9_./+-]+', relative) or '..' in relative.split('/') or relative.startswith('/'):
                raise RepairError('Invalid component path')
            file = folder / relative
            if self.check_owner:
                trusted(file)
            if digest(file.read_bytes()) != expected:
                raise RepairError('Repair component hash mismatch')
        # No shell wrappers: private tools must be ELF with application-relative RUNPATH.
        for relative in required:
            binary = (folder / relative).read_bytes()
            machines = {'x86_64': 62, 'aarch64': 183}
            if len(binary) < 20 or binary[:6] != b'\x7fELF\x02\x01' or int.from_bytes(binary[18:20], 'little') != machines.get(platform.machine()):
                raise RepairError('Repair component must contain matching 64-bit ELF executables')
            if b'/nix/store/' in binary:
                raise RepairError('Debian repair component contains Nix store references')
        return manifest

    def restore(self, state):
        if self.dropin.exists() or self.dropin.is_symlink():
            if self.dropin.is_symlink() or digest(self.dropin.read_bytes()) != state.get('override_sha256'):
                raise RepairError('Package override changed externally; refusing to remove it')
            self.dropin.unlink()
        if state.get('override_sha256') and (not self.check_owner or Path('/run/systemd/system').exists()):
            self.run(['/usr/bin/systemctl', 'daemon-reload'])
            self.run(['/usr/bin/systemctl', 'restart', 'usbmuxd.service'])
        self.save({'phase': 'rolled_back', 'previous_phase': state.get('phase')})
        return {'status': 'rolled_back'}

    def rollback(self):
        with self.lock():
            return self.restore(self.read())

    def repair(self):
        with self.lock():
            previous = self.read()
            if previous.get('phase') in ('prepared', 'activating'):
                self.restore(previous)
                return {'status': 'rolled_back', 'message': 'Recovered interrupted repair; run check again'}
            report = self.diagnose()
            if report['status'] == 'ready':
                self.save({**previous, 'last_result': 'ready'})
                return {'status': 'ready', 'changed': False}
            if report['status'] == 'client_library_incompatible':
                if previous.get('phase') == 'active':
                    raise RepairError('Active daemon repair requires rollback or administrator review before client repair')
                self.manifest('client', report)
                tested = self.diagnose(client_dir=str(self.base / 'client' / 'bin'))
                if tested['status'] == 'ready':
                    self.save({'phase': 'private_client', 'last_result': 'ready'})
                    return {'status': 'ready', 'changed': True, 'strategy': 'private_client'}
                return {'status': 'repair_failed', 'changed': False, 'diagnostics': tested}
            if report['status'] != 'daemon_failure':
                return select(report)
            if previous.get('phase') == 'active':
                return {'status': 'manual_intervention_required', 'message': 'Replacement already active; inspect diagnostics or rollback'}
            manifest = self.manifest('daemon', report)
            effective, properties, args = self.unit()
            if manifest.get('stock_unit_sha256') != digest(effective.encode()):
                raise RepairError('Distribution unit changed; replacement requires revalidation')
            observed = report.get('host', {})
            if manifest.get('failure_match') != {'socket': observed.get('socket'), 'packages': observed.get('packages')} or observed.get('socket') not in ('missing', 'unreachable', 'invalid') or not observed.get('packages'):
                raise RepairError('Replacement lacks evidence for this exact daemon failure and package set')
            if report.get('host', {}).get('conflicting_daemons'):
                raise RepairError('Conflicting daemon instances require administrator review')
            pids = {str(proc.get('pid')) for proc in observed.get('processes', [])}
            if self.check_owner:
                # Refresh immediately before activation, after the slower manifest checks.
                pids = set()
                for proc in Path('/proc').glob('[0-9]*'):
                    try:
                        if (proc / 'comm').read_text().strip() == 'usbmuxd':
                            pids.add(proc.name)
                    except (OSError, UnicodeError):
                        continue
            if pids - {properties.get('MainPID', '0')}:
                raise RepairError('An unmanaged daemon may own the socket; administrator review required')
            if self.dropin.exists() or self.dropin.is_symlink():
                raise RepairError('Override path already exists')
            self.dropin.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            if self.check_owner:
                for parent in [self.dropin.parent, *self.dropin.parent.parents]:
                    info = parent.lstat()
                    if stat.S_ISLNK(info.st_mode) or info.st_uid or info.st_mode & 0o022:
                        raise RepairError('Unsafe service override directory')
            args[0] = str(self.base / 'daemon' / 'usbmuxd')
            content = '# Owned by ios-usbmuxd-compat\n[Service]\nExecStart=\nExecStart=' + ' '.join(args) + '\n'
            state = {'phase': 'prepared', 'effective_unit': effective, 'properties': properties, 'override_sha256': digest(content.encode())}
            self.save(state)  # Durable undo information before mutation.
            try:
                atomic(self.dropin, content)
                self.save({**state, 'phase': 'activating'})
                self.run(['/usr/bin/systemctl', 'daemon-reload'])
                self.run(['/usr/bin/systemctl', 'restart', 'usbmuxd.service'])
                # Device disappearance may let the distribution service exit cleanly.
                tested = self.diagnose()
                runtime = self.run(['/usr/bin/systemctl', 'show', 'usbmuxd.service', '--property=ActiveState,Result,MainPID'])
                health = dict(line.split('=', 1) for line in runtime.splitlines() if '=' in line)
                if health.get('Result') != 'success' or health.get('ActiveState') == 'failed':
                    raise RepairError('Replacement service startup failed')
                pending = tested['status'] == 'pending_device'
                if not pending and (not tested.get('daemon_healthy') or tested['status'] in ('daemon_failure', 'client_library_incompatible', 'repair_failed', 'pairing_protocol_error', 'application_protocol_failure')):
                    raise RepairError('Replacement failed health verification')
                if health.get('ActiveState') == 'active':
                    pid = health.get('MainPID', '')
                    if not pid.isdigit() or pid == '0':
                        raise RepairError('Replacement process identity unavailable')
                    actual = os.readlink('/proc/' + pid + '/exe') if self.check_owner else str(self.base / 'daemon' / 'usbmuxd')
                    if actual != str(self.base / 'daemon' / 'usbmuxd'):
                        raise RepairError('Unexpected running daemon executable')
                elif not pending:
                    raise RepairError('Replacement is not running')
                self.save({**state, 'phase': 'active', 'last_result': tested['status']})
                return {'status': tested['status'], 'changed': True, 'hardware_validated': tested['status'] == 'ready'}
            except Exception as exc:
                self.restore(state)
                return {'status': 'repair_failed', 'rolled_back': True, 'message': str(exc)}


def select(report):
    state = report.get('status')
    actions = {'ready': 'none', 'pending_device': 'connect_device', 'awaiting_trust': 'unlock_and_trust', 'client_library_incompatible': 'private_client', 'daemon_failure': 'validated_daemon'}
    action = actions.get(state, 'manual_intervention')
    return {'status': state, 'strategy': action, 'requires_admin': action in ('private_client', 'validated_daemon'), 'changed': False,
            'message': 'Repair components must be installed and independently validated before activation' if action in ('private_client', 'validated_daemon') else 'Follow the diagnostic guidance'}


def status():
    return Engine().public_status()


def _authorized(action):
    try:
        result = subprocess.run(['/usr/bin/pkexec', '/usr/lib/ios-usbmuxd-compat/helper', action], capture_output=True, text=True, timeout=180, env=ENV, check=False)
        if not result.stdout or len(result.stdout) > 262144:
            raise RepairError('Administrator authorization unavailable or declined')
        parsed = json.loads(result.stdout)
        if not isinstance(parsed, dict) or not isinstance(parsed.get('status'), str):
            raise ValueError('Invalid helper result')
        return parsed
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        raise RepairError('Administrator authorization required; installed PolicyKit helper unavailable') from exc


def repair(dry_run=False):
    engine = Engine()
    if dry_run:
        return select(engine.diagnose())
    return engine.repair() if os.geteuid() == 0 else _authorized('repair')


def rollback():
    return Engine().rollback() if os.geteuid() == 0 else _authorized('rollback')


def diagnose_selected(*, probes=()):
    """Unprivileged application check honoring a previously verified private bundle.

    Stock ready takes precedence. Revalidate the fixed private inventory before
    reuse, including distribution/package compatibility represented by its manifest.
    """
    from ios_usbmuxd_compat import diagnose
    stock = diagnose(probes=probes)
    if stock['status'] != 'client_library_incompatible' or status().get('phase') != 'private_client':
        return stock
    Engine().manifest('client', stock)
    return diagnose(probes=probes, client_mode='private')


def pair_selected():
    """Pair explicitly using the approved client selection, preserving Trust."""
    from ios_usbmuxd_compat import diagnose, pair_devices
    if status().get('phase') == 'private_client':
        stock = diagnose()
        if stock['status'] == 'client_library_incompatible':
            Engine().manifest('client', stock)
            return pair_devices(client_mode='private')
    return pair_devices()
