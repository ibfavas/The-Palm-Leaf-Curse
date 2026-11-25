"""Render a manuscript leaf on the archive's linen scanning bed."""
import math
import random

from PIL import Image, ImageDraw, ImageFilter


def scan(leaf_number, rows):
    rng = random.Random(1794047 + leaf_number)
    width, height = 1400, 540
    coarse = Image.frombytes("L", (70, 27), rng.randbytes(70 * 27)).resize((width, height), Image.Resampling.BICUBIC)
    grain = Image.frombytes("L", (width, height), rng.randbytes(width * height))
    light = Image.blend(coarse, grain, .23)
    bed = light.convert("RGB").point(tuple(v for low, spread in [(33, 22), (33, 19), (27, 15)] for v in [low + j * spread // 255 for j in range(256)]))
    top, bottom = 132, 397
    def edge(x):
        return 8 * math.sin(x / 375) + 2 * math.sin(x / 70)
    xs = range(59, 1343, 3)
    outline = [(x, top + edge(x) + rng.uniform(-2, 2)) for x in xs]
    outline += [(x, bottom + edge(x) + rng.uniform(-3, 3)) for x in reversed(xs)]
    mask = Image.new("L", bed.size)
    md = ImageDraw.Draw(mask)
    md.polygon(outline, fill=255)
    hole = (width // 2 - 12, 255, width // 2 + 13, 279)
    md.ellipse(hole, fill=0)
    shadow = Image.new("L", bed.size)
    shadow.paste(mask, (4, 10))
    bed.paste((18, 17, 13), mask=shadow.filter(ImageFilter.GaussianBlur(6)))
    fibers = Image.frombytes("L", (17, height), rng.randbytes(17 * height)).resize(bed.size, Image.Resampling.BICUBIC)
    tone = Image.blend(light, fibers, .48)
    leaf = tone.convert("RGB").point(tuple(v for low, spread in [(65, 136), (40, 122), (23, 85)] for v in [low + j * spread // 255 for j in range(256)]))
    pen = ImageDraw.Draw(leaf)
    for _ in range(1600):
        x, y = rng.randint(55, 1340), rng.uniform(top, bottom)
        end = min(1340, x + rng.expovariate(1 / 90))
        mid = ((x + end) / 2, y + rng.uniform(-1.5, 1.5))
        color = rng.choice([(126, 95, 55), (151, 117, 73), (108, 78, 48)])
        pen.line([(x, y), mid, (end, y)], fill=color)
    # Reuse a few stylus marks to make each row look hand-etched.
    alphabet = []
    for _ in range(32):
        span = rng.randrange(12, 24)
        loops = rng.choice([1, 1, 2])
        strokes = []
        for j in range(loops):
            cx = (j + .5) * span / loops
            rise, tilt = rng.uniform(4, 8), rng.uniform(-2, 2)
            start, length = rng.uniform(-2.8, -.8), rng.uniform(4.7, 6.8)
            stroke = []
            for step in range(21):
                a = start + length * step / 20
                stroke.append((cx + math.cos(a) * span / (2.1 * loops) + tilt * math.sin(a), rise * math.sin(a)))
            strokes.append(stroke)
        x, y = strokes[-1][-1]
        strokes[-1] += [(x+2, y-3), (span-1, -11), (span+1, -12)]
        alphabet.append((span, strokes))
    for row in range(rows):
        y = (top+bottom)/2 if rows == 1 else top + 52 + row * 32
        x = 100 if rows > 1 else 393
        right = 1305 if rows > 1 else 1000
        while x < right:
            if 660 < x < 734:
                x = 744
            span, strokes = rng.choice(alphabet)
            baseline = y + edge(x) + rng.uniform(-1.7, 1.7)
            for stroke in strokes:
                pts = [(x+a, baseline+b) for a,b in stroke]
                pen.line([(a,b+1.4) for a,b in pts], fill=(177,135,85), width=2)
                pen.line(pts, fill=rng.choice([(60,44,28),(55,39,26),(72,50,29)]), width=2)
            x += span + rng.choice([2, 3, 3, 8])
    pen.ellipse((hole[0]-3,hole[1]-3,hole[2]+3,hole[3]+3), outline=(81, 55, 34), width=3)
    bed.paste(leaf, mask=mask)
    return bed


def first_page(destination, message):
    image = scan(1, 6)
    data = bytearray(image.tobytes())
    for i, value in enumerate(message.encode() + b"\0"):
        for j in range(8):
            index = i * 8 + j
            data[index] = (data[index] & 254) | ((value >> (7 - j)) & 1)
    Image.frombytes("RGB", image.size, bytes(data)).save(destination)
