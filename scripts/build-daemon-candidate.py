#!/usr/bin/env python3
"""Build an unvalidated upstream stack in a native Debian build environment."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'packaging/daemon/candidate-sources.json'
PREFIX = '/usr/lib/ios-usbmuxd-compat/daemon'


def run(args, **kw):
    return subprocess.run(args, check=True, **kw)


def build():
    lock = json.loads(LOCK.read_text())
    assert lock['validated'] is False
    output = ROOT / 'dist/candidate'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        sdk = work / 'sdk'
        sdk.mkdir()
        env = dict(os.environ, SOURCE_DATE_EPOCH=str(lock['source_date_epoch']),
                   LC_ALL='C.UTF-8', TZ='UTC',
                   PKG_CONFIG_PATH=str(sdk / 'lib/pkgconfig'),
                   LD_LIBRARY_PATH=str(sdk / 'lib'),
                   CFLAGS='-O2 -ffile-prefix-map=' + str(work) + '=/usr/src/ios-usbmuxd-compat')
        sources = work / 'sources'
        sources.mkdir()
        for item in lock['sources']:
            archive = sources / (item['name'] + '.tar.gz')
            data = urllib.request.urlopen(item['url'], timeout=120).read()
            assert hashlib.sha256(data).hexdigest() == item['sha256'], item['name']
            archive.write_bytes(data)
            source = work / item['name']
            source.mkdir()
            with tarfile.open(archive) as tar:
                # All members must stay under a single upstream top-level directory.
                for member in tar.getmembers():
                    p = Path(member.name)
                    assert not p.is_absolute() and '..' not in p.parts
                    assert not member.issym() and not member.islnk()
            run(['tar', '-xf', str(archive), '--strip-components=1', '-C', str(source)])
            (source / '.tarball-version').write_text(item['version'] + '\n')
            flags = ['--disable-static']
            if item['name'] in ('libplist', 'libimobiledevice'):
                flags += ['--without-cython']
            if item['name'] == 'libimobiledevice':
                flags += ['--without-openssl', '--with-gnutls']
            run(['./autogen.sh', '--prefix=' + str(sdk), '--sysconfdir=/etc', '--localstatedir=/var', *flags], cwd=source, env=env)
            run(['make', '-j2'], cwd=source, env=env)
            run(['make', 'install'], cwd=source, env=env)
        stage = work / 'package'
        base = stage / PREFIX.lstrip('/')
        (base / 'lib').mkdir(parents=True)
        (base / 'bin').mkdir()
        shutil.copy2(sdk / 'sbin/usbmuxd', base / 'usbmuxd')
        for name in ('idevice_id', 'idevicepair', 'ideviceinfo'):
            shutil.copy2(sdk / 'bin' / name, base / 'bin' / name)
        # Store real SONAME files, never symlinks. Each ELF gets its own private RUNPATH.
        for path in (sdk / 'lib').glob('*.so.*'):
            soname = subprocess.check_output(['patchelf', '--print-soname', str(path)], text=True).strip()
            shutil.copy2(path.resolve(), base / 'lib' / soname)
        for path in base.rglob('*'):
            if path.is_file():
                rpath = '$ORIGIN' if path.parent.name == 'lib' else ('$ORIGIN/../lib' if path.parent.name == 'bin' else '$ORIGIN/lib')
                run(['patchelf', '--set-rpath', rpath, str(path)])
        # Fail if the closure refers to the build tree, Nix, or unresolved libraries.
        for path in base.rglob('*'):
            if path.is_file():
                resolved = subprocess.check_output(['ldd', str(path)], text=True)
                assert 'not found' not in resolved and '/nix/store/' not in resolved and str(sdk) not in resolved, resolved
        manifest = dict(schema_version=1, validated=False, architecture=platform.machine(),
                        provenance='Pinned upstream candidate; see candidate-sources.json. Hardware validation pending.',
                        sha256={str(p.relative_to(base)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in base.rglob('*') if p.is_file()})
        (base / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        docs = stage / 'usr/share/doc/ios-usbmuxd-compat-daemon'
        docs.mkdir(parents=True)
        shutil.copy2(LOCK, docs / LOCK.name)
        for item in lock['sources']:
            dest = docs / item['name']
            dest.mkdir()
            for pattern in ('COPYING*', 'AUTHORS*', 'LICENSE*'):
                for p in (work / item['name']).glob(pattern):
                    if p.is_file():
                        shutil.copy2(p, dest / p.name)
        (docs / 'copyright').write_text('See each component directory for upstream license and author notices.\nCorresponding source archives accompany this package. Framework MIT does not relicense these components.\n')
        (work / 'debian').mkdir()
        shutil.copy2(ROOT / 'packaging/debian/control', work / 'debian/control')
        (stage / 'DEBIAN').mkdir()
        # Private libraries are shipped in this package and need no external package mapping.
        args = ['dpkg-shlibdeps', '-O', '--ignore-missing-info', '-l' + str(base / 'lib')]
        args += ['-e' + str(p) for p in base.rglob('*') if p.is_file() and p.name != 'manifest.json']
        deps = subprocess.check_output(args, cwd=work, text=True).strip().removeprefix('shlibs:Depends=')
        control = stage / 'DEBIAN'
        control.mkdir(exist_ok=True)
        arch = subprocess.check_output(['dpkg', '--print-architecture'], text=True).strip()
        version = lock['sources'][-1]['version'] + '-1'
        (control / 'control').write_text(f'Package: ios-usbmuxd-compat-daemon\nVersion: {version}\nArchitecture: {arch}\nMaintainer: ios-usbmuxd-compat contributors <maintainers@example.invalid>\nDepends: ios-usbmuxd-compat, {deps}\nSection: utils\nPriority: optional\nDescription: isolated upstream usbmuxd candidate awaiting hardware validation\n Contains a private native library stack. Never activates automatically without\n a separately reviewed hardware validation manifest.\n')
        (control / 'prerm').write_text('#!/bin/sh\nset -e\ncase "$1" in remove|deconfigure|upgrade) /usr/lib/ios-usbmuxd-compat/helper rollback;; esac\n')
        (control / 'prerm').chmod(0o755)
        run(['dpkg-deb', '--root-owner-group', '--build', str(stage), str(output / f'ios-usbmuxd-compat-daemon_{version}_{arch}.deb')], env=env)
        for rel in ('packaging/daemon/candidate-sources.json', 'packaging/debian/control',
                    'scripts/build-daemon-candidate.py', 'scripts/build-candidate-container.sh'):
            dest = sources / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dest)
        (output / 'BUILD_PACKAGES').write_text(subprocess.check_output(['dpkg-query', '-W'], text=True))
        run(['tar', '--sort=name', '--mtime=@' + str(lock['source_date_epoch']), '--owner=0', '--group=0', '--numeric-owner', '-czf', str(output / 'candidate-corresponding-source.tar.gz'), '-C', str(sources), '.'])
        (output / 'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n' for p in sorted(output.iterdir()) if p.name != 'SHA256SUMS' and p.is_file()))


if __name__ == '__main__':
    build()
