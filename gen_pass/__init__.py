"""Offline password generation using only Python's standard library."""
import argparse
from dataclasses import dataclass
from functools import lru_cache
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import string
import subprocess
import sys

DICTIONARY = Path(__file__).resolve().parent / 'dictionary'


@dataclass(frozen=True)
class Generated:
    password: str
    entropy: float | None
    mode: str


def load_words(path, minimum=1):
    words = path.read_text(encoding='ascii').splitlines()
    if len(words) < minimum:
        raise ValueError(f'Dictionary has too few entries: {path.name}')
    if any(re.fullmatch('[a-z]{2,32}', word) is None for word in words):
        raise ValueError(f'Invalid dictionary entry: {path.name}')
    if len(words) != len(set(words)):
        raise ValueError(f'Duplicate dictionary entry: {path.name}')
    return tuple(words)


def random_password(length, separators):
    if length < 3:
        raise ValueError('Maximum length must be at least 3')
    alphabet = string.ascii_letters + string.digits + separators
    # Reject whole uniformly sampled strings: conditioning preserves uniformity
    # over ALL strings containing the three required character classes.
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c in string.ascii_uppercase for c in password)
                and any(c in string.ascii_lowercase for c in password)
                and any(c in string.digits for c in password)):
            break
    count = 0
    sizes = (26, 26, 10)
    for mask in range(8):
        excluded = sum(sizes[i] for i in range(3) if mask & (1 << i))
        count += (-1) ** mask.bit_count() * (len(alphabet) - excluded) ** length
    return Generated(password, math.log2(count), 'random')


def capitalize_words(words):
    # Exactly uniform over the 2**k - 1 nonempty capitalization patterns.
    mask = secrets.randbelow((1 << len(words)) - 1) + 1
    return [word[0].upper() + word[1:] if mask & (1 << i) else word
            for i, word in enumerate(words)]


def shuffle(items):
    for i in range(len(items) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        items[i], items[j] = items[j], items[i]


def render_phrase(words, digits, separators):
    words = list(words)
    shuffle(words)
    parts = capitalize_words(words)
    number = ''.join(secrets.choice(string.digits) for _ in range(digits))
    parts.insert(secrets.randbelow(len(parts) + 1), number)
    if not separators:
        return ''.join(parts)
    result = parts[0]
    for part in parts[1:]:
        result += secrets.choice(separators) + part
    return result


def length_groups(words, minimum=2):
    groups = {}
    for word in words:
        if len(word) >= minimum:
            groups.setdefault(len(word), []).append(word)
    return {length: tuple(entries) for length, entries in sorted(groups.items())}


def completion_counter(slots):
    @lru_cache(maxsize=None)
    def count(index, remaining):
        if index == len(slots):
            return int(remaining == 0)
        return sum(len(entries) * count(index + 1, remaining - length)
                   for length, entries in slots[index].items() if length <= remaining)
    return count


def choose_words(slots, total_length, count):
    words = []
    remaining = total_length
    for i, groups in enumerate(slots):
        ticket = secrets.randbelow(count(i, remaining))
        for length, entries in groups.items():
            weight = len(entries) * count(i + 1, remaining - length)
            if ticket < weight:
                words.append(secrets.choice(entries))
                remaining -= length
                break
            ticket -= weight
    return words


def bounded_phrase(max_length, japanese, english, separators):
    # Prefer Japanese words of >=6 letters to avoid concentrating all choices
    # on a tiny short-word subset. Introduce short English words as needed.
    preferred = length_groups(japanese, 6)
    full = length_groups(japanese)
    eng = length_groups(english)
    target = min(5, max(2, (max_length - 1) // 6))
    for jp_groups in (preferred, full):
        for k in range(target, 1, -1):
            for jp_count in range(k, -1, -1):
                slots = (jp_groups,) * jp_count + (eng,) * (k - jp_count)
                if any(not slot for slot in slots):
                    continue
                count = completion_counter(slots)
                for digits in range(5, 0, -1):
                    budget = max_length - digits - (k if separators else 0)
                    # Limit work even for a very large user-supplied maximum.
                    upper = min(budget, sum(max(slot) for slot in slots))
                    lower = sum(min(slot) for slot in slots)
                    for letters in range(upper, lower - 1, -1):
                        if count(0, letters):
                            words = choose_words(slots, letters, count)
                            password = render_phrase(words, digits, separators)
                            mode = ('japanese' if jp_count == k else
                                    'english' if jp_count == 0 else 'mixed')
                            return Generated(password, None, mode)
    return random_password(max_length, separators)


def generate(max_length=None, exclude_dash=False, exclude_under=False):
    separators = ('' if exclude_dash else '-') + ('' if exclude_under else '_')
    if max_length is not None and max_length <= 16:
        return random_password(max_length, separators)
    japanese = load_words(DICTIONARY / 'japanese_romaji.txt', minimum=10000)
    if max_length is None:
        words = [secrets.choice(japanese) for _ in range(5)]
        entropy = 5 * math.log2(len(japanese)) + 5 * math.log2(10) if separators else None
        return Generated(render_phrase(words, 5, separators), entropy, 'japanese')
    english = load_words(DICTIONARY / 'english.txt')
    # Even replacement dictionaries cannot give the same spelling two weights.
    jp_set = set(japanese)
    english = tuple(word for word in english if word not in jp_set)
    return bounded_phrase(max_length, japanese, english, separators)


def clipboard_command():
    if sys.platform == 'darwin':
        return ['/usr/bin/pbcopy']
    if sys.platform == 'win32':
        command = shutil.which('clip.exe')
        if command:
            return [command]
        raise RuntimeError('Windows clip.exe was not found; use --no-clipboard to print only')
    if sys.platform.startswith('linux'):
        if os.environ.get('WAYLAND_DISPLAY'):
            command = shutil.which('wl-copy')
            if command:
                return [command, '--type', 'text/plain']
        if os.environ.get('DISPLAY'):
            command = shutil.which('xclip')
            if command:
                return [command, '-selection', 'clipboard']
            command = shutil.which('xsel')
            if command:
                return [command, '--clipboard', '--input']
        raise RuntimeError('Clipboard unavailable: install wl-clipboard (Wayland) or xclip/xsel (X11) in a desktop session, or use --no-clipboard')
    raise RuntimeError('Clipboard is unsupported on this OS; use --no-clipboard to print only')


def copy_to_clipboard(password):
    command = clipboard_command()
    try:
        subprocess.run(command, input=password, text=True,
                       encoding='ascii', capture_output=True, check=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f'Could not copy password to clipboard using {Path(command[0]).name}') from exc


def valid_length(value):
    try:
        length = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError('N must be an integer of at least 3') from exc
    if length < 3:
        raise argparse.ArgumentTypeError('N must be at least 3 (uppercase, lowercase, digit)')
    return length


def main(argv=None):
    parser = argparse.ArgumentParser(description='Generate an offline Japanese romaji password and copy it to the clipboard.')
    parser.add_argument('-n', '--max-length', type=valid_length, metavar='N',
                        help='maximum length; 3–16: exactly N random characters; 17+: passphrase within N')
    parser.add_argument('--exclude-dash', action='store_true', help='exclude -')
    parser.add_argument('--exclude-under', action='store_true', help='exclude _')
    parser.add_argument('--no-clipboard', action='store_true', help='print only (for SSH, servers, and terminals without a clipboard)')
    args = parser.parse_args(argv)
    try:
        result = generate(args.max_length, args.exclude_dash, args.exclude_under)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    entropy = f'~{result.entropy:.1f} bits' if result.entropy is not None else 'N/A'
    print(f'Generated {len(result.password)} character password. Entropy: {entropy}')
    print(result.password, flush=True)
    if not args.no_clipboard:
        try:
            copy_to_clipboard(result.password)
        except RuntimeError as exc:
            print(f'Error: {exc}', file=sys.stderr)
            return 1
    return 0
