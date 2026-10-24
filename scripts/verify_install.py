#!/usr/bin/env python3
"""Install a wheel into a temporary venv and exercise its command outside the repo."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import venv


def verify(wheel):
    with tempfile.TemporaryDirectory(prefix='gen-pass-install-') as temporary:
        directory = Path(temporary)
        environment = directory / 'venv'
        venv.EnvBuilder(with_pip=True).create(environment)
        binaries = environment / ('Scripts' if sys.platform == 'win32' else 'bin')
        python = binaries / ('python.exe' if sys.platform == 'win32' else 'python')
        command = binaries / ('gen-pass.exe' if sys.platform == 'win32' else 'gen-pass')
        subprocess.run([str(python), '-m', 'pip', 'install', '--no-index', '--no-deps', str(wheel.resolve())], cwd=directory, capture_output=True, text=True, check=True)
        inspection = subprocess.run([str(python), '-I', '-c', '''
import json
from importlib.metadata import distribution
from pathlib import Path
import gen_pass
d = distribution('gen-pass-romaji')
assert not d.requires, d.requires
for name in ('LICENSE', 'THIRD_PARTY_LICENSES.md', 'Apache-2.0.txt', 'CC-BY-4.0.txt', 'SudachiDict-LEGAL.txt'):
    assert any(p.name == name for p in d.files), name
assert any(e.name == 'gen-pass' and e.value == 'gen_pass:main' for e in d.entry_points)
print(json.dumps({'japanese': len(gen_pass.load_words(gen_pass.DICTIONARY / 'japanese_romaji.txt', 10000)),
                  'english': len(gen_pass.load_words(gen_pass.DICTIONARY / 'english.txt')),
                  'installed': str(Path(gen_pass.__file__).resolve())}))
'''], cwd=directory, capture_output=True, text=True, check=True)
        info = json.loads(inspection.stdout)
        assert environment.resolve() in Path(info['installed']).parents, info
        print(f'PASS bundled dictionaries ({info["japanese"]} Japanese / {info["english"]} English), licenses, entry point, zero runtime dependencies')
        for args in ([], ['-n', '8'], ['-n', '16'], ['-n', '17'], ['-n', '32'], ['-n', '32', '--ed', '--eu'], ['--hr'], ['--hr', '-n', '16', '--ed'], ['--hr', '--ed', '--eu']):
            result = subprocess.run([str(command), *args, '--no-clipboard'], cwd=directory, capture_output=True, text=True, check=True)
            header, password = result.stdout.splitlines()
            assert not result.stderr, result.stderr
            assert header.startswith(f'Generated {len(password)} character password. Entropy: ')
            assert re.fullmatch('[A-Za-z0-9_-]+', password)
            if '--hr' in args:
                separator = '_' if '--ed' in args and '--eu' not in args else '' if '--ed' in args else '-'
                assert re.fullmatch(rf'[a-z]{{2,8}}{separator}[a-z]{{2,8}}{separator}[a-z]{{2,8}}{separator}[0-9]{{4}}', password)
            else:
                assert all(re.search(pattern, password) for pattern in ('[A-Z]', '[a-z]', '[0-9]'))
            if '-n' in args:
                maximum = int(args[args.index('-n') + 1])
                assert len(password) <= maximum
                if maximum <= 16 and '--hr' not in args:
                    assert len(password) == maximum
            if '--ed' in args:
                assert '-' not in password
            if '--eu' in args:
                assert '_' not in password
            print('PASS installed gen-pass ' + (' '.join(args) or 'default'))
        result = subprocess.run([str(command), '--help'], cwd=directory, capture_output=True, text=True, check=True)
        assert '--no-clipboard' in result.stdout
        result = subprocess.run([str(command), '-n', '2'], cwd=directory, capture_output=True, text=True)
        assert result.returncode == 2 and not result.stdout
        print('PASS help and invalid length')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wheel', type=Path)
    verify(parser.parse_args().wheel)
