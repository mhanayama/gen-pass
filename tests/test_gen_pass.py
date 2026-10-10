import contextlib
import io
import itertools
import math
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import gen_pass as gp


class GeneratorTests(unittest.TestCase):
    def assert_password(self, result, maximum=None, exact=False, forbidden=''):
        password = result.password
        self.assertRegex(password, r'^[a-zA-Z0-9_-]+$')
        for pattern in ('[A-Z]', '[a-z]', '[0-9]'):
            self.assertRegex(password, pattern)
        if maximum is not None:
            self.assertLessEqual(len(password), maximum)
            if exact:
                self.assertEqual(len(password), maximum)
        for character in forbidden:
            self.assertNotIn(character, password)

    def test_default(self):
        jp = set(gp.load_words(gp.DICTIONARY / 'japanese_romaji.txt'))
        for _ in range(20):
            result = gp.generate()
            self.assert_password(result)
            parts = re.split('[-_]', result.password)
            self.assertEqual(len(parts), 6)
            numbers = [part for part in parts if part.isdigit()]
            self.assertEqual(len(numbers), 1)
            self.assertEqual(len(numbers[0]), 5)
            words = [part for part in parts if not part.isdigit()]
            self.assertTrue(all(part.lower() in jp for part in words))
            self.assertGreater(result.entropy, 80)
            self.assertAlmostEqual(result.entropy, 5 * math.log2(len(jp)) + 5 * math.log2(10))

    def test_length_and_exclusion_matrix(self):
        for length, dash, under in itertools.product((3, 8, 12, 16, 17, 18, 23, 32, 64, 1000), (False, True), (False, True)):
            with self.subTest(length=length, dash=dash, under=under):
                for _ in range(3):
                    self.assert_password(gp.generate(length, dash, under), length,
                                         exact=length <= 16,
                                         forbidden=('-' if dash else '') + ('_' if under else ''))

    def test_default_exclusions_and_ambiguous_entropy(self):
        for dash, under in itertools.product((False, True), repeat=2):
            result = gp.generate(None, dash, under)
            self.assert_password(result, forbidden=('-' if dash else '') + ('_' if under else ''))
            if dash and under:
                self.assertIsNone(result.entropy)

    def test_mixed_dictionary(self):
        result = gp.generate(32)
        self.assertEqual(result.mode, 'mixed')
        self.assertEqual(len(result.password), 32)
        parts = {part.lower() for part in re.split('[-_]', result.password) if not part.isdigit()}
        japanese = set(gp.load_words(gp.DICTIONARY / 'japanese_romaji.txt'))
        english = set(gp.load_words(gp.DICTIONARY / 'english.txt'))
        self.assertTrue(parts & japanese)
        self.assertTrue(parts & english)
        self.assertIsNone(result.entropy)

    def test_english_only_and_fallback(self):
        result = gp.bounded_phrase(17, ('extremelylongword',), ('cat', 'dog'), '-')
        self.assertEqual(result.mode, 'english')
        self.assert_password(result, 17)
        result = gp.bounded_phrase(17, ('extremelylongword',), (), '-')
        self.assertEqual(result.mode, 'random')
        self.assert_password(result, 17, exact=True)

    def test_full_short_japanese_tier(self):
        result = gp.bounded_phrase(17, ('yama',), (), '-')
        self.assertEqual(result.mode, 'japanese')
        self.assert_password(result, 17)

    def test_never_fallback_due_to_unlucky_draw(self):
        # Only one feasible pair among many overly long dictionary entries.
        with patch.object(gp, 'random_password', side_effect=AssertionError('unexpected fallback')):
            result = gp.bounded_phrase(17, ('yamato', 'abcdefghijklmnop'), (), '-')
        self.assert_password(result, 17)

    def test_nonconstant_results(self):
        self.assertGreater(len({gp.generate(16).password for _ in range(20)}), 1)

    def test_uniform_capitalization_masks(self):
        outputs = set()
        for value in range(31):
            with patch.object(gp.secrets, 'randbelow', return_value=value) as draw:
                output = gp.capitalize_words(['word'] * 5)
                draw.assert_called_once_with(31)
                self.assertTrue(any(w[0].isupper() for w in output))
                self.assertTrue(all(w[1:] == 'ord' for w in output))
                outputs.add(tuple(output))
        self.assertEqual(len(outputs), 31)

    def test_rejection_samples_entire_random_candidate(self):
        with patch.object(gp.secrets, 'choice', side_effect=list('aaaAb3')) as draw:
            result = gp.random_password(3, '')
        self.assertEqual(result.password, 'Ab3')
        self.assertEqual(draw.call_count, 6)
        self.assertTrue(all(call.args == (gp.string.ascii_letters + gp.string.digits,) for call in draw.call_args_list))

    def test_exact_random_entropy_inclusion_exclusion(self):
        # At length 3, valid strings are permutations of one of each class.
        for separators in ('', '-', '-_'):
            self.assertAlmostEqual(gp.random_password(3, separators).entropy,
                                   math.log2(6 * 26 * 26 * 10))

    def test_completion_counts_match_exhaustive_enumeration(self):
        slots = (gp.length_groups(('aa', 'bb', 'ccc')), gp.length_groups(('dd', 'eee', 'fff')))
        count = gp.completion_counter(slots)
        for budget in range(4, 7):
            expected = sum(len(a) + len(b) == budget for a, b in itertools.product(('aa', 'bb', 'ccc'), ('dd', 'eee', 'fff')))
            self.assertEqual(count(0, budget), expected)
        # First length branch has weight 2*2=4; next has weight 1*1=1.
        chosen = []
        for ticket in range(5):
            with patch.object(gp.secrets, 'randbelow', side_effect=[ticket, 0]), patch.object(gp.secrets, 'choice', side_effect=lambda entries: entries[0]):
                chosen.append(gp.choose_words(slots, 5, count)[0])
        self.assertEqual(chosen, ['aa'] * 4 + ['ccc'])

    def test_leading_zero_and_number_positions(self):
        for position in range(3):
            with patch.object(gp, 'shuffle'), patch.object(gp, 'capitalize_words', return_value=['Word', 'other']), patch.object(gp.secrets, 'choice', side_effect=lambda values: values[0]), patch.object(gp.secrets, 'randbelow', return_value=position):
                result = gp.render_phrase(['word', 'other'], 5, '-')
            self.assertEqual(result.split('-')[position], '00000')

    def test_runtime_has_no_network(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')):
            self.assert_password(gp.generate())
            self.assert_password(gp.generate(32))

    def test_runtime_uses_secrets_not_random(self):
        import ast
        tree = ast.parse(Path(gp.__file__).read_text(encoding='utf-8'))
        imported = {node.name for parent in ast.walk(tree) if isinstance(parent, ast.Import) for node in parent.names}
        self.assertIn('secrets', imported)
        self.assertNotIn('random', imported)
        self.assertNotIn('random', {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)})


class DictionaryTests(unittest.TestCase):
    def test_bundled_dictionaries(self):
        japanese = gp.load_words(gp.DICTIONARY / 'japanese_romaji.txt', minimum=10000)
        english = gp.load_words(gp.DICTIONARY / 'english.txt')
        self.assertFalse(set(japanese) & set(english))
        self.assertGreater(len(english), 1000)
        for word in ('tokyo', 'okonomiyaki', 'marubiru', 'toshiba', 'rettsunoto', 'komorebi'):
            self.assertIn(word, japanese)

    def test_invalid_entries(self):
        for content in ('word\nword\n', 'Good\n', 'two words\n', 'abc-xyz\n', 'abc1\n', '\n', '日本語\n', 'a\n'):
            with tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / 'bad.txt'
                path.write_text(content, encoding='utf-8')
                with self.assertRaises((ValueError, UnicodeError)):
                    gp.load_words(path)

    def test_minimum_entries(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'short.txt'
            path.write_text('word\n')
            with self.assertRaises(ValueError):
                gp.load_words(path, minimum=10000)

    def test_build_romanization(self):
        from scripts.build_dictionary import romanize
        for reading, expected in [('オコノミヤキ','okonomiyaki'), ('マルビル','marubiru'), ('レッツノート','rettsunoto'), ('コモレビ','komorebi'), ('チャット','chatto'), ('シンヨウ','shinyou'), ('スーパー','supa'), ('ﾌｨﾙﾑ','firumu')]:
            self.assertEqual(romanize(reading), expected)
        for reading in ('ー', 'ッ', 'ABC', 'カッア', 'カ・ナ', 'カ1ナ'):
            self.assertIsNone(romanize(reading))


class ClipboardAndCLITests(unittest.TestCase):
    def run_main(self, args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = gp.main(args)
        return status, out.getvalue(), err.getvalue()

    def test_cli_success_and_clipboard_exact_match(self):
        for args in ([], ['-n','8'], ['-n','12'], ['-n','16'], ['-n','17'], ['-n','32'], ['-n','16','--exclude-dash','--exclude-under']):
            with patch.object(gp, 'clipboard_command', return_value=['/usr/bin/pbcopy']), patch.object(gp.subprocess, 'run') as copy, patch.object(gp, 'generate', wraps=gp.generate) as generate:
                status, stdout, stderr = self.run_main(args)
            self.assertEqual(status, 0)
            self.assertEqual(stderr, '')
            generate.assert_called_once()
            header, password = stdout.splitlines()
            self.assertTrue(header.startswith(f'Generated {len(password)} character password. Entropy: '))
            copy.assert_called_once_with(['/usr/bin/pbcopy'], input=password, text=True, encoding='ascii', capture_output=True, check=True, timeout=10)
            self.assertNotIn('\n', copy.call_args.kwargs['input'])

    def test_pbcopy_failures(self):
        errors = (FileNotFoundError(), subprocess.CalledProcessError(1, ['/usr/bin/pbcopy']), subprocess.TimeoutExpired(['/usr/bin/pbcopy'], 10))
        for error in errors:
            with patch.object(gp, 'clipboard_command', return_value=['/usr/bin/pbcopy']), patch.object(gp.subprocess, 'run', side_effect=error):
                status, stdout, stderr = self.run_main(['-n', '8'])
            self.assertEqual(status, 1)
            self.assertIn('pbcopy', stderr)
            self.assertEqual(len(stdout.splitlines()), 2)

    def test_no_clipboard(self):
        with patch.object(gp, 'copy_to_clipboard') as copy:
            status, stdout, stderr = self.run_main(['-n', '8', '--no-clipboard'])
        self.assertEqual(status, 0)
        self.assertEqual(stderr, '')
        self.assertEqual(len(stdout.splitlines()[1]), 8)
        copy.assert_not_called()

    def test_module_entry_point(self):
        result = subprocess.run([sys.executable, '-m', 'gen_pass', '-n', '8', '--no-clipboard'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(result.stdout.splitlines()[1]), 8)

    def test_invalid_cli_in_subprocess(self):
        for value in ('-1', '0', '1', '2', 'abc', '3.5'):
            result = subprocess.run([sys.executable, str(ROOT / 'gen-pass.py'), '-n', value], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, '')
            self.assertIn('error:', result.stderr)

    def test_help_in_subprocess(self):
        result = subprocess.run([sys.executable, str(ROOT / 'gen-pass.py'), '--help'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        for option in ('--max-length', '--exclude-dash', '--exclude-under'):
            self.assertIn(option, result.stdout)

    def test_bad_dictionary_returns_clear_error(self):
        with patch.object(gp, 'load_words', side_effect=ValueError('Invalid dictionary entry')), patch.object(gp, 'copy_to_clipboard') as copy:
            status, stdout, stderr = self.run_main([])
        self.assertEqual(status, 1)
        self.assertEqual(stdout, '')
        self.assertIn('Invalid dictionary', stderr)
        copy.assert_not_called()


class ClipboardBackendTests(unittest.TestCase):
    def command(self, platform, environment=None, available=()):
        def which(name):
            return '/tools/' + name if name in available else None
        with patch.object(gp.sys, 'platform', platform), patch.dict(gp.os.environ, environment or {}, clear=True), patch.object(gp.shutil, 'which', side_effect=which):
            return gp.clipboard_command()

    def test_macos(self):
        self.assertEqual(self.command('darwin'), ['/usr/bin/pbcopy'])

    def test_windows(self):
        self.assertEqual(self.command('win32', available=('clip.exe',)), ['/tools/clip.exe'])
        with self.assertRaisesRegex(RuntimeError, 'clip.exe'):
            self.command('win32')

    def test_wayland_precedes_x11(self):
        self.assertEqual(self.command('linux', {'WAYLAND_DISPLAY': 'wayland-0', 'DISPLAY': ':0'}, ('wl-copy', 'xclip')), ['/tools/wl-copy', '--type', 'text/plain'])

    def test_x11_clipboard_selection(self):
        self.assertEqual(self.command('linux', {'DISPLAY': ':0'}, ('xclip', 'xsel')), ['/tools/xclip', '-selection', 'clipboard'])
        self.assertEqual(self.command('linux', {'DISPLAY': ':0'}, ('xsel',)), ['/tools/xsel', '--clipboard', '--input'])

    def test_wayland_can_use_available_x11(self):
        self.assertEqual(self.command('linux', {'WAYLAND_DISPLAY': 'wayland-0', 'DISPLAY': ':0'}, ('xclip',)), ['/tools/xclip', '-selection', 'clipboard'])

    def test_no_display_or_tools(self):
        for environment, available in (({}, ('xclip', 'wl-copy')), ({'DISPLAY': ':0'}, ()), ({'WAYLAND_DISPLAY': 'wayland-0'}, ())):
            with self.assertRaisesRegex(RuntimeError, '--no-clipboard'):
                self.command('linux', environment, available)

    def test_unsupported_os(self):
        with self.assertRaisesRegex(RuntimeError, '--no-clipboard'):
            self.command('unknown')

    def test_all_backends_use_stdin_without_newline_or_password_argument(self):
        for command in (['/usr/bin/pbcopy'], ['/tools/clip.exe'], ['/tools/wl-copy', '--type', 'text/plain'], ['/tools/xclip', '-selection', 'clipboard'], ['/tools/xsel', '--clipboard', '--input']):
            with patch.object(gp, 'clipboard_command', return_value=command), patch.object(gp.subprocess, 'run') as run:
                gp.copy_to_clipboard('Ab3_test')
            self.assertEqual(run.call_args.args[0], command)
            self.assertEqual(run.call_args.kwargs['input'], 'Ab3_test')
            self.assertNotIn('Ab3_test', command)
            self.assertNotIn('shell', run.call_args.kwargs)


if __name__ == '__main__':
    unittest.main()
