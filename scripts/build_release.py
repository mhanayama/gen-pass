#!/usr/bin/env python3
"""Build and smoke-test a Python-free release for the current OS/CPU."""
import argparse
import hashlib
import platform
from pathlib import Path
import re
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import tempfile
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def target():
    system = {'Darwin': 'macos', 'Linux': 'linux', 'Windows': 'windows'}.get(platform.system())
    machine = platform.machine().lower()
    arch = {'arm64': 'arm64', 'aarch64': 'arm64', 'amd64': 'x86_64', 'x86_64': 'x86_64'}.get(machine)
    if system is None or arch is None or (system == 'windows' and arch != 'x86_64'):
        raise SystemExit(f'Unsupported build platform: {platform.system()} / {machine}')
    return f'{system}-{arch}'


def verify_command(command):
    """Run outside the repository, using both bundled dictionaries, without copying."""
    with tempfile.TemporaryDirectory(prefix='gen-pass-smoke-') as directory:
        for args in (['--help'], ['--no-clipboard'], ['--hr', '--no-clipboard'],
                     ['-n', '32', '--ed', '--eu', '--no-clipboard']):
            result = subprocess.run([str(command), *args], cwd=directory, text=True,
                                    capture_output=True, timeout=60)
            if result.returncode:
                raise RuntimeError(f'{command.name} failed ({result.returncode}): {result.stderr}')
            if result.stderr:
                raise RuntimeError(result.stderr)
            if args == ['--help']:
                assert '--no-clipboard' in result.stdout
                continue
            header, password = result.stdout.splitlines()
            assert header.startswith(f'Generated {len(password)} character password.')
            assert re.fullmatch('[A-Za-z0-9_-]+', password)
            if '--hr' in args:
                assert re.fullmatch(r'[a-z]{3,5}-[a-z]{3,5}-[a-z]{3,5}-[0-9]{4}', password)
            if '-n' in args:
                assert len(password) <= 32 and '-' not in password and '_' not in password
    print('PASS standalone executable outside repository (clipboard disabled)')


def package_release(binary, output, platform_target):
    """Package executable and redistribution notices; create a SHA-256 sidecar."""
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='gen-pass-package-') as directory:
        bundle = Path(directory) / 'gen-pass'
        bundle.mkdir()
        shutil.copy2(binary, bundle / binary.name)
        for name in ('README.md', 'LICENSE', 'THIRD_PARTY_LICENSES.md'):
            shutil.copy2(ROOT / name, bundle / name)
        shutil.copytree(ROOT / 'licenses', bundle / 'licenses')
        # The executable also redistributes CPython, including its library notices.
        candidates = (Path(sysconfig.get_path('stdlib')) / 'LICENSE.txt',
                      Path(sys.base_prefix) / 'LICENSE.txt')
        python_license = next((path for path in candidates if path.is_file()), None)
        if python_license is None:
            raise RuntimeError('Cannot find the bundled Python runtime LICENSE.txt')
        shutil.copy2(python_license, bundle / 'licenses' / 'Python-LICENSE.txt')
        if platform_target.startswith('windows-'):
            archive = output / f'gen-pass-{platform_target}.zip'
            with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as handle:
                for path in sorted(bundle.rglob('*')):
                    if path.is_file():
                        handle.write(path, path.relative_to(bundle.parent))
        else:
            archive = output / f'gen-pass-{platform_target}.tar.gz'
            with tarfile.open(archive, 'w:gz') as handle:
                handle.add(bundle, arcname='gen-pass')
    with archive.open('rb') as handle:
        digest = hashlib.file_digest(handle, 'sha256').hexdigest()
    archive.with_name(archive.name + '.sha256').write_text(f'{digest}  {archive.name}\n', encoding='ascii')
    print(f'Created {archive}')
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', help='Require a tag matching the package version, e.g. v0.1.0')
    args = parser.parse_args()
    version = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']['version']
    if args.tag and args.tag != f'v{version}':
        parser.error(f'Tag must be v{version}, got {args.tag}')
    platform_target = target()
    workspace = ROOT / '.build' / 'standalone' / platform_target
    workspace.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile',
        '--name', 'gen-pass', '--distpath', str(workspace / 'dist'),
        '--workpath', str(workspace / 'work'), '--specpath', str(workspace),
        '--collect-data', 'gen_pass', '--noupx', str(ROOT / 'gen-pass.py'),
    ], cwd=ROOT, check=True)
    binary = workspace / 'dist' / ('gen-pass.exe' if sys.platform == 'win32' else 'gen-pass')
    verify_command(binary)
    package_release(binary, ROOT / 'dist' / 'release', platform_target)


if __name__ == '__main__':
    main()
