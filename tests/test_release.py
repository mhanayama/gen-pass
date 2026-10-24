import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_release', ROOT / 'scripts' / 'build_release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def test_archive_contents_and_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for target, filename in (('linux-x86_64', 'gen-pass'), ('windows-x86_64', 'gen-pass.exe')):
                with self.subTest(target=target):
                    binary = root / filename
                    binary.write_bytes(b'fake executable')
                    binary.chmod(0o755)
                    archive = release.package_release(binary, root / 'output', target)
                    if archive.suffix == '.zip':
                        with zipfile.ZipFile(archive) as handle:
                            names = set(handle.namelist())
                    else:
                        with tarfile.open(archive) as handle:
                            names = set(handle.getnames())
                            # Windows does not represent POSIX executable permission bits.
                            if sys.platform != 'win32':
                                self.assertTrue(handle.getmember(f'gen-pass/{filename}').mode & 0o111)
                    for name in (filename, 'LICENSE', 'THIRD_PARTY_LICENSES.md', 'README.md',
                                 'licenses/SudachiDict-LEGAL.txt', 'licenses/Python-LICENSE.txt'):
                        self.assertIn(f'gen-pass/{name}', names)
                    checksum = archive.with_name(archive.name + '.sha256').read_text()
                    self.assertEqual(checksum, f'{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n')


@unittest.skipIf(sys.platform == 'win32', 'POSIX installer')
class ShellInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.fixture = self.root / 'assets'
        self.fixture.mkdir()
        self.fake_bin = self.root / 'tools'
        self.fake_bin.mkdir()
        self.binary = self.root / 'gen-pass'
        self.binary.write_text('#!/bin/sh\n[ "$1" = --help ]\n')
        self.binary.chmod(0o755)
        self.archive = release.package_release(self.binary, self.fixture, 'linux-x86_64')
        self.bin_dir = self.root / 'install with spaces' / 'bin'
        self.data_dir = self.root / 'install with spaces' / 'data'
        self.env = dict(os.environ, PATH=f'{self.fake_bin}{os.pathsep}{os.environ["PATH"]}',
                        GEN_PASS_INSTALL_DIR=str(self.bin_dir), GEN_PASS_DATA_DIR=str(self.data_dir),
                        GEN_PASS_VERSION='v0.1.0', FIXTURE=str(self.fixture))
        self.fake('uname', '#!/bin/sh\nif [ "$1" = -s ]; then echo Linux; else echo x86_64; fi\n')
        # Redirect only the expected HTTPS requests to local, offline release fixtures.
        self.fake('curl', f'''#!{sys.executable}
import os, pathlib, shutil, sys
args = sys.argv[1:]
url = next(x for x in args if x.startswith('https://'))
assert url.startswith('https://github.com/mhanayama/gen-pass/releases/download/v0.1.0/')
name = url.rsplit('/', 1)[-1]
shutil.copyfile(pathlib.Path(os.environ['FIXTURE']) / name, args[args.index('-o') + 1])
''')

    def fake(self, name, code):
        path = self.fake_bin / name
        path.write_text(code)
        path.chmod(0o755)

    def install(self):
        return subprocess.run(['sh', str(ROOT / 'install.sh')], env=self.env,
                              text=True, capture_output=True, timeout=30)

    def test_install_and_update_with_licenses(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        installed = self.bin_dir / 'gen-pass'
        old_bytes = installed.read_bytes()
        self.binary.write_text('#!/bin/sh\n# newer release\n[ "$1" = --help ]\n')
        release.package_release(self.binary, self.fixture, 'linux-x86_64')
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Updating existing installation', result.stdout)
        self.assertNotEqual(installed.read_bytes(), old_bytes)
        self.assertEqual(installed.read_bytes(), self.binary.read_bytes())
        self.assertTrue(os.access(installed, os.X_OK))
        self.assertTrue((self.data_dir / 'licenses' / 'Python-LICENSE.txt').is_file())
        self.assertFalse(list(self.bin_dir.glob('.gen-pass.*')))

    def test_update_finds_old_install_on_path(self):
        previous_bin = self.root / 'previous install' / 'bin'
        previous_bin.mkdir(parents=True)
        installed = previous_bin / 'gen-pass'
        installed.write_text('#!/bin/sh\nexit 99\n')
        installed.chmod(0o755)
        self.env.pop('GEN_PASS_INSTALL_DIR')
        self.env['PATH'] = f'{previous_bin}{os.pathsep}{self.env["PATH"]}'
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(installed.read_bytes(), self.binary.read_bytes())
        self.assertIn('Updating existing installation', result.stdout)
        self.assertFalse(self.bin_dir.exists())

    def test_update_replaces_pipx_style_symlink_without_changing_venv(self):
        previous = self.root / 'venv' / 'bin' / 'gen-pass'
        previous.parent.mkdir(parents=True)
        previous.write_text('#!/bin/sh\nexit 99\n')
        previous.chmod(0o755)
        self.bin_dir.mkdir(parents=True)
        installed = self.bin_dir / 'gen-pass'
        installed.symlink_to(previous)
        self.env.pop('GEN_PASS_INSTALL_DIR')
        self.env['PATH'] = f'{self.bin_dir}{os.pathsep}{self.env["PATH"]}'
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(installed.is_symlink())
        self.assertEqual(installed.read_bytes(), self.binary.read_bytes())
        self.assertEqual(previous.read_text(), '#!/bin/sh\nexit 99\n')

    def test_checksum_failure_preserves_existing_install(self):
        self.bin_dir.mkdir(parents=True)
        existing = self.bin_dir / 'gen-pass'
        existing.write_text('existing binary')
        self.archive.write_bytes(self.archive.read_bytes() + b'tampered')
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('SHA-256 mismatch', result.stderr)
        self.assertEqual(existing.read_text(), 'existing binary')

    def test_failed_download_does_not_install(self):
        self.archive.unlink()
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.bin_dir.exists())

    def test_wrong_cpu_does_not_download(self):
        self.fake('uname', '#!/bin/sh\nif [ "$1" = -s ]; then echo Linux; else echo riscv64; fi\n')
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Supported CPUs', result.stderr)
        self.assertFalse(self.bin_dir.exists())

    def test_invalid_version_does_not_download(self):
        self.env['GEN_PASS_VERSION'] = '../v0.1.0'
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Invalid GEN_PASS_VERSION', result.stderr)

    def test_unrunnable_binary_preserves_existing_install(self):
        self.binary.write_text('#!/bin/sh\nexit 1\n')
        release.package_release(self.binary, self.fixture, 'linux-x86_64')
        self.bin_dir.mkdir(parents=True)
        existing = self.bin_dir / 'gen-pass'
        existing.write_text('existing binary')
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(existing.read_text(), 'existing binary')


if __name__ == '__main__':
    unittest.main()
