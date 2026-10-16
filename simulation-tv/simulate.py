"""Simulation d'une TV 55" (Samsung Neo QLED 4K) au mur face au lit.

Modèle de perspective estimé à partir de la photo 1 (pas de mesures réelles) :
point de fuite (1276, 297), focale ~810 px, appareil à 1,58 m du sol,
à 0,29 m du mur droit, mur du fond à 3,7 m. Plafond supposé à 2,80 m.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sys

SRC = sys.argv[1]
OUT = sys.argv[2]

VX, VY, F, CAM_H, X_R, Z_BACK = 1276, 297, 810, 1.58, 0.29, 3.70
TV_W, TV_H = 1.227, 0.706          # 55" Samsung Neo QLED (sans pied)
TV_CENTER_D = 1.07                 # axe du lit, depuis le mur fenêtre (m)
TV_BOTTOM = 0.85                   # bas de l'écran (m)

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def wall_to_img(d, h, depth=0.0):
    """Point du mur droit: d = distance au mur fenêtre, h = hauteur, depth = saillie."""
    z = Z_BACK - d
    return (VX + F * (X_R - depth) / z, VY + (CAM_H - h) * F / z)


def quad(d0, d1, h0, h1, depth=0.0):
    return [wall_to_img(d0, h0, depth), wall_to_img(d1, h0, depth),
            wall_to_img(d1, h1, depth), wall_to_img(d0, h1, depth)]


img = Image.open(SRC).convert("RGB")
img = img.resize((2000, round(img.height * 2000 / img.width)), Image.LANCZOS)  # repère en 2000 px
S = 3  # suréchantillonnage pour l'anticrénelage
big = img.resize((img.width * S, img.height * S), Image.LANCZOS)
ov = Image.new("RGBA", big.size, (0, 0, 0, 0))
dr = ImageDraw.Draw(ov)
sc = lambda pts: [(x * S, y * S) for x, y in pts]

d0, d1 = TV_CENTER_D - TV_W / 2, TV_CENTER_D + TV_W / 2
h0, h1 = TV_BOTTOM, TV_BOTTOM + TV_H

# ombre portée sur le mur
shadow = Image.new("RGBA", big.size, (0, 0, 0, 0))
ImageDraw.Draw(shadow).polygon(sc(quad(d0 + 0.03, d1 + 0.05, h0 - 0.04, h1 - 0.01)), fill=(0, 0, 0, 110))
shadow = shadow.filter(ImageFilter.GaussianBlur(6 * S))
big = Image.alpha_composite(big.convert("RGBA"), shadow)

# tranche de la TV (épaisseur ~4 cm avec support plat)
dr.polygon(sc([wall_to_img(d1, h0, 0), wall_to_img(d1, h0, 0.04),
               wall_to_img(d1, h1, 0.04), wall_to_img(d1, h1, 0)]), fill=(55, 55, 58, 255))
dr.polygon(sc([wall_to_img(d0, h0, 0), wall_to_img(d1, h0, 0),
               wall_to_img(d1, h0, 0.04), wall_to_img(d0, h0, 0.04)]), fill=(40, 40, 42, 255))
# façade (cadre fin + dalle)
dr.polygon(sc(quad(d0, d1, h0, h1, 0.04)), fill=(28, 28, 30, 255))
dr.polygon(sc(quad(d0 + 0.012, d1 - 0.012, h0 + 0.02, h1 - 0.012, 0.04)), fill=(8, 10, 16, 255))
# léger reflet
dr.polygon(sc([wall_to_img(d0 + 0.05, h1 - 0.02, 0.04), wall_to_img(d0 + 0.45, h1 - 0.02, 0.04),
               wall_to_img(d0 + 0.15, h0 + 0.03, 0.04), wall_to_img(d0 + 0.02, h0 + 0.03, 0.04)]),
           fill=(255, 255, 255, 18))

big = Image.alpha_composite(big, ov)
out = big.resize(img.size, Image.LANCZOS).convert("RGB")

# encart zoom
xs = [p[0] for p in quad(d0, d1, h0, h1)]
ys = [p[1] for p in quad(d0, d1, h0, h1)]
cx0, cy0, cx1, cy1 = int(min(xs)) - 50, int(min(ys)) - 60, int(max(xs)) + 60, int(max(ys)) + 60
crop = out.crop((cx0, cy0, cx1, cy1))
zoom = 2.0
crop = crop.resize((int(crop.width * zoom), int(crop.height * zoom)), Image.LANCZOS)
d = ImageDraw.Draw(out)
d.rectangle((cx0, cy0, cx1, cy1), outline=(255, 196, 0), width=4)
px, py = 1560, 230
out.paste(crop, (px, py))
d.rectangle((px, py, px + crop.width, py + crop.height), outline=(255, 196, 0), width=5)
d.line([(cx1, cy0), (px, py)], fill=(255, 196, 0), width=3)
d.line([(cx1, cy1), (px, py + crop.height)], fill=(255, 196, 0), width=3)

f_t = ImageFont.truetype(FONT_B, 34)
f_s = ImageFont.truetype(FONT, 26)
box = (24, 24, 900, 200)
d.rounded_rectangle(box, 14, fill=(20, 20, 24))
d.text((46, 40), 'TV 55" Neo QLED – support mural', font=f_t, fill="white")
d.text((46, 92), "Centrée sur le lit · bas de l'écran à 85 cm du sol", font=f_s, fill=(220, 220, 220))
d.text((46, 130), "Perspective estimée (mur vu presque de profil)", font=f_s, fill=(255, 196, 0))
d.text((px + 12, py + crop.height + 10), "Zoom ×2", font=f_s, fill=(255, 196, 0))
out.save(OUT, quality=92)
print("ok", (cx0, cy0, cx1, cy1))
