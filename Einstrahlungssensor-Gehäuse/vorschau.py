#!/usr/bin/env python3
# Einfache Vorschau der STL-Dateien (Maleralgorithmus mit Pillow), ohne OpenGL.
import math
import os
import struct
import sys
from PIL import Image, ImageDraw

ORDNER = os.path.dirname(os.path.abspath(__file__))


def lies_stl(pfad):
    daten = open(pfad, "rb").read()
    if daten[:5] == b"solid" and b"facet" in daten[:300]:
        dreiecke, pkt = [], []
        for zeile in daten.decode().splitlines():
            w = zeile.split()
            if w and w[0] == "vertex":
                pkt.append(tuple(map(float, w[1:4])))
                if len(pkt) == 3:
                    dreiecke.append(pkt)
                    pkt = []
        return dreiecke
    n = struct.unpack_from("<I", daten, 80)[0]
    return [[struct.unpack_from("<3f", daten, 84 + i * 50 + 12 + j * 12) for j in range(3)] for i in range(n)]


def teile_auf(d, maxlaenge=4.0):
    """Lange Dreiecke halbieren, damit die Tiefensortierung stimmt."""
    kanten = [(i, (i + 1) % 3) for i in range(3)]
    laengen = [math.dist(d[i], d[j]) for i, j in kanten]
    k = max(range(3), key=lambda n: laengen[n])
    if laengen[k] <= maxlaenge:
        return [d]
    i, j = kanten[k]
    o = 3 - i - j
    m = tuple((d[i][n] + d[j][n]) / 2 for n in range(3))
    return teile_auf([d[i], m, d[o]], maxlaenge) + teile_auf([m, d[j], d[o]], maxlaenge)


def zeichne(teile, datei, az=-35, el=35, breite=1400, hoehe=900):
    teile = [([t for d in dr for t in teile_auf(d)], v, f) for dr, v, f in teile]
    a, e = math.radians(az), math.radians(el)
    def drehe(p):
        x, y, z = p
        x1 = x * math.cos(a) - y * math.sin(a)
        y1 = x * math.sin(a) + y * math.cos(a)
        return (x1, y1 * math.sin(e) + z * math.cos(e), y1 * math.cos(e) - z * math.sin(e))
    licht = (0.35, 0.55, -0.75)
    flaechen = []
    for dreiecke, versatz, farbe in teile:
        for d in dreiecke:
            p = [drehe((q[0] + versatz[0], q[1] + versatz[1], q[2] + versatz[2])) for q in d]
            u = [p[1][i] - p[0][i] for i in range(3)]
            v = [p[2][i] - p[0][i] for i in range(3)]
            nx, ny, nz = u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]
            l = math.sqrt(nx * nx + ny * ny + nz * nz) or 1
            hell = abs(nx * licht[0] + ny * licht[1] + nz * licht[2]) / l
            tiefe = sum(q[2] for q in p) / 3
            flaechen.append((tiefe, p, farbe, 0.35 + 0.65 * hell))
    xs = [q[0] for f in flaechen for q in f[1]]
    ys = [q[1] for f in flaechen for q in f[1]]
    s = min((breite - 60) / (max(xs) - min(xs)), (hoehe - 60) / (max(ys) - min(ys)))
    ox = breite / 2 - s * (max(xs) + min(xs)) / 2
    oy = hoehe / 2 + s * (max(ys) + min(ys)) / 2
    bild = Image.new("RGB", (breite, hoehe), (250, 250, 248))
    zeich = ImageDraw.Draw(bild)
    for _, p, farbe, h in sorted(flaechen, key=lambda f: -f[0]):
        c = tuple(int(k * h) for k in farbe)
        zeich.polygon([(ox + s * q[0], oy - s * q[1]) for q in p], fill=c, outline=c)
    bild.save(datei, quality=88)


if __name__ == "__main__":
    os.makedirs(os.path.join(ORDNER, "Bilder"), exist_ok=True)
    unten = lies_stl(os.path.join(ORDNER, "gehaeuse-unterteil.stl"))
    deckel = lies_stl(os.path.join(ORDNER, "gehaeuse-deckel.stl"))
    inhalt = lies_stl(os.path.join(ORDNER, "pruefung-inhalt.stl"))
    grau, gruen, blau = (200, 200, 205), (60, 150, 90), (120, 140, 220)
    b = os.path.join(ORDNER, "Bilder")
    zeichne([(unten, (0, 0, 0), grau), (inhalt, (0, 0, 0), gruen)], os.path.join(b, "unterteil.jpg"), el=50)
    zeichne([(deckel, (0, 0, 0), blau)], os.path.join(b, "deckel.jpg"), el=55)
    zeichne([(unten, (0, 0, 0), grau), (inhalt, (0, 0, 0), gruen), (deckel, (0, 0, 45), blau)],
            os.path.join(b, "explosion.jpg"), el=28)
    zeichne([(unten, (0, 0, 0), grau)], os.path.join(b, "boden.jpg"), el=-50)
    print("Bilder in", b)
