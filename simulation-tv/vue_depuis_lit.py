"""Vue de face (élévation à l'échelle) du mur face au lit, telle que vue depuis l'oreiller."""
from PIL import Image, ImageDraw, ImageFont

PX = 300                       # px par mètre
WALL_W, WALL_H = 3.70, 2.80    # estimés depuis la photo
M = 140
W, H = int(WALL_W * PX) + 2 * M, int(WALL_H * PX) + 2 * M + 60
img = Image.new("RGB", (W, H), (250, 250, 248))
d = ImageDraw.Draw(img)
f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)

def P(x, y):  # x depuis le mur fenêtre (gauche), y hauteur
    return (M + x * PX, M + 60 + (WALL_H - y) * PX)

def dim(x0, y0, x1, y1, txt, off=(0, 0)):
    d.line([P(x0, y0), P(x1, y1)], fill=(200, 60, 40), width=2)
    for x, y in ((x0, y0), (x1, y1)):
        cx, cy = P(x, y)
        d.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=(200, 60, 40))
    mx, my = P((x0 + x1) / 2, (y0 + y1) / 2)
    d.text((mx + off[0], my + off[1]), txt, font=f, fill=(200, 60, 40), anchor="mm")

d.text((M, 30), 'Vue depuis le lit – mur en face (échelle approx.)', font=fb, fill=(20, 20, 20))
d.rectangle([P(0, WALL_H), P(WALL_W, 0)], fill=(238, 238, 236), outline=(90, 90, 90), width=3)
d.rectangle([P(0, 0.10), P(WALL_W, 0)], fill=(110, 112, 115))  # plinthe
d.text(P(0.05, 2.70), "← mur fenêtre", font=f, fill=(90, 90, 90))
d.text(P(WALL_W - 0.05, 2.70), "porte →", font=f, fill=(90, 90, 90), anchor="ra")

# pied de lit (bed 140, axe à 1,07 m du mur fenêtre)
bx, bw = 1.07, 1.40
d.rectangle([P(bx - bw / 2, 0.58), P(bx + bw / 2, 0.05)], fill=(232, 140, 50), outline=(150, 80, 30), width=2)
d.text(P(bx, 0.32), "pied du lit (140 cm, estimé)", font=f, fill=(60, 30, 10), anchor="mm")

# TV
tw, th, tb = 1.227, 0.706, 0.85
d.rectangle([P(bx - tw / 2, tb + th), P(bx + tw / 2, tb)], fill=(15, 17, 24), outline=(50, 50, 55), width=4)
d.text(P(bx, tb + th / 2 + 0.06), 'Neo QLED 55"', font=fb, fill="white", anchor="mm")
d.text(P(bx, tb + th / 2 - 0.08), "122,7 × 70,6 cm", font=f, fill=(190, 190, 190), anchor="mm")
# axe
d.line([P(bx, 2.6), P(bx, 0.6)], fill=(60, 120, 200), width=1)

dim(bx + tw / 2 + 0.12, 0, bx + tw / 2 + 0.12, tb, "85 cm", (45, 0))
dim(bx + tw / 2 + 0.40, 0, bx + tw / 2 + 0.40, tb + th / 2, "≈120 cm\n(centre)", (60, 0))
dim(0, 2.25, bx, 2.25, "≈107 cm (axe du lit)", (0, -18))

# prise / câble existant (estimé)
ox, oy = 2.52, 1.73
cx, cy = P(ox, oy)
d.rectangle((cx - 12, cy - 12, cx + 12, cy + 12), outline=(200, 60, 40), width=3)
d.text((cx, cy + 30), "câble existant\n(~1,4 m hors axe)", font=f, fill=(200, 60, 40), anchor="ma", align="center")

img.save("vue_depuis_lit.png")
