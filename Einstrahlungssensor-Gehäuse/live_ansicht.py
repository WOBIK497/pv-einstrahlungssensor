# FreeCAD-Makro: Live-Ansicht des Gehäuses.
#
# Start:  freecad live_ansicht.py   (oder in FreeCAD: Makro → Makros … → ausführen)
#
# Das Makro beobachtet erzeuge_gehaeuse.py. Sobald die Datei gespeichert wurde
# und RUHE Sekunden unverändert bleibt, baut es Unterteil, Deckel, Solarmodule
# und Inhalt im Dokument „Gehaeuse_Live“ neu auf – die Kamera bleibt, wo sie
# ist. Fehler erscheinen nur als eine Zeile in der Ausgabe-Ansicht (keine
# Einblendung über dem Modell), der volle Text steht in Live-Ansicht/status.txt;
# das alte Modell bleibt stehen.
#
# Änderungen am Skript laufen über Live-Ansicht/arbeitskopie.py und
# live_uebernehmen.sh (Probelauf, dann Austausch in einem Schritt).
#
# Zusätzlich führt es Live-Ansicht/befehl.py einmal aus, falls vorhanden
# (Kamera, Sichtbarkeit, Bildschirmfoto), und schreibt das Ergebnis nach
# Live-Ansicht/antwort.txt. Nach jedem Neubau liegt ein Bild in
# Live-Ansicht/ansicht.png, damit Claude dasselbe sieht.
import io
import os
import sys
import time
import traceback
import contextlib

import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector as V
from PySide import QtCore

try:
    ORDNER = os.path.dirname(os.path.abspath(__file__))
except NameError:
    ORDNER = os.path.expanduser("~/Claude.Code/Projekte/PV-Einstrahlungssensor Eigenbau/Einstrahlungssensor-Gehäuse")
SKRIPT = os.path.join(ORDNER, "erzeuge_gehaeuse.py")
LIVE = os.path.join(ORDNER, "Live-Ansicht")
BEFEHL = os.path.join(LIVE, "befehl.py")
ANTWORT = os.path.join(LIVE, "antwort.txt")
STATUS = os.path.join(LIVE, "status.txt")
BILD = os.path.join(LIVE, "ansicht.png")
DOKNAME = "Gehaeuse_Live"
os.makedirs(LIVE, exist_ok=True)

# Darstellung – per befehl.py änderbar, danach neu_bauen() aufrufen
EXPLOSION = 95.0       # Deckel über dem Unterteil: in der ISO-Ansicht berühren sich Deckel-
                        # vorderkante und Gehäusehinterkante bei 74,5 – etwas Luft; 0 = geschlossen
RUHE = 2.0              # Sekunden ohne Dateiänderung vor dem Neubau
FARBEN = {"Unterteil": (0.80, 0.80, 0.78), "Deckel": (0.80, 0.80, 0.78),
          "Solarmodule": (0.07, 0.07, 0.08), "Inhalt": (0.15, 0.55, 0.25),
          "Kleber": (0.04, 0.04, 0.04), "Dichtring": (0.06, 0.06, 0.06),
          "Kondensator": (0.10, 0.28, 0.62), "Kondensatordraehte": (0.75, 0.75, 0.75),
          "Platine": (0.17, 0.29, 0.22), "Funkmodul": (0.12, 0.30, 0.20),
          "Funkmodul_Schirm": (0.78, 0.79, 0.80), "Buchsen": (1.0, 1.0, 1.0),
          "Stecker": (0.96, 0.94, 0.86), "Druckausgleich": (0.30, 0.32, 0.34),
          "Gegenmutter": (0.30, 0.32, 0.34), "Deckelschrauben": (0.72, 0.74, 0.77),
          "Platinenschrauben": (0.80, 0.64, 0.30), "Druckausgleich_Membran": (0.96, 0.96, 0.95), "Litze_rot": (0.80, 0.08, 0.06),
          "Litze_schwarz": (0.08, 0.08, 0.08), "Schrumpfschlauch": (0.15, 0.15, 0.15),
          "Buchsen_Kontakte": (0.85, 0.70, 0.30), "Gewindeeinsaetze": (0.80, 0.62, 0.26),
          "Druckausgleich_Dichtring": (0.06, 0.06, 0.06)}
TRANSPARENZ = {"Deckel": 0, "Solarmodule": 0}

# Vorherige Instanz (erneuter Makrostart) sauber beenden
alt = getattr(App, "_gehaeuse_live", None)
if alt is not None:
    try:
        alt["timer"].stop()
    except Exception:
        pass

zustand = {"mtime": None, "werte": {}, "erstmals": True, "baut": False}


def melde(text, fehler=False):
    """Eine Zeile in die Ausgabe-Ansicht. Bewusst nie PrintError/PrintWarning:
    die erzeugen Einblendungen, die das Modell verdecken."""
    zeile = time.strftime("%H:%M:%S ") + text
    kurz = zeile.strip().splitlines()[-1] if fehler else zeile
    if fehler:
        kurz = time.strftime("%H:%M:%S ") + "Fehler: " + kurz.strip() + " (Details in status.txt)"
    App.Console.PrintMessage("[Live] " + kurz + "\n")
    return zeile


def dokument():
    doc = App.listDocuments().get(DOKNAME)
    if doc is None:
        doc = App.newDocument(DOKNAME)
    return doc


def setze(doc, name, form, platz=None):
    obj = doc.getObject(name)
    if obj is None:
        obj = doc.addObject("Part::Feature", name)
        vo = obj.ViewObject
        if vo is not None:
            vo.ShapeColor = FARBEN.get(name, (0.7, 0.7, 0.7))
            vo.Transparency = TRANSPARENZ.get(name, 0)
    elif name in FARBEN and obj.ViewObject is not None:
        # Farbänderungen im Makro auch auf bestehende Objekte übertragen
        if tuple(round(c, 3) for c in obj.ViewObject.ShapeColor[:3]) != tuple(round(c, 3) for c in FARBEN[name]):
            obj.ViewObject.ShapeColor = FARBEN[name]
    obj.Shape = form
    obj.Placement = platz or App.Placement()
    return obj


def textur(obj, datei, breite, hoehe):
    """Bild als Textur auf ein flaches Objekt legen, das in lokalen Koordinaten
    von (0, 0) bis (breite, hoehe) reicht; Bild-oben = +y."""
    from pivy import coin
    from PySide import QtGui
    obj.ViewObject.ShapeColor = (1.0, 1.0, 1.0)
    root = obj.ViewObject.RootNode
    for i in reversed(range(root.getNumChildren())):
        if root.getChild(i).getName().getString().startswith("LiveTextur"):
            root.removeChild(i)
    img = QtGui.QImage(datei).convertToFormat(QtGui.QImage.Format_RGBA8888).mirrored(False, True)
    w, h = img.width(), img.height()
    tex = coin.SoTexture2()
    tex.setName("LiveTexturBild")
    tex.image.setValue(coin.SbVec2s(w, h), 4, bytes(img.constBits())[:w * h * 4])
    tex.model = coin.SoTexture2.DECAL
    ebene = coin.SoTextureCoordinatePlane()
    ebene.setName("LiveTexturEbene")
    ebene.directionS.setValue(1.0 / breite, 0, 0)
    ebene.directionT.setValue(0, 1.0 / hoehe, 0)
    root.insertChild(tex, 0)
    root.insertChild(ebene, 0)


def bildflaeche(doc, name, platz, b, h, datei, form=None):
    """Flaches Rechteck b × h (lokal ab 0,0) mit Bild aus Live-Ansicht/<datei>;
    mit form eine beliebige flache Form innerhalb dieses Rechtecks."""
    obj = setze(doc, name, form or Part.makePlane(b, h), platz)
    if zustand.setdefault("texturen", {}).get(name) != (datei, b, h):
        textur(obj, os.path.join(LIVE, datei), b, h)
        zustand["texturen"][name] = (datei, b, h)
    return obj


def senkschraube_vorlage(laenge, dk, d, k, sechskant):
    """Eine Senkschraube M3 im Ursprung, mit echtem Gewinde (Steigung 0,5 mm als
    Schraubenlinie). Wird zwischengespeichert, weil das Gewinde ein paar Sekunden braucht."""
    schluessel = ("senkschraube", laenge)
    if schluessel in zustand.setdefault("vorlagen", {}):
        return zustand["vorlagen"][schluessel]
    steigung, r_kern, tiefe = 0.5, d / 2 - 0.31, 0.29
    kopf = Part.makeCone(dk / 2, d / 2, k, V(0, 0, 0))
    kopf = kopf.cut(sechskant(2.0, 1.3, 0, 0, -0.01))         # Innensechskant SW 2
    kern = Part.makeCylinder(r_kern, laenge - k, V(0, 0, k))
    schraube = kopf.fuse(kern)
    try:
        h = laenge - k - 0.6
        wendel = Part.makeHelix(steigung, h, r_kern - 0.02)
        wendel.translate(V(0, 0, k + 0.1))
        p0 = wendel.Vertexes[0].Point
        # dreieckiges Gewindeprofil (60°) radial nach außen, in der Ebene durch die Achse
        rad = V(p0.x, p0.y, 0)
        rad.normalize()
        b = steigung * 0.42
        profil = Part.makePolygon([p0 + V(0, 0, -b), p0 + rad * (tiefe + 0.02), p0 + V(0, 0, b), p0 + V(0, 0, -b)])
        gang = Part.Wire(wendel).makePipeShell([profil], True, True)
        schraube = Part.makeCompound([schraube, gang])
    except Exception:
        melde("Gewinde nicht darstellbar, nehme Rillen: " + traceback.format_exc(limit=1), True)
        for i in range(int((laenge - k) / steigung) - 1):
            schraube = schraube.fuse(Part.makeTorus(r_kern, tiefe * 0.8, V(0, 0, k + 0.5 + i * steigung)))
    zustand["vorlagen"][schluessel] = schraube
    return schraube


def schrauben_zeigen(doc, g):
    """Deckelschrauben (Senkkopf ISO 10642 mit Innensechskant, von unten in den Domen)
    und Platinenschrauben (Linsenkopf ISO 7045 mit Kreuzschlitz), Edelstahl."""
    if "SCHRAUB_MITTEN" not in g or "SCHRAUBE_L" not in g:
        return
    dk, d = 6.72, 3.0
    k = (dk - d) / 2                                          # 90°-Senkkopf
    vorlage = senkschraube_vorlage(g["SCHRAUBE_L"], dk, d, k, g["sechskant"])
    teile = []
    for x, y in g["SCHRAUB_MITTEN"]:
        s = vorlage.copy()
        s.translate(V(x, y, g.get("SCHRAUBE_Z", 0.0)))   # Kopf ggf. tiefer im Boden versenkt
        teile.append(s)
    setze(doc, "Deckelschrauben", Part.makeCompound(teile))

    if "PLATINE_LOECHER" in g and "PLATINE_SCHRAUBE_L" in g:
        z_pl = g["BODEN"] + g["ABSTAND_H"] + 1.6              # Platinenoberseite
        px0, py0 = -g["PLATINE"][0] / 2, g["PLATINE"][1] / 2
        linse = None
        for lx, ly in g["PLATINE_LOECHER"]:
            x, y = px0 + lx, py0 - ly
            kopf = Part.makeCylinder(2.75, 2.4, V(x, y, z_pl))
            oben = [e for e in kopf.Edges if abs(e.BoundBox.ZMin - (z_pl + 2.4)) < 1e-6]
            kopf = kopf.makeFillet(1.0, oben)
            for w in (0, 90):                                 # Kreuzschlitz
                schlitz = Part.makeBox(3.2, 0.7, 1.4, V(-1.6, -0.35, z_pl + 1.05))
                schlitz.rotate(V(0, 0, z_pl), V(0, 0, 1), w)
                schlitz.translate(V(x, y, 0))
                kopf = kopf.cut(schlitz)
            schaft = Part.makeCylinder(d / 2 - 0.05, g["PLATINE_SCHRAUBE_L"], V(x, y, z_pl - g["PLATINE_SCHRAUBE_L"]))
            s = kopf.fuse(schaft)
            linse = s if linse is None else linse.fuse(s)
        setze(doc, "Platinenschrauben", linse)


def einsaetze_zeigen(doc, g, platz):
    """Gewindeeinsätze M3 × 5,7 aus Messing (Bauart Ruthex) von unten im Deckel:
    zwei gerändelte Bänder mit einer Nut dazwischen, Bohrung mit Innengewinde M3
    (Steigung 0,5 mm). Das Gewinde ist wie bei den Schrauben eine Schraubenlinie mit
    60°-Profil: hier ein Steg, der von der Bohrungswand (Nenn-Ø 3,0) nach innen bis
    zum Kern-Ø 2,46 ragt – ohne Boolesche Operation, damit es schnell bleibt."""
    import math
    if "SCHRAUB_MITTEN" not in g:
        return
    laenge, r_aussen, r_kern, r_bohr = 5.7, 2.3, 2.05, 1.5
    schluessel = ("einsatz", laenge, "gewinde")
    vorlage = zustand.setdefault("vorlagen", {}).get(schluessel)
    if vorlage is None:
        zaehne = 18
        pkt = []
        for i in range(2 * zaehne):
            r = r_aussen if i % 2 == 0 else r_kern
            w = math.pi * i / zaehne
            pkt.append(V(r * math.cos(w), r * math.sin(w), 0))
        stern = Part.Face(Part.makePolygon(pkt + [pkt[0]]))
        vorlage = Part.makeCylinder(r_kern, laenge)
        for z0, h in ((0.5, 1.9), (3.3, 1.9)):                # Rändelbänder, Nut dazwischen
            band = stern.extrude(V(0, 0, h))
            band.translate(V(0, 0, z0))
            vorlage = vorlage.fuse(band)
        vorlage = vorlage.cut(Part.makeCylinder(r_bohr, laenge + 2, V(0, 0, -1)))
        vorlage = vorlage.cut(Part.makeCone(r_bohr + 0.3, r_bohr, 0.3, V(0, 0, -0.001)))   # Fase am Eingang
        try:
            steigung, tiefe = 0.5, 0.27
            h = laenge - 0.6
            wendel = Part.makeHelix(steigung, h, r_bohr + 0.02)
            wendel.translate(V(0, 0, 0.3))
            p0 = wendel.Vertexes[0].Point
            rad = V(p0.x, p0.y, 0)
            rad.normalize()
            b = steigung * 0.42
            # Dreieck in der Ebene durch die Achse: Basis in der Wand, Spitze nach innen
            profil = Part.makePolygon([p0 + V(0, 0, -b), p0 - rad * (tiefe + 0.02), p0 + V(0, 0, b), p0 + V(0, 0, -b)])
            gang = Part.Wire(wendel).makePipeShell([profil], True, True)
            vorlage = Part.makeCompound([vorlage, gang])
        except Exception:
            melde("Innengewinde nicht darstellbar: " + traceback.format_exc(limit=1), True)
        zustand["vorlagen"][schluessel] = vorlage
    teile = []
    for x, y in g["SCHRAUB_MITTEN"]:
        e = vorlage.copy()
        e.translate(V(x, y, 0))
        teile.append(e)
    setze(doc, "Gewindeeinsaetze", Part.makeCompound(teile), platz)


def druckausgleich_zeigen(doc, g):
    """Druckausgleichselement wie das Jacob JDAE12 PA/sw: Sechskantkopf mit Fase an
    der Kappe, Lüftungsschlitze auf allen Flächen, Gewinde mit Gängen, Gegenmutter.
    Maße aus den DAE_-Parametern des Gehäuseskripts. Die Kappe zeigt nach außen (unten)."""
    import math
    if "DAE_X" not in g or "sechskant" not in g:
        return False
    x, y = g["DAE_X"], g["DAE_Y"]
    sw, hk, lg = g["DAE_SW"], g["DAE_KOPF_H"], g["DAE_GEWINDE_L"]
    z_kappe, z_kopf = g["DAE_TASCHE_T"] - hk, g["DAE_TASCHE_T"]
    ru = sw / 2 / math.cos(math.radians(30))                    # Umkreisradius
    kopf = g["sechskant"](sw, hk, x, y, z_kappe)
    kopf = kopf.common(Part.makeCone(sw / 2 + 0.3, sw / 2 + 0.3 + hk, hk, V(x, y, z_kappe)))   # 45°-Fase
    zs, hs, wb, tief = z_kappe + 0.38 * hk, 0.16 * hk, 0.55 * ru, 1.6
    for i in range(6):                                          # Schlitz mitten auf jeder Fläche
        s = Part.makeBox(tief + 0.5, wb, hs, V(sw / 2 - tief, -wb / 2, 0))
        s.rotate(V(0, 0, 0), V(0, 0, 1), 30 + 60 * i)
        s.translate(V(x, y, zs))
        kopf = kopf.cut(s)
    gewinde = Part.makeCylinder(6.0, lg, V(x, y, z_kopf))
    for k in range(int(lg / 1.5)):
        gewinde = gewinde.cut(Part.makeTorus(6.0, 0.42, V(x, y, z_kopf + 0.75 + 1.5 * k)))
    # Luftweg: Bohrung durchs Gewinde bis zur Membran, die über den Schlitzen liegt;
    # außen geht die Luft durch die Schlitze unter der Kappe heraus
    bohr_r = 3.25
    z_membran = zs + hs + 0.6
    koerper = kopf.fuse(gewinde).cut(Part.makeCylinder(bohr_r, z_kopf + lg + 1 - z_membran, V(x, y, z_membran)))
    # Dichtring unter dem Kopf: liegt in einer Nut der Kopfauflage um das Gewinde und
    # dichtet gegen den Taschengrund (Maße angenommen: 1,5 mm Schnur, innen am Gewinde)
    ring_d = 1.5
    ring_r = 6.0 + ring_d / 2
    koerper = koerper.cut(Part.makeCylinder(6.0 + ring_d + 0.1, ring_d * 0.8, V(x, y, z_kopf - ring_d * 0.8 + 0.01))
                          .cut(Part.makeCylinder(6.0, ring_d, V(x, y, z_kopf - ring_d))))
    setze(doc, "Druckausgleich", koerper)
    setze(doc, "Druckausgleich_Dichtring", Part.makeTorus(ring_r, ring_d / 2, V(x, y, z_kopf - ring_d / 2)))
    setze(doc, "Druckausgleich_Membran", Part.makeCylinder(bohr_r, 0.15, V(x, y, z_membran)))
    # Gegenmutter auf dem Dom, beidseitig gefast
    zm, mh, msw = g["DAE_DOM_H"], g["MUTTER_H"], g["MUTTER_SW"]
    m = g["sechskant"](msw, mh, x, y, zm)
    m = m.common(Part.makeCone(msw / 2 + 0.3, msw / 2 + 0.3 + mh, mh, V(x, y, zm)))
    m = m.common(Part.makeCone(msw / 2 + 0.3 + mh, msw / 2 + 0.3, mh, V(x, y, zm)))
    m = m.cut(Part.makeCylinder(5.9, mh + 1, V(x, y, zm - 0.5)))
    setze(doc, "Gegenmutter", m)
    # Aufdruck auf der Kappe (Bild gespiegelt, weil von unten betrachtet)
    pkt = [V(ru + ru * math.cos(math.radians(60 * i)), ru + ru * math.sin(math.radians(60 * i)), 0) for i in range(6)]
    flaeche = Part.Face(Part.makePolygon(pkt + [pkt[0]]))
    bildflaeche(doc, "Druckausgleich_Bild", App.Placement(V(x - ru, y - ru, z_kappe - 0.02), App.Rotation()),
                2 * ru, 2 * ru, "textur-dae.png", flaeche)
    return True


def platine_zeigen(doc, g):
    """Platine mit dem KiCad-Bild als Oberfläche, Funkmodul MDBT42Q und ZH-Buchsen.
    Daten aus platine_ansicht_daten.py (Live-Ansicht/platine.json + Texturen)."""
    import json
    pfad = os.path.join(LIVE, "platine.json")
    if not os.path.exists(pfad):
        return False
    with open(pfad, encoding="utf-8") as f:
        d = json.load(f)
    l, o, r, u = d["platine"]                     # KiCad-Koordinaten, y nach unten
    kx, ky = (l + r) / 2, (o + u) / 2
    z_pl = g["BODEN"] + g["ABSTAND_H"]
    z_oben = z_pl + 1.6

    def gh(x0, y0, x1, y1):                       # KiCad-Rechteck → Gehäuse (x, y, Breite, Höhe)
        return x0 - kx, ky - y1, x1 - x0, y1 - y0

    def flach(name, x, y, b, h, z, datei):
        bildflaeche(doc, name, App.Placement(V(x, y, z), App.Rotation()), b, h, datei)

    x, y, b, h = gh(l, o, r, u)
    brett = Part.makeBox(b, h, 1.6, V(x, y, z_pl))
    for lx, ly in g.get("PLATINE_LOECHER", ()):                 # Befestigungslöcher 3,2 mm
        brett = brett.cut(Part.makeCylinder(1.6, 2.0, V(-g["PLATINE"][0] / 2 + lx, g["PLATINE"][1] / 2 - ly, z_pl - 0.2)))
    setze(doc, "Platine", brett)
    flach("Platinenbild", x, y, b, h, z_oben + 0.01, "textur-platine.png")

    # Funkmodul: Trägerplatine 0,8 mm, Abschirmblech 1,4 mm, Antennenende ohne Blech
    x, y, b, h = gh(*d["teile"]["U3"]["fab"])
    ant = d["antenne_mm"]
    setze(doc, "Funkmodul", Part.makeBox(b, h, 0.8, V(x, y, z_oben)))
    setze(doc, "Funkmodul_Schirm", Part.makeBox(b - 0.3, h - ant - 0.15, 1.4, V(x + 0.15, y + 0.15, z_oben + 0.8)))
    flach("Funkmodul_Aufdruck", x + 0.15, y + 0.15, b - 0.3, h - ant - 0.15, z_oben + 2.21, "textur-modul-schirm.png")
    flach("Funkmodul_Antenne", x, y + h - ant, b, ant, z_oben + 0.81, "textur-modul-antenne.png")

    # ZH-Buchsen (JST B2B-ZR, stehend): Gehäuse 6 mm hoch, oben offen, Kontaktstifte
    buchsen, stifte = None, None
    for ref in ("J1", "J2", "J3"):
        if ref not in d["teile"] or "ZH" not in d["teile"][ref]["footprint"]:
            continue
        x, y, b, h = gh(*d["teile"][ref]["fab"])
        k = Part.makeBox(b, h, 6.0, V(x, y, z_oben))
        k = k.cut(Part.makeBox(b - 1.2, h - 1.2, 5.2, V(x + 0.6, y + 0.6, z_oben + 0.8)))
        buchsen = k if buchsen is None else buchsen.fuse(k)
        for px, py in d["teile"][ref]["pads"]:
            s = Part.makeBox(0.64, 0.64, 4.6, V(px - kx - 0.32, ky - py - 0.32, z_oben))
            stifte = s if stifte is None else stifte.fuse(s)
    setze(doc, "Buchsen", buchsen)
    setze(doc, "Buchsen_Kontakte", stifte)

    # ZH-Stecker (JST ZHR-2) in den Buchsen, oben 2 mm überstehend, mit Kabeln:
    # Pin 1 (Plus) rot, Pin 2 schwarz. Die Adern laufen als Paar direkt aneinander
    # in weichen Bögen und spreizen erst kurz vor dem Anschluss auseinander.
    # J1/J2 gehen durch die Deckelfenster zu den Modulen, J3 zum Superkondensator.
    LITZE_R = 0.4                                 # 28 AWG mit Isolierung ≈ Ø 0,8 mm
    ABST = LITZE_R * 1.02                         # halber Mittenabstand im Paar
    ZIEL_MODUL = {"J2": 0, "J1": 1}               # PV-M → linkes Modul, PV-V → rechtes
    z_st = z_oben + 8.0                           # Oberkante Stecker
    OBEN = V(0, 0, 1)

    def kurve(punkte, t0=None, t1=None):
        c = Part.BSplineCurve()
        if t0 is not None and t1 is not None:
            c.interpolate(Points=punkte, InitialTangent=t0, FinalTangent=t1)
        else:
            c.interpolate(Points=punkte)
        return c

    def ader(punkte, t0, t1):
        """Ader als Rohr entlang einer glatten Kurve durch die Punkte."""
        c = kurve(punkte, t0, t1)
        try:
            return Part.makeTube(Part.Edge(c), LITZE_R)   # Rohrfläche, robust auch in engen Bögen
        except Exception:
            p0 = c.value(c.FirstParameter)
            kreis = Part.Wire(Part.Edge(Part.Circle(p0, c.tangent(c.FirstParameter)[0], LITZE_R)))
            return Part.Wire(Part.Edge(c)).makePipeShell([kreis], False, False)

    def paar_seiten(c, s0, ziel=None):
        """Mittellinie abtasten; Querrichtung parallel mitführen (verdrehungsarm).
        Mit ziel liegt das Paar am Ende quer zu dieser Richtung nebeneinander; die
        nötige Drehung wird gleichmäßig über die ganze Länge verteilt."""
        import math
        pkt = c.discretize(Distance=1.5)
        seiten, tang, s = [], [], s0
        for p in pkt:
            t = c.tangent(c.parameter(p))[0]
            s = s - t * s.dot(t)
            s.normalize()
            seiten.append(s)
            tang.append(t)
        if ziel is not None:
            t_e, s_e = tang[-1], seiten[-1]
            d = ziel - t_e * ziel.dot(t_e)
            d.normalize()
            if d.dot(s_e) < 0:
                d = d * -1
            phi = math.degrees(math.atan2(t_e.dot(s_e.cross(d)), s_e.dot(d)))
            n = len(pkt) - 1
            seiten = [App.Rotation(t, phi * k / n).multVec(s) for k, (s, t) in enumerate(zip(seiten, tang))]
        return pkt, seiten

    stecker, rot, schwarz, schlauch = None, None, None, None
    for ref in ("J1", "J2", "J3"):
        if ref not in d["teile"] or "ZH" not in d["teile"][ref]["footprint"]:
            continue
        x, y, b, h = gh(*d["teile"][ref]["fab"])
        s = Part.makeBox(b - 1.4, h - 1.4, z_st - (z_oben + 0.8), V(x + 0.7, y + 0.7, z_oben + 0.8))
        stecker = s if stecker is None else stecker.fuse(s)
        pins = [V(px - kx, ky - py, z_st) for px, py in d["teile"][ref]["pads"]]
        mitte = (pins[0] + pins[1]) * 0.5
        achse = pins[0] - mitte
        achse.normalize()
        start = mitte + V(0, 0, 4.0)              # hier liegt das Paar zusammen
        enden = None                              # Endpunkte je Ader (rot, schwarz) samt Tangente
        if ref in ZIEL_MODUL and "MODUL_X" in g:
            # Austritt hinten am Modul über dem Fenster (Lage wie auf dem Produktfoto)
            mx = g["MODUL_X"][ZIEL_MODUL[ref]]
            aus = V(mx - g["PANEL"] / 2 + 0.38 * g["PANEL"], -24.0, 0)
            z_mod = g["HOEHE"] + EXPLOSION + g["DECKEL_D"] - g["TASCHE_TIEFE"] + g.get("KLEBER_D", 0.0)
            hin = aus - V(mitte.x, mitte.y, 0)
            mittel = [start, V(mitte.x, mitte.y, 0) + hin * 0.45 + V(0, 0, z_st + 9.0),
                      aus + V(0, 0, z_st + 16.0), aus + V(0, 0, z_mod)]
            c = kurve(mittel, OBEN, OBEN)
            enden = "modul"
        elif ref == "J3" and "KOND_X" in g:
            kr = g["KOND_ZELLE_D"] / 2
            x_draht = g["KOND_X"] + g["KOND_L"] / 2 - 0.5 - g["KOND_ZELLE_L"] - g["KOND_DRAHT_L"]
            z_draht = g["BODEN"] + kr
            # Paar über die Platine, hinter ihrer rechten Kante absteigen (dort ist frei)
            x_ab = max(x_draht - 9.5, g["PLATINE"][0] / 2 + 2.5)
            mittel = [start, start + V(6.0, 5.0, 1.5), V(x_ab, g["KOND_Y"], z_draht + 7.5)]
            c = kurve(mittel, OBEN, V(0.5, 0, -1))
            enden = "kondensator"
        else:
            continue
        pkt, seiten = paar_seiten(c, achse, V(0, 1, 0) if enden == "kondensator" else None)
        for i in (0, 1):
            vz = 1 if i == 0 else -1                # Pin 1 auf der Seite von „achse“
            punkte = [pins[i], pins[i] + OBEN * 1.2] + [p + q * (vz * ABST) for p, q in zip(pkt, seiten)]
            t_ende = c.tangent(c.LastParameter)[0]
            # Punkte, die zu dicht liegen, verwerfen (sonst schwingt der Spline)
            dicht = [punkte[0]]
            for p in punkte[1:]:
                if (p - dicht[-1]).Length > 0.6:
                    dicht.append(p)
            l = ader(dicht, OBEN, t_ende)
            if enden == "kondensator":
                # Ab dem Ende des Paares: Bézier-Bogen tangential in die Schlauchachse,
                # dann gerade bis 1,5 mm auf den Draht – mittig durch den 4-mm-Schlauch
                ende = dicht[-1]
                y_draht = g["KOND_Y"] + (kr if ende.y >= g["KOND_Y"] else -kr)
                ein = V(x_draht - 3.5, y_draht, z_draht)
                bz = Part.BezierCurve()
                bz.setPoles([ende, ende + t_ende * 3.0, ein - V(3.5, 0, 0), ein])
                gerade = Part.makeTube(Part.LineSegment(ein, ein + V(5.0, 0, 0)).toShape(), LITZE_R)
                l = Part.makeCompound([l, Part.makeTube(bz.toShape(), LITZE_R), gerade])
                # Schlauch ab 2 mm vor der Lötstelle bis 0,5 mm vor den Kondensator
                sch = Part.makeCylinder(0.8, g["KOND_DRAHT_L"] + 1.5, V(x_draht - 2.0, y_draht, z_draht), V(1, 0, 0))
                schlauch = sch if schlauch is None else schlauch.fuse(sch)
            if i == 0:
                rot = l if rot is None else Part.makeCompound([rot, l])
            else:
                schwarz = l if schwarz is None else Part.makeCompound([schwarz, l])
    setze(doc, "Stecker", stecker)
    setze(doc, "Litze_rot", rot)
    setze(doc, "Litze_schwarz", schwarz)
    if schlauch is not None:
        setze(doc, "Schrumpfschlauch", schlauch)
    return True


def bild():
    try:
        Gui.ActiveDocument.ActiveView.saveImage(BILD, 1600, 1000, "Current")
    except Exception:
        melde("Bildschirmfoto fehlgeschlagen: " + traceback.format_exc(limit=1), True)


def neu_bauen():
    if zustand["baut"]:
        return
    zustand["baut"] = True
    t0 = time.time()
    try:
        g = {"__name__": "gehaeuse_live", "__file__": SKRIPT, "LIVE_ANSICHT": True}
        ausgabe = io.StringIO()
        with open(SKRIPT, encoding="utf-8") as f, contextlib.redirect_stdout(ausgabe):
            exec(compile(f.read(), SKRIPT, "exec"), g)
        if ausgabe.getvalue():
            App.Console.PrintMessage(ausgabe.getvalue())
        zustand["werte"] = g
        wanne, deckel = g["wanne"], g["deckel"]
        doc = dokument()
        Gui.setActiveDocument(doc.Name)

        setze(doc, "Unterteil", wanne)
        hoch = App.Placement(V(0, 0, g["HOEHE"] + EXPLOSION), App.Rotation())
        setze(doc, "Deckel", deckel, hoch)
        einsaetze_zeigen(doc, g, hoch)

        # Solarmodule in den Taschen, auf der Klebefuge (Noppen) liegend
        module = None
        dicke = g.get("PANEL_D", 2.0)
        z_mod = g["DECKEL_D"] - g["TASCHE_TIEFE"] + g.get("KLEBER_D", 0.0)
        mitten = g.get("MODUL_X") or [sx * (g["TASCHE"] / 2 + g["STEG"] / 2) for sx in (-1, 1)]
        for cx in mitten:
            p = Part.makeBox(g["PANEL"], g["PANEL"], dicke,
                             V(cx - g["PANEL"] / 2, -g["PANEL"] / 2, z_mod))
            module = p if module is None else module.fuse(p)
        setze(doc, "Solarmodule", module, hoch)
        # Oberfläche aus dem Produktfoto (schwarzes ETFE mit Narbung)
        if os.path.exists(os.path.join(LIVE, "textur-modul.png")):
            for i, cx in enumerate(mitten):
                platz = App.Placement(V(cx - g["PANEL"] / 2, -g["PANEL"] / 2, z_mod + dicke + 0.01) + hoch.Base,
                                      App.Rotation())
                bildflaeche(doc, f"Modul{i + 1}_Bild", platz, g["PANEL"], g["PANEL"], "textur-modul.png")

        # Kleber: füllt die Tasche um und unter den Modulen (nicht über den Fenstern)
        if "TASCHE_B" in g:
            z0 = g["DECKEL_D"] - g["TASCHE_TIEFE"]
            kleber = Part.makeBox(g["TASCHE_B"], g["TASCHE_H"], g["TASCHE_TIEFE"],
                                  V(-g["TASCHE_B"] / 2, -g["TASCHE_H"] / 2, z0))
            f = g["TASCHE"] - 2 * g["AUFLAGE"]
            for cx in mitten:
                kleber = kleber.cut(Part.makeBox(f, f, g["TASCHE_TIEFE"] + 2, V(cx - f / 2, -f / 2, z0 - 1)))
            kleber = kleber.cut(module).cut(deckel)
            setze(doc, "Kleber", kleber, hoch)

        # O-Ring: Rundschnur entlang der Nutmittellinie, ungepresst (steht über)
        if "INNEN_F" in g and "ORING_D" in g:
            try:
                mitte = g["INNEN_F"].makeOffset2D((g["NUT_INNEN"] + g["NUT_AUSSEN"]) / 2, join=0).OuterWire.copy()
                mitte.translate(V(0, 0, g["HOEHE"] - g["NUT_T"] + g["ORING_D"] / 2))
                e0 = mitte.OrderedEdges[0]
                kreis = Part.Wire(Part.makeCircle(g["ORING_D"] / 2, e0.valueAt(e0.FirstParameter),
                                                  e0.tangentAt(e0.FirstParameter)))
                ring = mitte.makePipeShell([kreis], True, False)
                setze(doc, "Dichtring", ring)
            except Exception:
                melde("Dichtring nicht darstellbar: " + traceback.format_exc(limit=1), True)

        teile = g["inhalt"]()
        # Kondensator und seine Drähte als eigene Objekte mit eigener Farbe
        for name, obj in (("Kondensator", "Kondensator"), ("Kondensatordrähte", "Kondensatordraehte")):
            if name in teile:
                setze(doc, obj, teile.pop(name))
        if os.path.exists(os.path.join(LIVE, "textur-dae.png")) and druckausgleich_zeigen(doc, g):
            teile.pop("Druckausgleich", None)
        schrauben_zeigen(doc, g)
        # echte Platine mit Bild, Funkmodul und Buchsen statt der grünen Hüllkörper
        if platine_zeigen(doc, g):
            for name in ("Platine", "Bauteil 1", "Bauteil 2", "Bauteil 3", "Bauteil 4", "Bauteil 5"):
                teile.pop(name, None)
        inhalt = None
        for k in teile.values():
            inhalt = k if inhalt is None else inhalt.fuse(k)
        if inhalt is not None:
            setze(doc, "Inhalt", inhalt)
        elif doc.getObject("Inhalt") is not None:
            doc.removeObject("Inhalt")      # alles wird inzwischen einzeln dargestellt

        # Zusatzteile aus dem Skript (Halter, Paneelrahmen …): Name → (Form, Farbe)
        if "ansicht_extra" in g:
            for name, (form, farbe) in g["ansicht_extra"]().items():
                if form is None:                    # Teil gibt es in dieser Bauart nicht
                    if doc.getObject(name) is not None:
                        doc.removeObject(name)
                    continue
                FARBEN.setdefault(name, farbe)
                setze(doc, name, form)

        doc.recompute()
        if zustand["erstmals"]:
            Gui.ActiveDocument.ActiveView.viewIsometric()
            Gui.SendMsgToActiveView("ViewFit")
            zustand["erstmals"] = False
        Gui.updateGui()

        bb = wanne.BoundBox
        gueltig = "ja" if wanne.isValid() and deckel.isValid() else "NEIN"
        text = melde(f"neu gebaut in {time.time() - t0:.1f} s – Außenmaß {bb.XLength:.1f} × "
                     f"{bb.YLength:.1f} × {g['HOEHE'] + g['DECKEL_D']:.1f} mm, "
                     f"Unterteil {wanne.Volume / 1000:.1f} cm³, Deckel {deckel.Volume / 1000:.1f} cm³, "
                     f"gültig: {gueltig}") + "\n" + ausgabe.getvalue().rstrip()
        bild()
    except Exception:
        text = melde("FEHLER beim Neubau, altes Modell bleibt:\n" + traceback.format_exc(), True)
    finally:
        zustand["baut"] = False
    with open(STATUS, "w", encoding="utf-8") as f:
        f.write(text + "\n")


def befehl_ausfuehren():
    with open(BEFEHL, encoding="utf-8") as f:
        code = f.read()
    os.replace(BEFEHL, BEFEHL + ".erledigt")
    puffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(puffer):
            exec(compile(code, BEFEHL, "exec"), globals())
        Gui.updateGui()
        ergebnis = "ok"
    except Exception:
        ergebnis = "FEHLER\n" + traceback.format_exc()
    with open(ANTWORT, "w", encoding="utf-8") as f:
        f.write(time.strftime("%H:%M:%S ") + ergebnis + "\n" + puffer.getvalue())


def pruefen():
    try:
        m = os.path.getmtime(SKRIPT)
        if m != zustand["mtime"] and time.time() - m >= RUHE:
            zustand["mtime"] = m
            neu_bauen()
        if os.path.exists(BEFEHL):
            befehl_ausfuehren()
    except Exception:
        melde(traceback.format_exc(), True)


timer = QtCore.QTimer()
timer.timeout.connect(pruefen)
timer.start(700)
App._gehaeuse_live = {"timer": timer, "zustand": zustand}
melde("Live-Ansicht läuft – beobachte " + SKRIPT)
