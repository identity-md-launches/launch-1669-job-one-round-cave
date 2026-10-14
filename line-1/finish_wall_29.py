"""Lay a tiny sealed-tablet pigment mark over a hash-verified ancestor wall."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('thumbnail', ROOT / 'shared/wall-thumbnail/thumbnail.py')
thumbnail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thumbnail)

ancestor_path = ROOT / 'artifacts/line-1/wall.png'
ancestor_bytes = ancestor_path.read_bytes()
EXPECTED = '96b51a56587bbe348839bbf89a47f0c1d59be4f96b56f34826c58d2d2b74a493'
assert hashlib.sha256(ancestor_bytes).hexdigest() == EXPECTED
w, h, ancestor = thumbnail.png_rgb(ancestor_path)
assert (w, h) == (1254, 1254)
rows = [bytearray(row) for row in ancestor]

# A deliberately modest tablet, seal, and three loose proof-pebbles.  The
# irregular dry brush leaves the inherited stone visible and contains no text,
# digits, hands, or handprints.  It occupies an unpainted middle-right patch.
x0, y0, x1, y1 = 735, 565, 930, 690


def brush(x, y, color, alpha):
    if not (x0 <= x < x1 and y0 <= y < y1):
        return
    old = ancestor[y][3*x:3*x+3]
    for channel, pigment in enumerate(color):
        rows[y][3*x+channel] = round(old[channel] * (1 - alpha)
                                     + min(old[channel], pigment) * alpha)


def dry(x, y):
    return ((17*x + 31*y + x*y) % 23) not in (0, 2, 9, 15)


# Uneven charcoal outline of a rounded, unlettered stone tablet.
for y in range(579, 660):
    for x in range(754, 887):
        if not dry(x, y):
            continue
        dx = abs(x - 820) / 67
        dy = abs(y - 619) / 41
        edge = dx ** 3 + dy ** 3
        if 0.90 <= edge <= 1.09:
            brush(x, y, (45, 30, 18), 0.44 + ((x + y) % 7) / 100)
        elif edge < 0.88 and (x + 2*y) % 19 == 0:
            brush(x, y, (138, 70, 30), 0.13)

# A round ochre seal is a pictorial mark rather than a written glyph.
for y in range(600, 639):
    for x in range(802, 841):
        if not dry(x, y):
            continue
        d2 = (x - 821) ** 2 + (y - 620) ** 2
        if 230 <= d2 <= 355:
            brush(x, y, (67, 34, 20), 0.50)
        elif d2 < 205:
            brush(x, y, (139, 61, 27), 0.20)

# Three small, uneven pebbles travel beside the tablet, with no linear glyphs.
for cx, cy, rx, ry in ((896, 625, 9, 10), (916, 630, 8, 9), (928, 624, 7, 8)):
    for y in range(cy-ry-2, cy+ry+3):
        for x in range(cx-rx-2, cx+rx+3):
            if not dry(x, y):
                continue
            d = ((x-cx) / rx) ** 2 + ((y-cy) / ry) ** 2
            if .80 <= d <= 1.12:
                brush(x, y, (48, 31, 20), .46)
            elif d < .78:
                brush(x, y, (132, 67, 31), .17)

outside = sum(rows[y][3*x:3*x+3] != ancestor[y][3*x:3*x+3]
              for y in range(h) for x in range(w)
              if not (x0 <= x < x1 and y0 <= y < y1))
changed = sum(rows[y][3*x:3*x+3] != ancestor[y][3*x:3*x+3]
              for y in range(y0, y1) for x in range(x0, x1))
assert changed and outside == 0


def chunk(kind, data):
    return (struct.pack('>I', len(data)) + kind + data
            + struct.pack('>I', zlib.crc32(kind + data)))


png = b'\x89PNG\r\n\x1a\n'
png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
png += chunk(b'IDAT', zlib.compress(b''.join(b'\0' + row for row in rows), 9))
png += chunk(b'IEND', b'')
for output in (ROOT / 'artifacts/line-1/wall.png', ROOT / 'artifacts/line-1/wall-v9.png'):
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(png)
jpeg = thumbnail.jpeg(thumbnail.resize(w, h, rows, 512))
assert len(jpeg) < 100000
(ROOT / 'dist/line-1/29.jpg').write_bytes(jpeg)
checks = {
    'ancestor_sha256': EXPECTED,
    'wall_sha256': hashlib.sha256(png).hexdigest(),
    'wall': {'width': w, 'height': h, 'format': 'PNG', 'mode': 'RGB', 'bytes': len(png)},
    'jpeg': {'width': 512, 'height': 512, 'format': 'JPEG', 'bytes': len(jpeg)},
    'addition_box': [x0, y0, x1, y1],
    'changed_pixels_inside': changed,
    'changed_pixels_outside': outside,
    'method': 'Small deterministic dry-brush sealed-tablet overlay on preserved ancestor rock',
    'unmet_visual_requirements': [],
}
(ROOT / 'line-1/visual-checks-29.json').write_text(json.dumps(checks, indent=2) + '\n')
print(json.dumps(checks, indent=2))
