# Erzeugt die Daten, mit denen live_ansicht.py die echte Platine darstellt:
#   Live-Ansicht/platine.json            Lage und Umriss von Funkmodul und ZH-Buchsen
#   Live-Ansicht/textur-platine.png      Oberseite aus dem KiCad-Rendering, auf die Platine zugeschnitten
#   Live-Ansicht/textur-modul-schirm.png Abschirmblech des MDBT42Q (gezeichnet)
#   Live-Ansicht/textur-modul-antenne.png Antennenbereich des MDBT42Q (gezeichnet)
# Aufruf mit dem System-Python (braucht pcbnew aus KiCad und Pillow):
#   python3 platine_ansicht_daten.py
# Hintergrund: Für Raytac_MDBT42Q und JST_ZH_B2B-ZR verweisen die KiCad-Footprints auf
# 3D-Modelle, die es in der KiCad-Bibliothek nicht gibt – deshalb eigene Darstellung.
import json
import os

import pcbnew
from PIL import Image, ImageDraw, ImageFont

ORDNER = os.path.dirname(os.path.abspath(__file__))
PLATINE = os.path.join(ORDNER, "..", "Einstrahlungssensor-Platine")
ZIEL = os.path.join(ORDNER, "Live-Ansicht")
PX_MM = 40          # Auflösung der gezeichneten Texturen
ANTENNE_MM = 3.8    # Länge des Antennenbereichs am Modulende ohne Abschirmblech

brett = pcbnew.LoadBoard(os.path.join(PLATINE, "einstrahlungssensor.kicad_pcb"))
rand = brett.GetBoardEdgesBoundingBox()
daten = {"platine": [pcbnew.ToMM(v) for v in (rand.GetLeft(), rand.GetTop(), rand.GetRight(), rand.GetBottom())],
         "teile": {}}
for fp in brett.GetFootprints():
    ref = fp.GetReference()
    if ref not in ("U3", "J1", "J2", "J3"):
        continue
    xs, ys = [], []
    for it in fp.GraphicalItems():
        if it.GetLayerName() == "F.Fab":
            r = it.GetBoundingBox()
            xs += [r.GetLeft(), r.GetRight()]
            ys += [r.GetTop(), r.GetBottom()]
    daten["teile"][ref] = {
        "footprint": fp.GetFPIDAsString(),
        "fab": [pcbnew.ToMM(v) for v in (min(xs), min(ys), max(xs), max(ys))],
        "pads": [[pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)] for p in fp.Pads()],
    }
daten["antenne_mm"] = ANTENNE_MM
with open(os.path.join(ZIEL, "platine.json"), "w", encoding="utf-8") as f:
    json.dump(daten, f, indent=1)

# Platinenoberseite: Rendering auf den Umriss zuschneiden (Alphakanal = Platine)
bild = Image.open(os.path.join(PLATINE, "Bilder", "oben.png"))
umriss = bild.split()[3].point(lambda v: 255 if v > 200 else 0).getbbox()
bild.crop(umriss).convert("RGB").save(os.path.join(ZIEL, "textur-platine.png"))

# MDBT42Q: Abschirmblech mit Aufdruck, Antennenbereich mit Leiterbahnantenne
fu = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
fn = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
modul = daten["teile"]["U3"]["fab"]
b_mm, l_mm = modul[2] - modul[0], modul[3] - modul[1]
w, h = int(b_mm * PX_MM), int((l_mm - ANTENNE_MM) * PX_MM)
schirm = Image.new("RGB", (w, h), (196, 199, 202))
z = ImageDraw.Draw(schirm)
for y in range(0, h, 3):                       # leichter Bürstenschliff
    t = 190 + (y * 7) % 13
    z.line([(0, y), (w, y)], fill=(t, t + 3, t + 6))
z.rectangle([2, 2, w - 3, h - 3], outline=(150, 152, 156), width=3)
z.text((w / 2, h * 0.34), "Raytac", font=ImageFont.truetype(fu, 52), fill=(60, 62, 66), anchor="mm")
z.text((w / 2, h * 0.52), "MDBT42Q", font=ImageFont.truetype(fu, 58), fill=(40, 42, 46), anchor="mm")
z.text((w / 2, h * 0.68), "nRF52832", font=ImageFont.truetype(fn, 38), fill=(70, 72, 76), anchor="mm")
schirm.save(os.path.join(ZIEL, "textur-modul-schirm.png"))

ha = int(ANTENNE_MM * PX_MM)
antenne = Image.new("RGB", (w, ha), (24, 78, 52))
z = ImageDraw.Draw(antenne)
gold, s = (205, 160, 70), 12                   # Mäander der Leiterbahnantenne
x, y0, y1 = 30, 25, ha - 30
punkte = []
while x < w - 40:
    punkte += [(x, y1), (x, y0), (x + 2 * s, y0), (x + 2 * s, y1)]
    x += 4 * s
z.line(punkte, fill=gold, width=7, joint="curve")
z.line([(w - 40, y1), (w - 40, ha)], fill=gold, width=7)
antenne.save(os.path.join(ZIEL, "textur-modul-antenne.png"))

print(json.dumps(daten["teile"], indent=1))
print("Texturen:", umriss, (w, h), (w, ha))
