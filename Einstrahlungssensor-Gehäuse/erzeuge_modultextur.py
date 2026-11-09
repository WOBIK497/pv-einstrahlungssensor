#!/usr/bin/env python3
"""Eigene Modultextur: schwarzes ETFE mit genarbter Oberfläche (versetzte Noppen,
Licht von links oben). Rein prozedural, kein Fremdbild.

Aufruf: python3 erzeuge_modultextur.py Live-Ansicht/textur-modul.png [GROESSE]
"""
import math
import random
import sys
from PIL import Image, ImageFilter

ziel = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 900
P = 20.0                       # Noppenabstand in Pixeln (900 px ≙ 70 mm → ≈ 1,6 mm)
R = 0.56 * P                   # Noppenradius, überlappt leicht → Waben-Narbung
BASIS = (40, 42, 52)
HELL = (96, 99, 114)
DUNKEL = (16, 17, 22)
L = (-0.55, -0.62, 0.56)       # Lichtrichtung (x rechts, y unten, z zum Betrachter)
ln = math.sqrt(sum(c * c for c in L))
L = tuple(c / ln for c in L)

random.seed(42)
img = Image.new("RGB", (N, N))
px = img.load()
zeilen_h = P * math.sqrt(3) / 2
# leichte Höhenschwankung je Noppe, damit es nicht wie ein Raster aussieht
hoehe = {}


def noppe(i, j):
    k = (i, j)
    if k not in hoehe:
        hoehe[k] = (0.75 + 0.5 * random.random(), random.uniform(-0.12, 0.12), random.uniform(-0.12, 0.12))
    return hoehe[k]


for y in range(N):
    j0 = int(y / zeilen_h)
    for x in range(N):
        best = None
        for j in (j0 - 1, j0, j0 + 1):
            versatz = (P / 2) if j % 2 else 0.0
            i0 = int((x - versatz) / P)
            for i in (i0 - 1, i0, i0 + 1):
                h, ox, oy = noppe(i, j)
                cx = i * P + versatz + ox * P
                cy = j * zeilen_h + oy * P
                dx, dy = (x - cx) / R, (y - cy) / R
                d2 = dx * dx + dy * dy
                if d2 < 1.0 and (best is None or d2 < best[0]):
                    best = (d2, dx, dy, h)
        if best is None:
            nx, ny, nz = 0.0, 0.0, 1.0
            tal = 1.0
        else:
            d2, dx, dy, h = best
            nz = math.sqrt(1.0 - d2)
            # flache Kuppe: Neigung mit Höhenfaktor skalieren
            nx, ny = dx * h * 0.9, dy * h * 0.9
            n = math.sqrt(nx * nx + ny * ny + nz * nz)
            nx, ny, nz = nx / n, ny / n, nz / n
            tal = 0.0
        s = nx * L[0] + ny * L[1] + nz * L[2] - L[2]      # 0 = flach, + = Licht, − = Schatten
        s += random.uniform(-0.03, 0.03)
        if tal:
            s -= 0.10
        if s >= 0:
            t = min(1.0, s * 2.2)
            c = tuple(round(b + (hh - b) * t) for b, hh in zip(BASIS, HELL))
        else:
            t = min(1.0, -s * 2.0)
            c = tuple(round(b + (d - b) * t) for b, d in zip(BASIS, DUNKEL))
        px[x, y] = c

img = img.filter(ImageFilter.GaussianBlur(0.6))
img.save(ziel)
print("gespeichert:", ziel, img.size)
