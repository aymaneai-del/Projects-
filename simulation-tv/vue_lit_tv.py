"""TV 55" incrustée sur la photo prise depuis le lit (mur vu de face).

Échelle estimée sur le mur : ~300 px/m dans le repère 2000 px
(plafond ≈ 2,77 m pour ~830 px, largeur du mur ≈ 3,9 m).
La TV est centrée sur les prises existantes, qu'elle cache.
"""
from PIL import Image, ImageDraw, ImageFilter
import sys

SRC, OUT = sys.argv[1], sys.argv[2]
PPM = 300                         # px par mètre sur le plan du mur
CX, TOP = 1035, 262               # centre horizontal et haut de l'écran (px)
W, H = round(1.227 * PPM), round(0.706 * PPM)

img = Image.open(SRC).convert("RGB")
img = img.resize((2000, round(img.height * 2000 / img.width)), Image.LANCZOS)
S = 3
big = img.resize((img.width * S, img.height * S), Image.LANCZOS).convert("RGBA")
x0, y0, x1, y1 = (CX - W / 2) * S, TOP * S, (CX + W / 2) * S, (TOP + H) * S

shadow = Image.new("RGBA", big.size, (0, 0, 0, 0))
ImageDraw.Draw(shadow).rectangle((x0 + 6 * S, y0 + 10 * S, x1 + 6 * S, y1 + 14 * S), fill=(0, 0, 0, 120))
big = Image.alpha_composite(big, shadow.filter(ImageFilter.GaussianBlur(9 * S)))

# image à l'écran : paysage lac au crépuscule (dégradé)
sw, sh = int(x1 - x0), int(y1 - y0)
screen = Image.new("RGB", (sw, sh))
sd = ImageDraw.Draw(screen)
for y in range(sh):
    t = y / sh
    if t < 0.55:
        k = t / 0.55
        c = (int(40 + 200 * k), int(70 + 110 * k), int(140 + 60 * k))
    else:
        k = (t - 0.55) / 0.45
        c = (int(200 - 160 * k), int(170 - 120 * k), int(190 - 90 * k))
    sd.line([(0, y), (sw, y)], fill=c)
hill = [(0, sh * 0.58), (sw * 0.18, sh * 0.47), (sw * 0.35, sh * 0.53), (sw * 0.55, sh * 0.42),
        (sw * 0.78, sh * 0.52), (sw, sh * 0.46), (sw, sh * 0.58)]
sd.polygon(hill, fill=(38, 52, 82))
sd.polygon([(x, sh * 1.16 - y) for x, y in hill], fill=(60, 72, 104))
screen = screen.filter(ImageFilter.GaussianBlur(2 * S))

d = ImageDraw.Draw(big)
d.rectangle((x0, y0, x1, y1), fill=(18, 18, 20, 255))
bz = 4 * S
big.paste(screen.resize((sw - 2 * bz, sh - 2 * bz)), (int(x0 + bz), int(y0 + bz)))
refl = Image.new("RGBA", big.size, (0, 0, 0, 0))
ImageDraw.Draw(refl).polygon([(x0 + bz, y0 + bz), (x0 + sw * 0.35, y0 + bz), (x0 + sw * 0.12, y1 - bz), (x0 + bz, y1 - bz)],
          fill=(255, 255, 255, 14))
big = Image.alpha_composite(big, refl)
big.resize(img.size, Image.LANCZOS).convert("RGB").save(OUT, quality=92)
print("ok", W, H)
