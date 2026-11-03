#!/usr/bin/env python
"""Make a monochrome white version of a logo PNG, for a dark header when the brand ships no
all-white variant. Pure Python (no Pillow): 8-bit RGB/RGBA, non-interlaced PNGs only.

    python png_mono.py <in.png> <out.png> [--floor 1.0]

Every visible pixel becomes white; its own transparency is kept, so parts the logo already draws
as translucent (a back band, a fold) still read as depth. With --floor below 1, colored areas
also turn their shading into opacity: the lightest color stays opaque, darker tones fade to
--floor.

This modifies the client's logo. Most brand guides forbid that - do it only when the user asks,
and record it in brand.json source.logo_note.
"""
import struct
import sys
import zlib


def read_png(path):
    data = open(path, 'rb').read()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        sys.exit('png_mono: not a PNG: ' + path)
    pos, idat, hdr = 8, b'', None
    while pos < len(data):
        n = struct.unpack('>I', data[pos:pos + 4])[0]
        kind, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + n]
        if kind == b'IHDR':
            hdr = struct.unpack('>IIBBBBB', body)
        elif kind == b'IDAT':
            idat += body
        pos += 12 + n
    w, h, depth, ctype, _, _, interlace = hdr
    if depth != 8 or ctype not in (2, 6) or interlace:
        sys.exit('png_mono: only 8-bit RGB/RGBA non-interlaced PNGs are supported')
    bpp = 4 if ctype == 6 else 3
    raw, stride = zlib.decompress(idat), w * bpp
    out, prev, i = bytearray(), bytearray(stride), 0
    for _ in range(h):
        f, line = raw[i], bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        out += line
        prev = line
    if bpp == 3:
        rgba = bytearray()
        for k in range(0, len(out), 3):
            rgba += out[k:k + 3] + b'\xff'
        out = rgba
    return w, h, out


def write_png(path, w, h, rgba):
    rows = b''.join(b'\x00' + bytes(rgba[y * w * 4:(y + 1) * w * 4]) for y in range(h))

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
                           + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))


def main(argv):
    args = [a for a in argv if not a.startswith('--')]
    floor = float(argv[argv.index('--floor') + 1]) if '--floor' in argv else 1.0
    if '--floor' in argv:
        args.remove(argv[argv.index('--floor') + 1])
    if len(args) != 2:
        sys.exit('usage: png_mono.py <in.png> <out.png> [--floor 1.0]')
    w, h, px = read_png(args[0])

    def y(r, g, b):
        return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255

    # Shading reference: the lightest *colored* (non-grey) visible pixel.
    ymax = 0
    for k in range(0, len(px), 4):
        r, g, b, a = px[k:k + 4]
        if a > 32 and max(r, g, b) - min(r, g, b) > 24:
            ymax = max(ymax, y(r, g, b))
    for k in range(0, len(px), 4):
        r, g, b, a = px[k:k + 4]
        if a == 0:
            continue
        colored = max(r, g, b) - min(r, g, b) > 24
        t = 1.0 if not colored or not ymax else min(1.0, floor + (1 - floor) * y(r, g, b) / ymax)
        px[k:k + 4] = bytes((255, 255, 255, round(a * t)))
    write_png(args[1], w, h, px)
    print('png_mono: %s -> %s (%dx%d, all white, shading floor %.2f)' % (args[0], args[1], w, h, floor))


if __name__ == '__main__':
    main(sys.argv[1:])
