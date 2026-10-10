#!/usr/bin/env python3
"""Rebuild fixed dictionaries from checksum-verified upstream source files."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import unicodedata
import zipfile

ROOT = Path(__file__).resolve().parents[1]
# ASCII Hepburn: long marks are omitted; kana-written vowels are retained.
ROWS = [
    ('アイウエオ', 'a i u e o'), ('カキクケコ', 'ka ki ku ke ko'),
    ('ガギグゲゴ', 'ga gi gu ge go'), ('サシスセソ', 'sa shi su se so'),
    ('ザジズゼゾ', 'za ji zu ze zo'), ('タチツテト', 'ta chi tsu te to'),
    ('ダヂヅデド', 'da ji zu de do'), ('ナニヌネノ', 'na ni nu ne no'),
    ('ハヒフヘホ', 'ha hi fu he ho'), ('バビブベボ', 'ba bi bu be bo'),
    ('パピプペポ', 'pa pi pu pe po'), ('マミムメモ', 'ma mi mu me mo'),
    ('ヤユヨ', 'ya yu yo'), ('ラリルレロ', 'ra ri ru re ro'),
    ('ワヲンヴ', 'wa o n vu'),
]
KANA = {k: v for chars, values in ROWS for k, v in zip(chars, values.split())}
for base, stem in [('キ','ky'), ('ギ','gy'), ('シ','sh'), ('ジ','j'),
                   ('チ','ch'), ('ヂ','j'), ('ニ','ny'), ('ヒ','hy'),
                   ('ビ','by'), ('ピ','py'), ('ミ','my'), ('リ','ry')]:
    for small, vowel in zip('ャュョ', 'auo'):
        KANA[base + small] = stem + vowel
KANA.update(dict(zip(
    'イェ ウィ ウェ ウォ シェ ジェ チェ ティ ディ トゥ ドゥ ツァ ツィ ツェ ツォ ファ フィ フェ フォ フュ ヴァ ヴィ ヴェ ヴォ'.split(),
    'ye wi we wo she je che ti di tu du tsa tsi tse tso fa fi fe fo fyu va vi ve vo'.split())))
OVERRIDES = {'東京': 'tokyo', '東芝': 'toshiba', 'レッツノート': 'rettsunoto'}


def romanize(reading):
    reading = unicodedata.normalize('NFKC', reading)
    reading = ''.join(chr(ord(c) + 96) if 'ぁ' <= c <= 'ゖ' else c for c in reading)
    output = []
    i = 0
    while i < len(reading):
        c = reading[i]
        if c == 'ー':
            if not output or output[-1][-1] not in 'aeiou':
                return None
            i += 1
            continue
        doubled = c == 'ッ'
        if doubled:
            i += 1
        token = reading[i:i+2]
        if token not in KANA:
            token = reading[i:i+1]
        value = KANA.get(token)
        if not value or (doubled and value[0] in 'aeioun'):
            return None
        if doubled:
            output.append('t' if value.startswith('ch') else value[0])
        output.append(value)
        i += len(token)
    return ''.join(output)


def checksum(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def build(source_dir, output_dir):
    manifest = json.loads((ROOT / 'gen_pass/dictionary/sources.json').read_text())
    for source in manifest['sources']:
        path = source_dir / source['file']
        if checksum(path) != source['sha256']:
            raise ValueError(f'Checksum mismatch: {path}')
    # Preserve examples / useful recognizable words, then sample each noun class
    # by a stable hash (build-time selection only; never password randomness).
    groups = {'common': {}, 'place': {}, 'person': {}, 'proper': {}}
    examples = {'東京', 'お好み焼き', '丸ビル', '東芝', 'レッツノート', '木漏れ日'}
    keep = set()
    for name in ('small_lex', 'core_lex', 'notcore_lex'):
        with zipfile.ZipFile(source_dir / f'{name}.zip') as archive:
            with archive.open(f'{name}.csv') as raw:
                for row in csv.reader(io.TextIOWrapper(raw, encoding='utf-8')):
                    surface, reading = row[4], row[11]
                    if row[5] != '名詞' or row[6] not in ('普通名詞', '固有名詞'):
                        continue
                    if row[6] == '普通名詞' and row[7] not in ('一般', 'サ変可能'):
                        continue
                    if not re.fullmatch(r'[一-龯々ぁ-ゖァ-ヺー]{2,12}', surface):
                        continue
                    word = OVERRIDES.get(surface) or romanize(reading)
                    if not word or not re.fullmatch('[a-z]{4,12}', word):
                        continue
                    group = ('common' if row[6] == '普通名詞' else
                             'place' if row[7] == '地名' else
                             'person' if row[7] == '人名' else 'proper')
                    groups[group][word] = None
                    if surface in examples:
                        keep.add(word)
    words = set(keep)
    quotas = {'common': 16384, 'place': 6144, 'person': 6144, 'proper': 4096}
    stats = {}
    for group, candidates in groups.items():
        selected = sorted(candidates, key=lambda w: (hashlib.sha256(w.encode()).digest(), w))[:quotas[group]]
        words.update(selected)
        stats[group] = {'eligible': len(candidates), 'selected': len(selected)}
    if len(words) < 10000:
        raise ValueError('Fewer than 10,000 Japanese entries')
    english = set()
    for line in (source_dir / 'eff_short_wordlist_1.txt').read_text().splitlines():
        _, word = line.split()
        word = word.replace('-', '')
        if not re.fullmatch('[a-z]{3,5}', word):
            raise ValueError(f'Invalid EFF entry: {word}')
        english.add(word)
    # A spelling belongs to Japanese only, avoiding duplicated mixed candidates.
    overlap = english & words
    english -= words
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, entries in [('japanese_romaji.txt', words), ('english.txt', english)]:
        (output_dir / filename).write_text(''.join(w + '\n' for w in sorted(entries)), encoding='ascii')
    stats.update(japanese_count=len(words), english_count=len(english),
                 removed_english_overlap=len(overlap), examples=sorted(keep))
    (output_dir / 'build_stats.json').write_text(json.dumps(stats, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, default=ROOT / '.build/sources')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'gen_pass/dictionary')
    args = parser.parse_args()
    build(args.source_dir, args.output_dir)
