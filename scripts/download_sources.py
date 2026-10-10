#!/usr/bin/env python3
"""Explicit build-time download only. The password CLI never imports this file."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def download(destination):
    manifest = json.loads((ROOT / 'gen_pass/dictionary/sources.json').read_text())
    destination.mkdir(parents=True, exist_ok=True)
    for source in manifest['sources']:
        target = destination / source['file']
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == source['sha256']:
            print(f'Already verified: {source["file"]}')
            continue
        print(f'Downloading: {source["file"]}')
        with urllib.request.urlopen(source['url'], timeout=120) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != source['sha256']:
            raise ValueError(f'Upstream checksum mismatch: {source["file"]}')
        target.write_bytes(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=ROOT / '.build/sources')
    download(parser.parse_args().destination)
