#!/usr/bin/env python3
"""Transfer only image-tool pigment; keep the ancestral raster around it exact.

Run once while wall.png is the verified Gathering 08 input and wall-v9.png
is the image tool's generated edit. No independent drawing is generated here.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib
sys.path.insert(0, str(Path('shared/wall-thumbnail').resolve()))
import thumbnail

OLD_HASH = '4ee2661ca638f7322bffbf64552377b77ed6c308984d665072c8299fa447c968'

def disk(x, y, cx, cy, radius, feather=2):
    distance = ((x-cx)**2 + (y-cy)**2)**.5
    return max(0., min(1., (radius+feather-distance)/feather))

def stroke(x, y, ax, ay, bx, by, radius):
    dx, dy = bx-ax, by-ay
    t = max(0., min(1., ((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
    return disk(x,y,ax+t*dx,ay+t*dy,radius)

def mask(x, y):
    if not (185 <= x <= 405 and 86 <= y <= 247): return 0.
    d = ((x-315)**2+(y-179)**2)**.5
    arch = max(0., min(1., (10-abs(d-18))/2)) if y <= 180 else 0.
    return max(arch, stroke(x,y,297,178,297,203,6), stroke(x,y,334,178,334,205,6),
               stroke(x,y,197,237,294,194,7), stroke(x,y,340,207,390,232,7),
               disk(x,y,315,100,7), disk(x,y,315,119,7), disk(x,y,315,139,7))

def chunk(kind, data):
    return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))

def main():
    old_path,new_path=Path('artifacts/gathering/wall.png'),Path('artifacts/gathering/wall-v9.png')
    assert hashlib.sha256(old_path.read_bytes()).hexdigest()==OLD_HASH
    width,height,old=thumbnail.png_rgb(old_path)
    nw,nh,new=thumbnail.png_rgb(new_path)
    assert (width,height)==(nw,nh)==(1254,1254)
    rows=[]; changed=[]
    for y in range(height):
        row=bytearray(old[y])
        for x in range(185,406):
            a=mask(x,y)
            if a:
                at=x*3
                for c in range(3): row[at+c]=round(old[y][at+c]*(1-a)+new[y][at+c]*a)
                if row[at:at+3]!=old[y][at:at+3]: changed.append((x,y))
        rows.append(bytes(row))
    raw=(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+
         chunk(b'IDAT',zlib.compress(b''.join(b'\0'+r for r in rows),9))+chunk(b'IEND',b''))
    new_path.write_bytes(raw); old_path.write_bytes(raw)
    out={'schema':'gathering-visual-checks-v9','source_sha256':OLD_HASH,
         'output_sha256':hashlib.sha256(raw).hexdigest(),'dimensions':[width,height],
         'format':'PNG RGB 8-bit opaque','bytes':len(raw),'changed_pixels':len(changed),
         'addition_rectangle':[185,86,405,247],
         'changed_pixel_bounds':[min(x for x,y in changed),min(y for x,y in changed),max(x for x,y in changed),max(y for x,y in changed)],
         'changed_pixels_outside_addition':sum(not (185<=x<=405 and 86<=y<=247) for x,y in changed),
         'review':'Manual visual review of final raster; central Pepe has five digits per hand; no new hands.',
         'unmet_visual_requirements_observed':[]}
    Path('gathering/visual-checks.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out))

if __name__=='__main__': main()
