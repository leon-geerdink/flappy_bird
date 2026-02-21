"""Generate the Birdy & Llama app icon."""
import struct
import zlib

SIZE = 512

def create_png(pixels, width, height):
    """Create a PNG file from RGBA pixel data."""
    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack('>I', zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack('>I', len(data)) + c + crc

    header = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))

    raw = b''
    for y in range(height):
        raw += b'\x00'
        for x in range(width):
            idx = (y * width + x) * 4
            raw += bytes(pixels[idx:idx+4])

    idat = chunk(b'IDAT', zlib.compress(raw, 9))
    iend = chunk(b'IEND', b'')
    return header + ihdr + idat + iend

def dist(x1, y1, x2, y2):
    return ((x1-x2)**2 + (y1-y2)**2) ** 0.5

def create_icon():
    s = SIZE
    pixels = [0] * (s * s * 4)

    for y in range(s):
        for x in range(s):
            idx = (y * s + x) * 4
            ny, nx = y / s, x / s

            # Sky gradient background
            r = int(100 + 80 * (1 - ny))
            g = int(180 + 50 * (1 - ny))
            b = int(220 + 35 * (1 - ny))
            a = 255

            # Rounded square mask
            margin = 0.02
            radius = 0.18
            cx = max(margin + radius, min(nx, 1 - margin - radius))
            cy = max(margin + radius, min(ny, 1 - margin - radius))
            d = dist(nx, ny, cx, cy)
            if nx < margin or nx > 1 - margin or ny < margin or ny > 1 - margin:
                if d > radius:
                    a = 0

            # Ground
            if ny > 0.78:
                r, g, b = 210, 180, 140
                if 0.78 < ny < 0.81:
                    r, g, b = 120, 180, 80

            # Pipe left
            px, pw = 0.12, 0.13
            if px <= nx <= px + pw:
                if 0.0 < ny < 0.35 or 0.30 < ny < 0.38:
                    cap = 0.30 < ny < 0.38
                    r, g, b = (50, 160, 50) if not cap else (40, 140, 40)
                    # Pipe shading
                    pipe_nx = (nx - px) / pw
                    shade = 1.0 - 0.4 * abs(pipe_nx - 0.35)
                    r, g, b = int(r*shade), int(g*shade), int(b*shade)

            # Pipe right
            px2 = 0.72
            if px2 <= nx <= px2 + pw:
                if 0.55 < ny < 0.78 or 0.52 < ny < 0.58:
                    cap = 0.52 < ny < 0.58
                    r, g, b = (50, 160, 50) if not cap else (40, 140, 40)
                    pipe_nx = (nx - px2) / pw
                    shade = 1.0 - 0.4 * abs(pipe_nx - 0.35)
                    r, g, b = int(r*shade), int(g*shade), int(b*shade)

            # Bird body
            bird_cx, bird_cy = 0.45, 0.48
            bird_rx, bird_ry = 0.12, 0.09
            bx = (nx - bird_cx) / bird_rx
            by = (ny - bird_cy) / bird_ry
            if bx*bx + by*by <= 1.0:
                r, g, b = 255, 210, 50
                # Belly
                if by > 0.2:
                    r, g, b = 255, 235, 150
                # Wing
                if -0.3 < bx < 0.5 and 0.0 < by < 0.7:
                    wing_d = dist(bx, by, 0.1, 0.35)
                    if wing_d < 0.45:
                        r, g, b = 230, 180, 30

            # Eye (white)
            eye_cx, eye_cy, eye_r = 0.51, 0.43, 0.032
            if dist(nx, ny, eye_cx, eye_cy) < eye_r:
                r, g, b = 255, 255, 255

            # Pupil
            if dist(nx, ny, 0.52, 0.43) < 0.018:
                r, g, b = 0, 0, 0

            # Beak
            beak_cx, beak_cy = 0.56, 0.50
            if 0.53 < nx < 0.63 and 0.47 < ny < 0.54:
                beak_d = (nx - beak_cx) / 0.07
                beak_dy = abs(ny - beak_cy) / 0.035
                if beak_d + beak_dy < 1.2:
                    r, g, b = 230, 120, 30
                    if ny > 0.505:
                        r, g, b = 200, 90, 20

            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))

            pixels[idx] = r
            pixels[idx+1] = g
            pixels[idx+2] = b
            pixels[idx+3] = a

    return create_png(pixels, s, s)

if __name__ == '__main__':
    png_data = create_icon()
    with open('/Users/leongeerdink/dev/fun/flappy_icon.png', 'wb') as f:
        f.write(png_data)
    print("Icon created!")
