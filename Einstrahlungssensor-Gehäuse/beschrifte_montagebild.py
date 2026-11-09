#!/usr/bin/env python3
"""Beschriftet Bilder/montage-hinten.jpg: Pfeil auf die M6-Schraube im Montageloch
des Rahmenflanschs. Ergebnis: Bilder/montage-hinten-beschriftet.jpg (Original bleibt).

Aufruf: python3 beschrifte_montagebild.py
"""
import math
import os
from PIL import Image, ImageDraw, ImageFont

ORDNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Bilder")
QUELLE = os.path.join(ORDNER, "montage-hinten.jpg")
ZIEL = os.path.join(ORDNER, "montage-hinten-beschriftet.jpg")
SCHRAUBE = (693, 428)          # Schraubenkopf im Bild (Pixel, 1340 × 900)
TEXT_POS = (290, 600)          # linke obere Ecke der Beschriftung (auf der Paneelrückseite)
TEXT = "M6-Schraube durch das\nMontageloch im Rahmenflansch"
FARBE = (255, 255, 255)

bild = Image.open(QUELLE).convert("RGB")
zeichnung = ImageDraw.Draw(bild)
schrift = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)

# Pfeil von der Beschriftung zur Schraube
start = (SCHRAUBE[0] - 30, TEXT_POS[1] - 10)
ende = (SCHRAUBE[0] - 4, SCHRAUBE[1] + 20)
zeichnung.line([start, ende], fill=FARBE, width=4)
w = math.atan2(ende[1] - start[1], ende[0] - start[0])
spitze = [ende,
          (ende[0] - 22 * math.cos(w - 0.4), ende[1] - 22 * math.sin(w - 0.4)),
          (ende[0] - 22 * math.cos(w + 0.4), ende[1] - 22 * math.sin(w + 0.4))]
zeichnung.polygon(spitze, fill=FARBE)
zeichnung.multiline_text(TEXT_POS, TEXT, font=schrift, fill=FARBE, spacing=8)

bild.save(ZIEL, quality=90)
print("gespeichert:", ZIEL)
