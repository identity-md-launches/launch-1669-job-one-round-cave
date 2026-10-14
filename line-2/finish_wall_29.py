#!/usr/bin/env python3
"""Add one generated transparent pigment insert; receive base64 only on stdin.

No insert picture is saved. Refuses to repaint anything but the exact ancestor.
"""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import finish_wall_26 as imageops

ROOT = Path(__file__).resolve().parents[1]
WALL = ROOT / 'artifacts/line-2/wall.png'
SOURCE_SHA256 = 'ead64051ad3128da20251e58a32f4a66607376a53a3e396df16f9cb8a74fea9f'
PLACEMENT = (655, 180, 170, 100)


def main():
    source = WALL.read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError('expected the exact record-28 wall')
    width, height, channels, original = imageops.decode(source)
    assert (width, height, channels) == (1254, 1254, 3)
    chunks = []
    for line in sys.stdin.buffer:
        if line.strip() == b'END':
            break
        chunks.append(line.strip())
    else:
        raise ValueError('missing END marker')
    mark = imageops.decode(base64.b64decode(b''.join(chunks), validate=True))
    # Keep opaque pigment flecks; omit the generator's faint background haze.
    # This mask affects only the new insert, never any ancestor pixel.
    mw, mh, mc, markrows = mark
    if mc != 4:
        raise ValueError('expected transparent RGBA pigment')
    cleaned = []
    for row in markrows:
        row = bytearray(row)
        for offset in range(3, len(row), 4):
            if row[offset] < 120:
                row[offset] = 0
        cleaned.append(bytes(row))
    mark = (mw, mh, mc, cleaned)
    imageops.PLACE_X, imageops.PLACE_Y, imageops.PLACE_W, imageops.PLACE_H = PLACEMENT
    rows, bounds = imageops.composite(original, mark)
    x, y, w, h = PLACEMENT
    for rownum, (old, new) in enumerate(zip(original, rows)):
        if not y <= rownum < y + h:
            assert old == new
        else:
            assert old[:x * 3] == new[:x * 3]
            assert old[(x + w) * 3:] == new[(x + w) * 3:]
    output = imageops.encode(width, height, rows)
    WALL.write_bytes(output)
    target = WALL.parent / 'wall-v9.png'
    target.write_bytes(output)
    spec = importlib.util.spec_from_file_location('thumbnail', ROOT / 'shared/wall-thumbnail/thumbnail.py')
    thumbnail = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(thumbnail)
    jpeg = thumbnail.jpeg(thumbnail.resize(width, height, rows, 512))
    assert len(jpeg) < 100000
    preview = ROOT / 'dist/line-2/29.jpg'
    with preview.open('xb') as stream:
        stream.write(jpeg)
    digest = hashlib.sha256(output).hexdigest()
    meaning = 'One charcoal cord keeps every reviewed ochre permission together without losing or doubling one.'
    record = {
        'name': 'Every Pebble Held',
        'image': 'https://api.imd.fun/artifacts/' + digest,
        'attributes': [
            {'trait_type': 'Cave', 'value': 'Moss'},
            {'trait_type': 'Wall', 'value': 'Line 2'},
            {'trait_type': 'Number', 'value': 29},
            {'trait_type': 'Left behind', 'value': 'Draft Bundle'},
            {'trait_type': 'Meaning', 'value': meaning},
            {'trait_type': 'One thing', 'value': 'ERC-20 spending-permission audits'},
        ],
    }
    with (ROOT / 'dist/line-2/29.json').open('x') as stream:
        stream.write(json.dumps(record, indent=2) + '\n')
    checks = {
        'source_sha256': SOURCE_SHA256, 'output_sha256': digest,
        'format': 'PNG', 'dimensions': [width, height], 'placement': PLACEMENT,
        'changed_pixels': sum(old[i:i+3] != new[i:i+3] for old, new in zip(original, rows)
                              for i in range(0, len(old), 3)),
        'outside_placement_unchanged': True, 'insert_alpha_bounds': bounds,
        'preview': {'format': 'JPEG', 'dimensions': [512, 512], 'bytes': len(jpeg)},
        'unmet_visual_requirements': [], 'visual_review': 'Pending complete PNG/JPEG inspection',
    }
    (ROOT / 'line-2/visual-checks-29.json').write_text(json.dumps(checks, indent=2) + '\n')
    print(json.dumps(checks))


if __name__ == '__main__':
    main()
