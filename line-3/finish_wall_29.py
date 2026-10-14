"""One-time assembly of image-editor pixels while retaining the ancestor wall.

This production helper is not a Code Surface dependency. Inputs are the record-28
wall.png and the generated wall-v9.png. It retains only the new head and two doors;
the editor's third door was too close to an inherited stone. No mark is drawn here.
"""
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
ancestor_path = ROOT / 'artifacts/line-3/wall.png'
generated_path = ROOT / 'artifacts/line-3/wall-v9.png'
ancestor_bytes = ancestor_path.read_bytes()
generated_bytes = generated_path.read_bytes()
assert hashlib.sha256(ancestor_bytes).hexdigest() == '81e288a895703f3e97f298f5a62ccbe22500726ce4f82eb529d9751629d102c0'
width, height, ancestor = thumbnail.png_rgb(ancestor_path)
gw, gh, generated = thumbnail.png_rgb(generated_path)
assert (width, height) == (gw, gh) == (1254, 1254)
# Source rectangles contain only this round's new pixels and bare rock.
# Destination rectangles are wholly clear of ancestor pigment.
patches = [(953, 389, 1097, 492, 953, 389), (995, 489, 1117, 582, 995, 489)]
rows = [bytearray(row) for row in ancestor]
boxes = []
for sx0, sy0, sx1, sy1, dx0, dy0 in patches:
    w, h = sx1 - sx0, sy1 - sy0
    boxes.append([dx0, dy0, dx0 + w, dy0 + h])
    for dy in range(h):
        for dx in range(w):
            alpha = min(1, min(dx, dy, w - 1 - dx, h - 1 - dy) / 8)
            for c in range(3):
                old = ancestor[dy0 + dy][3 * (dx0 + dx) + c]
                new = generated[sy0 + dy][3 * (sx0 + dx) + c]
                rows[dy0 + dy][3 * (dx0 + dx) + c] = round(old * (1 - alpha) + new * alpha)
inside = outside = 0
for y in range(height):
    for x in range(width):
        if rows[y][3*x:3*x+3] != ancestor[y][3*x:3*x+3]:
            if any(x0 <= x < x1 and y0 <= y < y1 for x0, y0, x1, y1 in boxes):
                inside += 1
            else:
                outside += 1
assert inside > 0 and outside == 0


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))


png = b'\x89PNG\r\n\x1a\n'
png += chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
png += chunk(b'IDAT', zlib.compress(b''.join(b'\0' + row for row in rows), 9))
png += chunk(b'IEND', b'')
generated_path.write_bytes(png)
ancestor_path.write_bytes(png)
jpeg = thumbnail.jpeg(thumbnail.resize(width, height, rows, 512))
assert len(jpeg) < 100000
with (ROOT / 'dist/line-3/29.jpg').open('wb') as stream:
    stream.write(jpeg)
report = {
    'ancestor_sha256': hashlib.sha256(ancestor_bytes).hexdigest(),
    'generated_before_assembly_sha256': hashlib.sha256(generated_bytes).hexdigest(),
    'wall_sha256': hashlib.sha256(png).hexdigest(), 'format': 'PNG',
    'dimensions': [width, height], 'mode': 'RGB', 'wall_bytes': len(png),
    'addition_boxes_xyxy': boxes, 'changed_pixels_inside_boxes': inside,
    'changed_pixels_outside_boxes': outside,
    'thumbnail': {'path': 'dist/line-3/29.jpg', 'format': 'JPEG', 'dimensions': [512, 512],
                  'bytes': len(jpeg), 'sha256': hashlib.sha256(jpeg).hexdigest()},
    'manual_review_pending': True,
}
(ROOT / 'line-3/visual-checks-29.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
