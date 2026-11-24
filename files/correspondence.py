import random
import textwrap

from PIL import Image, ImageDraw, ImageFont


def middle_leaves(message, key):
    key = [ord(k) - ord("A") for k in key]
    out = []
    pos = 0
    for c in message:
        if c.isascii() and c.isalpha():
            base = ord("A" if c.isupper() else "a")
            c = chr(base + (ord(c) - base + key[pos % len(key)]) % 26)
            pos += 1
        out.append(c)
    return "".join(out)


def priest_letter(destination, body, temple):
    rng = random.Random(1974047)
    size = (860, 1060)
    grain = Image.frombytes("L", size, rng.randbytes(size[0]*size[1]))
    paper = Image.merge("RGB", tuple(grain.point(lambda n, b=b: b+n//18) for b in (208, 192, 151)))
    pen = ImageDraw.Draw(paper)
    ink = (61, 54, 48)
    def type_line(x,y,line,point):
        font = ImageFont.load_default(size=point)
        for c in line:
            pen.text((x,y+rng.choice([0,0,0,1])),c,font=font,fill=ink)
            x += point*.61
    type_line(76,88,temple.upper(),25)
    type_line(77,132,"Private correspondence     /     1974",18)
    pen.line((76,180,778,181),fill=(114,96,74),width=2)
    type_line(76,242,"To the temple committee,",20)
    for i,line in enumerate(textwrap.wrap(body,53)):
        type_line(76,310+38*i,line,21)
    type_line(76,725,"Vasudevan Namboothiri",22)
    pen.line((24,536,838,539),fill=(184,166,134),width=2)
    pen.line((24,539,838,542),fill=(224,210,174),width=2)
    pen.ellipse((560,847,765,925),outline=(131,100,85),width=3)
    type_line(590,869,"FILE COPY",21)
    paper.save(destination)
