#!/usr/bin/env python3
"""Assemble a local installer using supplied, unchanged native Debian packages."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def field(path, name):
    return subprocess.check_output(['dpkg-deb', '-f', str(path), name], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vysor', required=True, type=Path)
    parser.add_argument('--framework', required=True, type=Path)
    parser.add_argument('--daemon', type=Path, help='Optional native daemon component; activation still requires validation')
    parser.add_argument('--daemon-source', type=Path, help='Required corresponding source archive when including a daemon')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.daemon and (not args.daemon_source or not args.daemon_source.is_file()):
        parser.error('--daemon requires --daemon-source for corresponding source distribution')
    if args.daemon_source and not args.daemon:
        parser.error('--daemon-source requires --daemon')
    inputs = [(args.vysor.resolve(), 'vysor', 'vysor.deb'),
              (args.framework.resolve(), 'ios-usbmuxd-compat', 'framework.deb')]
    if args.daemon:
        inputs.append((args.daemon.resolve(), 'ios-usbmuxd-compat-daemon', 'daemon.deb'))
    for path, package, _ in inputs:
        if field(path, 'Package') != package:
            parser.error(f'Expected package {package}')
    arch = field(args.vysor, 'Architecture')
    if arch not in ('amd64', 'arm64'):
        parser.error('Only native amd64/arm64 Vysor packages are supported')
    version = field(args.vysor, 'Version')
    if any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.+:~-' for c in version):
        parser.error('Invalid package version')
    for path, _, _ in inputs:
        if field(path, 'Architecture') not in (arch, 'all'):
            parser.error('Package architectures do not match')
    output = args.output.resolve()
    if output.exists():
        parser.error('Output directory already exists; choose a new versioned directory')
    source = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        framework = root / 'framework'
        subprocess.run(['dpkg-deb', '-x', str(args.framework.resolve()), str(framework)], check=True)
        if not (framework / 'usr/bin/ios-usbmuxd-wrap').is_file():
            parser.error('Framework package lacks the app wrapper; rebuild the current source')
        vendor = root / 'vendor'
        subprocess.run(['dpkg-deb', '-x', str(args.vysor.resolve()), str(vendor)], check=True)
        if not (vendor / 'opt/Vysor/vysorapp').is_file() or not (vendor / 'usr/share/applications/vysorapp.desktop').is_file():
            parser.error('Unsupported Vysor package layout')
        pkg = root / 'companion'
        (pkg / 'DEBIAN').mkdir(parents=True)
        depends = (f'vysor (= {version}), ios-usbmuxd-compat (>= 0.1.0), '
                   'libgbm1, libasound2t64 | libasound2, libcups2t64 | libcups2')
        if args.daemon:
            depends += ', ios-usbmuxd-compat-daemon'
        (pkg / 'DEBIAN/control').write_text(f'''Package: vysor-usb-compat
Version: 0.1.0
Architecture: all
Maintainer: ios-usbmuxd-compat contributors <maintainers@example.invalid>
Depends: {depends}
Section: utils
Priority: optional
Description: Vysor launcher with managed iPhone USB diagnostics
 Uses the ios-usbmuxd-compat framework without modifying the Vysor executable.
''')
        for script in ('preinst', 'postrm'):
            shutil.copy2(source / script, pkg / 'DEBIAN' / script)
        for local, target in [('vysor-usb', 'usr/bin/vysor-usb'),
                              ('vysorapp.desktop', 'usr/share/applications/vysorapp.desktop'),
                              ('README.md', 'usr/share/doc/vysor-usb-compat/README.md'),
                              ('copyright', 'usr/share/doc/vysor-usb-compat/copyright')]:
            dest = pkg / target
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / local, dest)
        bundle = root / 'bundle'
        bundle.mkdir()
        subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(pkg), str(bundle / 'integration.deb')], check=True)
        provenance = []
        for path, package, name in inputs:
            shutil.copyfile(path, bundle / name)
            provenance.append({'package': package, 'version': field(path, 'Version'), 'architecture': field(path, 'Architecture'), 'file': name})
        (bundle / 'packages.json').write_text(json.dumps(provenance, indent=2) + '\n')
        for name in ('install.sh', 'README.md'):
            shutil.copy2(source / name, bundle / name)
        if args.daemon_source:
            shutil.copyfile(args.daemon_source, bundle / 'daemon-corresponding-source.tar.gz')
        (bundle / 'ARCHITECTURE').write_text(arch + '\n')
        (bundle / 'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n' for p in sorted(bundle.iterdir()) if p.is_file()))
        shutil.copytree(bundle, output)
    print(f'Installer: {output}/install.sh')


if __name__ == '__main__':
    main()
