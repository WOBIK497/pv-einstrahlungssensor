# Druckbares Gehäuse für den PV-Einstrahlungssensor (Platine v1, 38 × 46 mm).
# Aufruf: freecad.cmd erzeuge_gehaeuse.py   → STL und STEP im selben Ordner.
#
# Aufbau: Unterteil (Wanne) mit Platinenhalter, Kondensatorhalter und angedruckter
# Lasche zum Paneelrahmen (eine M6 durchs Montageloch, siehe HALTER_ART; die Bauart
# „getrennt“ mit eigenem Halter an vier M4-Einsätzen bleibt umschaltbar);
# Deckel mit einer gemeinsamen Tasche für
# die zwei 70-mm-Solarmodule (1 mm Klebefuge rundum und dazwischen). Unter jedem Modul ein Fenster für Kabel und Lötstelle,
# außen herum ein 8 mm breiter Klebering. Dichtung: 2-mm-Rundschnur in der Nut
# des Unterteils. Deckel mit sechs M3-Senkschrauben von unten: Senkung im Boden,
# Schraubendom innen an der Wand, Gewindeeinsatz in der Deckelunterseite. Die
# Nut folgt der Innenkontur und läuft innen um die Dome herum – die Schrauben-
# löcher liegen damit außerhalb der Dichtung. Druckausgleich über ein Membran-
# element M12 × 1,5, von außen in eine Bodentasche versenkt (Sechskant gegen
# Mitdrehen), innen auf einem Dom mit Gegenmutter gekontert.
#
# Koordinaten: x = lange Seite, y = kurze Seite (+y = oben am Hang), z = hoch.
import math
import os
import FreeCAD as App
import Part
import MeshPart
from FreeCAD import Vector as V

ORDNER = os.path.dirname(os.path.abspath(__file__))

# --- Parameter -------------------------------------------------------------
PANEL = 70.2            # Kantenlänge Solarmodul: 6 Stück gemessen 70,08–70,19 mm (14.11.2026)
PANEL_SPIEL = 2.0       # Tasche größer als Modul: 1 mm Klebefuge rundum
NOPPE_SPIEL = 0.1       # Luft zwischen Positionsnoppe und Modulkante
SEITEN_NOPPE_B = 2.0    # Breite der Positionsnoppen an den Taschenwänden
SEITEN_NOPPE_UNTER = 0.8   # so weit enden sie unter der Oberfläche – der Kleber deckt sie zu
FENSTER_R = 0.0         # Eckradius der Fenster unter den Modulen
PANEL_D = 1.8           # Moduldicke, gemessen 14.11.2026 (Händler: 2,0)
KLEBER_D = 1.0          # Klebefuge unter dem Modul, durch Noppen festgelegt; 1 mm, damit der
                        # elastische Kleber die Wärmedehnung ASA/FR-4 aufnimmt
TASCHE_TIEFE = PANEL_D + KLEBER_D   # Moduloberseite bündig mit der Deckeloberseite
NOPPE_D = 3.0           # Abstandsnoppen auf dem Klebering, je Tasche vier
AUFLAGE = 8.0           # Breite des Kleberings unter dem Modul
AUSSEN_B, AUSSEN_H = 160.0, 90.0   # Außenmaß des Gehäuses
MODUL_FUGE = 1.0        # Fuge zwischen den Modulen, zwei Distanznoppen 1 mm dick, kein Steg
EINSATZ_WAND = 2.0      # Mindestwand zwischen Einsatzloch und Modultasche
DECKEL_D = 7.2          # trägt die Gewindeeinsätze von unten (6,0 Loch + 1,2 darüber)
DECKEL_RUNDUNG = 2.0    # Radius der oberen umlaufenden Außenkante
WAND = 5.2             # Nut 2,8 mm + je 1,2 mm Material
MATERIAL = "ASA"          # schwarz; braucht geschlossenen Bauraum (gedruckt auf Prusa CORE One+)
MATERIAL_FESTIGKEIT = 40.0  # MPa, Zugfestigkeit gedruckt, vorsichtig angesetzt
MATERIAL_DEHNUNG = 0.02     # zulässige Randdehnung kurzzeitig beim Einrasten, quer zu den Lagen
BODEN = 2.4
INNEN_H = 22.6          # Innenhöhe der Wanne; mit SCHRAUBE_L → 5 mm Gewindeeingriff
R_ECKE = 5.0
RAHMENSEITE_ECKIG = True  # Seite zum Paneelrahmen (−y) ohne Eckradien und ohne Deckelrundung:
                          # rechtwinklig am Rahmen, keine Zwickel, in denen sich Schmutz sammelt
# Dichtung: geschlossener O-Ring als Axialdichtung (Deckel drückt von oben).
# Nut nach üblicher Faustregel: Breite 1,4 × d, Tiefe 0,75 × d → 25 % Verpressung,
# rund 75 % Nutfüllung. Der Ring wird in der Nut leicht gedehnt (ORING_DEHNUNG_SOLL),
# damit er straff an der Innenflanke liegt und beim Deckelaufsetzen nicht herausquillt.
ORING_D = 2.0           # Schnurstärke
ORING_ID = 148.0        # Innendurchmesser laut Katalog (123kugellager OR-148X2-EPDM70)
ORING_DEHNUNG_SOLL = 0.02
NUT_B, NUT_T = round(1.4 * ORING_D, 2), round(0.75 * ORING_D, 2)
# Deckelschrauben: Senkschrauben von unten durch Dome in den vier Ecken
# und je einer in der Mitte der Längswände (Lage siehe SCHRAUB_MITTEN unten)
DOM_D = 15.0            # Außendurchmesser Schraubendom (trägt die Nut innen herum)
DOM_ABSTAND = 1.2       # Dommitte ab Wandinnenseite
DOM_ECK_VERSATZ = 1.0   # Eckdome zusätzlich diagonal nach außen: Abstand Einsatz–Modultasche
AUSRUNDUNG = 3.0        # Übergang Dom–Wand, damit die Rundschnur nicht knickt
SCHRAUBE_L = 30.0       # Senkschraube ISO 10642 / DIN 7991 M3 × 30
SENK_D = 6.9            # Senkung 90°, Kopf M3 max. 6,72 mm
M3_EINSATZ_D, M3_EINSATZ_T = 4.0, 6.0   # Einsatz M3 × 5,7 (z. B. Ruthex) im Deckel
M3_DURCH = 3.4
M4_EINSATZ_D, M4_EINSATZ_T = 5.6, 8.5   # z. B. Ruthex M4 × 8,1
M4_RASTER = (100.0, 50.0)
PLATINE = (38.0, 46.0)
PLATINE_LOECHER = ((3.5, 42.5), (34.5, 42.5))  # ab Platinenecke oben links
ABSTAND_H = 5.0         # Höhe der Abstandshalter
PLATINE_SCHRAUBE_L = 6.0   # Linsenkopfschraube M3 (ISO 7045), formt ihr Gewinde im 2,6-mm-Loch
KOND_L, KOND_B = 36.0, 22.0   # Mulde für den 5,5-V-4-F-Kombikondensator
KOND_X, KOND_Y = 48.0, -4.0
# Kondensator selbst: Kombityp aus zwei Zellen nebeneinander im Schrumpfschlauch.
# Gemessen 14.11.2026 (3 Stück): Länge 22,55–22,80, Breite 25,60–25,64, Höhe 12,98–13,02 mm.
# Zellendurchmesser = halbe größte Breite (die Klammern greifen seitlich), Länge = größte
# Länge + 0,2 mm Luft zwischen den Stirnanschlägen
KOND_ZELLE_D, KOND_ZELLE_L = 12.82, 23.0
KOND_DRAHT_D, KOND_DRAHT_L = 0.6, 8.0
# Schnappklammern: je zwei federnde Arme greifen mit einer runden Rastnase über
# die Außenseiten der beiden Zellen; Kondensator wird von oben eingedrückt
KLAMMER_LAGE = (0.25, 0.75)   # Lage entlang der Zellen (Anteil der Zellenlänge)
KLAMMER_B = 6.0         # Breite in Zellenrichtung
KLAMMER_T = 1.0         # Armdicke (ASA ist spröder als PETG; 1,2 mm gaben 2,1 % Dehnung)
KLAMMER_LUFT = 0.15     # Luft zwischen Arm und Zelle
KLAMMER_WINKEL = 25.0   # Rastnase greift so viele Grad über dem Zellenäquator (vorher 30)
KLAMMER_NASE_R = 1.0    # Radius der Rastnase
KOND_ANSCHLAG_H = (3.0, 6.0)   # Stirnanschläge: Drahtseite (unter den Drähten, gemessen höchstens 4), Gegenseite
# Druckausgleichselement M12 × 1,5 (Amazon/PigJuan), gemessen 14.11.2026: gesamt 18,26, Kopf 8,20
# (Sechskant SW 16,79 über die ganze Höhe), Gewinde 10,06; Belüftungsschlitz 1,1 mm hoch mittig im Kopf;
# O-Ring liegt in einer Nut der Kopfauflage (trägt nicht auf, Taschentiefe unabhängig davon),
# von außen in eine Tasche im Boden versenkt, innen mit Gegenmutter gekontert
DAE_X, DAE_Y = -36.0, 0.0
DAE_SW, DAE_KOPF_H, DAE_GEWINDE_L = 16.8, 8.2, 10.0
DAE_SCHLITZ_H = 1.1        # Belüftungsschlitz mittig im Kopf: muss außerhalb des Sechskantsitzes liegen
DAE_LOCH = 12.4
DAE_TASCHE_D = 21.0       # runder Teil der Tasche (Kappe)
DAE_TASCHE_SW = 17.2      # Sechskant am Taschengrund (0,4 Luft zum Kopf): Kopf dreht beim Kontern nicht mit
DAE_SECHSKANT_T = 3.0     # endet 0,55 mm vor dem Belüftungsschlitz (3,55–4,65 über der Auflage)
DAE_TASCHE_T = 8.5        # Kopf liegt 0,3 mm hinter der Bodenfläche
MUTTER_SW, MUTTER_H = 15.9, 5.12  # Gegenmutter M12 × 1,5, gemessen 14.11.2026: SW 15,86, 5,12 hoch, Kragen Ø 16,83
DAE_DOM_D = 26.0          # 2,5 mm Wand um die Tasche
# Halter am langen Paneelrahmen (JA Solar JAM60D41, Datenblatt S. 2): Paneel quer,
# Gehäuse an der oberen Langkante neben dem Rahmen (−y = zum Paneel), Deckel bündig
# mit der Rahmenvorderkante. Eine gedruckte Platte an den vier M4-Einsätzen, ein Arm
# unter den Fußflansch des Rahmens, eine M6-Schraube durchs Montageloch (Langloch 7 × 10).
# Die Gehäusewand liegt direkt an der Rahmenaußenfläche (HALTER_SPALT = 0): sie
# nimmt das Hangabtriebsgewicht auf und sperrt auf ganzer Länge das Verdrehen um
# die einzelne Schraube. Mit Spalt > 0 füllt ihn eine Anschlagleiste am Halter.
RAHMEN_H = 30.0           # Rahmenhöhe (Datenblatt; am Paneel gemessen 29,9)
RAHMEN_FLANSCH = 28.0     # Fußflansch nach innen unter das Modul (Datenblatt, nicht messbar)
RAHMEN_FLANSCH_D = 1.7    # Flanschdicke aus der Profilzeichnung im Datenblatt ausgemessen
                          # (maßstabsgetreu, ±0,2) – geht nur in die Schraubenlänge ein
MONTAGELOCH_ABSTAND = 19.0     # Lochmitte ab Außenfläche des Rahmens: Datenblatt,
                               # (Breite 1134 − Lochabstand 1096) / 2
HALTER_D = 5.0            # Plattendicke unter dem Gehäuse
HALTER_PLATTE = (116.0, 66.0)   # Platte um die M4-Einsätze, frei von den Deckelschrauben
HALTER_ARM_B = 36.0       # Armbreite, frei von den mittleren Deckelschrauben (x ±24,9)
HALTER_SPALT = 0.0        # Abstand Gehäuse–Rahmen; 0 = Gehäuse liegt am Rahmen an
HALTER_LEISTE_H = 6.0     # Leiste ragt so weit über die Rahmenrückseite an der Außenfläche hoch
HALTER_LANGLOCH = 4.0     # M6-Loch als Langloch quer zum Rahmen (± 2 mm für das „ca. 19“)
M6_LOCH = 6.6
M4_DURCH = 4.5
DAE_FREI_D = 24.0         # Loch über der Druckausgleichstasche: Luft kommt weiter heran
# Bauart des Halters:
#   "getrennt" – eigenes Druckteil an vier M4-Einsätzen im Boden (Parameter HALTER_* oben)
#   "lasche"   – Lasche an der Langseite zum Paneel, mit dem Unterteil in einem Stück gedruckt.
#                Sie liegt beim Druck auf dem Bett, ihre Oberseite trifft die Rahmenrückseite:
#                Dicke = Gehäusehöhe − Rahmenhöhe. Ist LASCHE_D größer, wird der Boden dicker
#                und die Deckelschrauben sitzen um so viel tiefer versenkt (gleiche M3 × 30).
HALTER_ART = "lasche"
LASCHE_D = 2.2            # Mindestdicke der Lasche (2,2 = ohne Bodenzugabe)
BODEN_ZUSATZ = 0.0
if HALTER_ART == "lasche":
    BODEN_ZUSATZ = round(max(0.0, LASCHE_D - (BODEN + INNEN_H + DECKEL_D - RAHMEN_H)), 3)
    BODEN += BODEN_ZUSATZ
SCHRAUBE_Z = BODEN_ZUSATZ   # Kopf der Deckelschrauben liegt so tief im Boden

TASCHE = PANEL + PANEL_SPIEL                       # Taschenmaß je Modul
TASCHE_B = 2 * PANEL + MODUL_FUGE + PANEL_SPIEL     # gemeinsame Tasche für beide Module
TASCHE_H = TASCHE
MODUL_X = (-(PANEL + MODUL_FUGE) / 2, (PANEL + MODUL_FUGE) / 2)   # Modulmitten
B, H = AUSSEN_B, AUSSEN_H
RAND_X, RAND_Y = (B - TASCHE_B) / 2, (H - TASCHE_H) / 2
HOEHE = BODEN + INNEN_H
DOM_Y = H / 2 - WAND - DOM_ABSTAND
DOM_X = B / 2 - WAND - DOM_ABSTAND   # Eckdome stecken in beiden Wänden
ECK_X, ECK_Y = DOM_X + DOM_ECK_VERSATZ, DOM_Y + DOM_ECK_VERSATZ
# mittlere Schrauben: so weit außen, dass der Einsatz EINSATZ_WAND zur Tasche behält;
# je Längsseite zwei, gleichmäßig zwischen den Ecken verteilt
MITTE_Y = TASCHE_H / 2 + EINSATZ_WAND + M3_EINSATZ_D / 2
SCHRAUB_MITTEN = ([(sx * ECK_X, sy * ECK_Y) for sx in (-1, 1) for sy in (-1, 1)]
                  + [(sx * ECK_X / 3, sy * MITTE_Y) for sx in (-1, 1) for sy in (-1, 1)])
DAE_DOM_H = DAE_TASCHE_T + DAE_GEWINDE_L - MUTTER_H - 1.0   # 1 mm Gewinde über der Mutter
# Paneelrahmen im Gehäusesystem (z = 0 Gehäuseunterseite): Rahmenrückseite bei Z_RAHMEN,
# damit die Rahmenvorderkante genau auf Höhe der Deckeloberseite liegt
Z_RAHMEN = HOEHE + DECKEL_D - RAHMEN_H
Y_RAHMEN = -H / 2 - HALTER_SPALT          # Außenfläche des Rahmens
Y_LOCH = Y_RAHMEN - MONTAGELOCH_ABSTAND        # Montageloch im Flansch
Y_FLANSCH = Y_RAHMEN - RAHMEN_FLANSCH     # Flanschende unter dem Modul


def sechskant(sw, h, x, y, z):
    """Sechskantprisma mit Schlüsselweite sw."""
    r = sw / 2 / math.cos(math.radians(30))
    pkt = [V(x + r * math.cos(math.radians(60 * i)), y + r * math.sin(math.radians(60 * i)), z)
           for i in range(6)]
    return Part.Face(Part.makePolygon(pkt + [pkt[0]])).extrude(V(0, 0, h))


def rrect(w, h, r, z, hoehe, cx=0.0, cy=0.0):
    """Quader mit gerundeten senkrechten Kanten."""
    r = min(r, w / 2 - 0.01, h / 2 - 0.01)
    if r <= 0.05:
        return Part.makeBox(w, h, hoehe, V(cx - w / 2, cy - h / 2, z))
    teile = [Part.makeBox(w - 2 * r, h, hoehe, V(cx - w / 2 + r, cy - h / 2, z)),
             Part.makeBox(w, h - 2 * r, hoehe, V(cx - w / 2, cy - h / 2 + r, z))]
    for sx in (-1, 1):
        for sy in (-1, 1):
            teile.append(Part.makeCylinder(r, hoehe, V(cx + sx * (w / 2 - r), cy + sy * (h / 2 - r), z)))
    s = teile[0]
    for t in teile[1:]:
        s = s.fuse(t)
    return s.removeSplitter()


def aussenkontur(z, hoehe):
    """Außenumriss von Unterteil und Deckel: Ecken mit R_ECKE gerundet, zur
    Rahmenseite (−y) bei RAHMENSEITE_ECKIG rechtwinklig."""
    k = rrect(B, H, R_ECKE, z, hoehe)
    if RAHMENSEITE_ECKIG:
        k = k.fuse(Part.makeBox(B, H / 2, hoehe, V(-B / 2, -H / 2, z))).removeSplitter()
    return k


def zyl_loch(d, tiefe, x, y, z):
    return Part.makeCylinder(d / 2, tiefe, V(x, y, z))


def inhalt():
    """Hüllkörper für Platine, Bauteile und Kondensator (Passungsprüfung, Live-Ansicht)."""
    z_pl = BODEN + ABSTAND_H
    platine = Part.makeBox(PLATINE[0], PLATINE[1], 1.6, V(-PLATINE[0] / 2, -PLATINE[1] / 2, z_pl))

    # Bauteile oben: Funkmodul 2,2 mm, ZH-Buchsen mit Stecker bis 10 mm über der Platine.
    # Platinenkoordinaten (KiCad) → Gehäuse: x - 119, 123 - y
    def bk(x0, x1, y0, y1, h):
        return Part.makeBox(x1 - x0, y1 - y0, h, V(x0 - 119, 123 - y1, z_pl + 1.6))
    teile = {"Platine": platine,
             "Bauteil 1": bk(114, 124, 100, 116, 2.2),          # MDBT42Q
             "Bauteil 2": bk(110.5, 117.5, 139.5, 145.5, 10.0),  # J1 mit Stecker
             "Bauteil 3": bk(100.0, 106.0, 120.5, 127.5, 10.0),  # J2 mit Stecker
             "Bauteil 4": bk(105.5, 135.0, 117.0, 137.5, 2.5),   # Kleinteile, Regler, R1/R2
             "Bauteil 5": bk(120.5, 127.5, 139.5, 145.5, 10.0)}  # J3 (Superkondensator) mit Stecker
    # Kondensator liegend in der Mulde, Zellen längs, Drähte zur Platine (nach −x)
    r = KOND_ZELLE_D / 2
    x_ende = KOND_X + KOND_L / 2 - 0.5
    x0 = x_ende - KOND_ZELLE_L
    zellen, draehte = None, None
    for dy in (-r, r):
        z = Part.makeCylinder(r, KOND_ZELLE_L, V(x0, KOND_Y + dy, BODEN + r), V(1, 0, 0))
        d = Part.makeCylinder(KOND_DRAHT_D / 2, KOND_DRAHT_L, V(x0, KOND_Y + dy, BODEN + r), V(-1, 0, 0))
        zellen = z if zellen is None else zellen.fuse(z)
        draehte = d if draehte is None else draehte.fuse(d)
    teile["Kondensator"] = zellen
    teile["Kondensatordrähte"] = draehte
    # Druckausgleichselement: Kopf in der Bodentasche, Gewinde, Gegenmutter auf dem Dom
    kopf = sechskant(DAE_SW, DAE_KOPF_H, DAE_X, DAE_Y, DAE_TASCHE_T - DAE_KOPF_H)
    gewinde = Part.makeCylinder(6.0, DAE_GEWINDE_L, V(DAE_X, DAE_Y, DAE_TASCHE_T))
    mutter = sechskant(MUTTER_SW, MUTTER_H, DAE_X, DAE_Y, DAE_DOM_H)
    teile["Druckausgleich"] = kopf.fuse(gewinde).fuse(mutter)
    return teile


# --- Unterteil -------------------------------------------------------------
# Innenkontur als Fläche: Innenraum ohne die Schraubendome, Übergänge zwischen
# Dom und Wand ausgerundet (erst schrumpfen, dann wieder wachsen lassen).
roh = rrect(B - 2 * WAND, H - 2 * WAND, max(R_ECKE - WAND, 1.0), 0, 1)
for x, y in SCHRAUB_MITTEN:
    roh = roh.cut(Part.makeCylinder(DOM_D / 2, 3, V(x, y, -1)))
roh = roh.removeSplitter()
boden_f = [f for f in roh.Faces if abs(f.BoundBox.ZMax) < 1e-6]
assert len(boden_f) == 1, "Innenkontur nicht eindeutig"
INNEN_F = boden_f[0].makeOffset2D(-AUSRUNDUNG, join=0).makeOffset2D(AUSRUNDUNG, join=0)

hohl = INNEN_F.extrude(V(0, 0, INNEN_H + 1))
hohl.translate(V(0, 0, BODEN))
wanne = aussenkontur(0, HOEHE).cut(hohl)

# Dichtungsnut im festen Abstand zur Innenkontur: in der Wand mittig, an den
# Domen auf deren Innenseite (Schraubenlöcher liegen außerhalb der Dichtung)
NUT_INNEN, NUT_AUSSEN = WAND / 2 - NUT_B / 2, WAND / 2 + NUT_B / 2
nut_f = INNEN_F.makeOffset2D(NUT_AUSSEN, join=0).cut(INNEN_F.makeOffset2D(NUT_INNEN, join=0))
nut = nut_f.extrude(V(0, 0, NUT_T + 1))
nut.translate(V(0, 0, HOEHE - NUT_T))
wanne = wanne.cut(nut)
# Länge der Nutmittellinie gegen den Umfang des O-Rings (Mittellinie π·(ID + d))
NUT_LAENGE = INNEN_F.makeOffset2D((NUT_INNEN + NUT_AUSSEN) / 2, join=0).OuterWire.Length
ORING_DEHNUNG = NUT_LAENGE / (math.pi * (ORING_ID + ORING_D)) - 1
ORING_ID_IDEAL = NUT_LAENGE / (1 + ORING_DEHNUNG_SOLL) / math.pi - ORING_D

# Platine: Kante oben (Antenne) bei y = +PLATINE[1]/2, mittig in x
px0, py0 = -PLATINE[0] / 2, PLATINE[1] / 2
innen = []
for lx, ly in PLATINE_LOECHER:
    x, y = px0 + lx, py0 - ly
    innen.append(Part.makeCylinder(3.0, ABSTAND_H, V(x, y, BODEN)))
# Halter für die Oberkante mit Schlitz, in den die Platine eingeschoben wird
for x in (-12.0, 12.0):
    pfosten = Part.makeBox(5.0, 4.0, ABSTAND_H + 1.6 + 2.0, V(x - 2.5, py0 - 1.5, BODEN))
    schlitz = Part.makeBox(5.2, 1.8, 1.9, V(x - 2.6, py0 - 1.6, BODEN + ABSTAND_H - 0.1))
    innen.append(pfosten.cut(schlitz))
# Halter für den Superkondensator: zwei Stirnanschläge in Kondensatorbreite und
# Schnappklammern. Seitlich halten nur die Klammern – die Zellen sind dort rund,
# ein niedriger Rand würde sie nicht fassen. Der Anschlag an der Drahtseite ist
# niedrig, die Drähte laufen darüber hinweg.
kr = KOND_ZELLE_D / 2
k_ende = KOND_X + KOND_L / 2 - 0.5
k_x0 = k_ende - KOND_ZELLE_L
k_nase_y = kr + (kr + KLAMMER_NASE_R) * math.cos(math.radians(KLAMMER_WINKEL))
k_nase_z = BODEN + kr + (kr + KLAMMER_NASE_R) * math.sin(math.radians(KLAMMER_WINKEL))
k_innen = KOND_ZELLE_D + KLAMMER_LUFT          # Arm-Innenseite ab Kondensatormitte
for x_a, h_a in ((k_x0 - 2.0, KOND_ANSCHLAG_H[0]), (k_ende, KOND_ANSCHLAG_H[1])):
    # obere Ecken bodentief abgerundet: Radius = Höhe, die Rundung läuft am Boden aus
    huelle = Part.makeBox(2.0, 2 * KOND_ZELLE_D, h_a, V(x_a, KOND_Y - KOND_ZELLE_D, BODEN))
    a = Part.makeBox(2.0, 2 * (KOND_ZELLE_D - h_a), h_a, V(x_a, KOND_Y - KOND_ZELLE_D + h_a, BODEN))
    for s in (-1, 1):
        a = a.fuse(Part.makeCylinder(h_a, 2.0, V(x_a, KOND_Y + s * (KOND_ZELLE_D - h_a), BODEN), V(1, 0, 0)))
    innen.append(a.common(huelle).removeSplitter())
for f in KLAMMER_LAGE:
    xc = k_x0 + f * KOND_ZELLE_L
    for s in (-1, 1):
        y_arm = KOND_Y + s * k_innen if s > 0 else KOND_Y - k_innen - KLAMMER_T
        innen.append(Part.makeBox(KLAMMER_B, KLAMMER_T, k_nase_z - BODEN,
                                  V(xc - KLAMMER_B / 2, y_arm, BODEN)))
        innen.append(Part.makeCylinder(KLAMMER_NASE_R, KLAMMER_B,
                                       V(xc - KLAMMER_B / 2, KOND_Y + s * k_nase_y, k_nase_z), V(1, 0, 0)))
# Säulen für die M4-Einsätze des getrennten Halters (von außen eingepresst, Boden bleibt dicht)
m4 = ([(sx * M4_RASTER[0] / 2, sy * M4_RASTER[1] / 2) for sx in (-1, 1) for sy in (-1, 1)]
      if HALTER_ART == "getrennt" else [])
for x, y in m4:
    innen.append(Part.makeCylinder(5.0, M4_EINSATZ_T + 2.0, V(x, y, 0)))
# Dom für das Druckausgleichselement
innen.append(Part.makeCylinder(DAE_DOM_D / 2, DAE_DOM_H, V(DAE_X, DAE_Y, 0)))
# Angedruckte Lasche zum Rahmenflansch: so lang wie die gerade Gehäusewand (bei eckiger
# Rahmenseite die ganze Länge), Oberseite an der Rahmenrückseite, Ende gerundet; greift 1 mm in die Wand
lasche = None
if HALTER_ART == "lasche":
    _lb = B if RAHMENSEITE_ECKIG else B - 2 * R_ECKE
    _ll = -H / 2 - Y_FLANSCH
    lasche = rrect(_lb, 2 * _ll, 6.0, 0, Z_RAHMEN, 0, -H / 2).common(
        Part.makeBox(_lb + 2, _ll + 1.0, Z_RAHMEN + 2, V(-_lb / 2 - 1, Y_FLANSCH - 1, -1)))
    innen.append(lasche)
for t in innen:
    wanne = wanne.fuse(t)
for lx, ly in PLATINE_LOECHER:
    wanne = wanne.cut(zyl_loch(2.6, ABSTAND_H + 0.1, px0 + lx, py0 - ly, BODEN))
for x, y in m4:
    wanne = wanne.cut(zyl_loch(M4_EINSATZ_D, M4_EINSATZ_T, x, y, -0.01))
# Durchgangsloch und 90°-Senkung von außen, Kopf liegt bündig mit dem Boden – bei dickerem
# Boden (BODEN_ZUSATZ) um so viel tiefer, darunter eine Ansenkung für den Schlüssel
senk_h = (SENK_D - M3_DURCH) / 2
for x, y in SCHRAUB_MITTEN:
    wanne = wanne.cut(zyl_loch(M3_DURCH, HOEHE + 1, x, y, -0.5))
    wanne = wanne.cut(Part.makeCone(SENK_D / 2 + 0.01, M3_DURCH / 2, senk_h + 0.01, V(x, y, SCHRAUBE_Z - 0.01)))
    if SCHRAUBE_Z > 0:
        wanne = wanne.cut(zyl_loch(SENK_D + 0.02, SCHRAUBE_Z + 0.01, x, y, -0.01))
# M6-Langloch in der Lasche für das Montageloch
if lasche is not None:
    _sl = Part.makeBox(M6_LOCH, HALTER_LANGLOCH, 100, V(-M6_LOCH / 2, Y_LOCH - HALTER_LANGLOCH / 2, -50))
    for _s in (-1, 1):
        _sl = _sl.fuse(Part.makeCylinder(M6_LOCH / 2, 100, V(0, Y_LOCH + _s * HALTER_LANGLOCH / 2, -50)))
    wanne = wanne.cut(_sl)

# Druckausgleich: Durchgang, runde Tasche für die Kappe, Sechskant am Taschengrund
wanne = wanne.cut(zyl_loch(DAE_LOCH, DAE_DOM_H + 1, DAE_X, DAE_Y, -0.5))
wanne = wanne.cut(zyl_loch(DAE_TASCHE_D, DAE_TASCHE_T - DAE_SECHSKANT_T + 0.01, DAE_X, DAE_Y, -0.01))
wanne = wanne.cut(sechskant(DAE_TASCHE_SW, DAE_SECHSKANT_T, DAE_X, DAE_Y, DAE_TASCHE_T - DAE_SECHSKANT_T))
wanne = wanne.removeSplitter()

# --- Deckel ----------------------------------------------------------------
deckel = aussenkontur(0, DECKEL_D)
# Obere Außenkante abrunden (vor allen Ausschnitten: dann sind es nur die Kanten des
# Außenumrisses auf der Oberseite) – zur Rahmenseite bei RAHMENSEITE_ECKIG nicht, dort
# stößt der Deckel scharfkantig und bündig an die Rahmenvorderkante
oben = [k for k in deckel.Edges if abs(k.BoundBox.ZMin - DECKEL_D) < 1e-6 and abs(k.BoundBox.ZMax - DECKEL_D) < 1e-6
        and not (RAHMENSEITE_ECKIG and k.BoundBox.YMax < -H / 2 + 1e-6)]
deckel = deckel.makeFillet(DECKEL_RUNDUNG, oben)
# Gewindeeinsätze von der Unterseite, Sackloch – oben bleibt der Deckel geschlossen
for x, y in SCHRAUB_MITTEN:
    deckel = deckel.cut(zyl_loch(M3_EINSATZ_D, M3_EINSATZ_T + 0.01, x, y, -0.01))
fenster = TASCHE - 2 * AUFLAGE
z0 = DECKEL_D - TASCHE_TIEFE
# eine gemeinsame Tasche für beide Module, kein Steg dazwischen
deckel = deckel.cut(Part.makeBox(TASCHE_B, TASCHE_H, TASCHE_TIEFE + 1, V(-TASCHE_B / 2, -TASCHE_H / 2, z0)))
# Positionsnoppen zentrieren die Module in der Fuge und enden unter der
# Oberfläche, damit der Kleber sie zudeckt
t = PANEL_SPIEL / 2 - NOPPE_SPIEL
h = TASCHE_TIEFE - SEITEN_NOPPE_UNTER
for cx in MODUL_X:
    deckel = deckel.cut(rrect(fenster, fenster, FENSTER_R, -1, DECKEL_D + 2, cx, 0))
    for p in (-PANEL / 4, PANEL / 4):          # je Modul zwei an jeder Längswand
        for s in (-1, 1):
            yw = s * TASCHE_H / 2
            deckel = deckel.fuse(Part.makeBox(SEITEN_NOPPE_B, t + 0.2, h,
                                              V(cx + p - SEITEN_NOPPE_B / 2, yw - t if s > 0 else yw - 0.2, z0)))
    # Höhennoppen in den Ecken des Kleberings: Das Modul liegt darauf, der
    # Kleber füllt die Fuge drumherum – so sitzt die Oberseite genau bündig
    a = TASCHE / 2 - AUFLAGE / 2
    for ex in (-1, 1):
        for ey in (-1, 1):
            deckel = deckel.fuse(Part.makeCylinder(NOPPE_D / 2, KLEBER_D, V(cx + ex * a, ey * a, z0)))
for p in (-PANEL / 4, PANEL / 4):
    for s in (-1, 1):                           # je zwei an den Stirnwänden
        xw = s * TASCHE_B / 2
        deckel = deckel.fuse(Part.makeBox(t + 0.2, SEITEN_NOPPE_B, h,
                                          V(xw - t if s > 0 else xw - 0.2, p - SEITEN_NOPPE_B / 2, z0)))
    # Distanznoppe zwischen den Modulen, so dick wie die Fuge
    deckel = deckel.fuse(Part.makeBox(MODUL_FUGE, SEITEN_NOPPE_B, h,
                                      V(-MODUL_FUGE / 2, p - SEITEN_NOPPE_B / 2, z0)))
deckel = deckel.removeSplitter()

# --- Halter (nur Bauart "getrennt") ---------------------------------------
# Eigenes Druckteil: Platte an den M4-Einsätzen, Arm unter den Rahmenflansch.
halter = None
Z_HALTER = min(0.0, Z_RAHMEN) - HALTER_D  # Halterunterseite (liegt beim Druck auf dem Bett)
if HALTER_ART == "getrennt":
    _bx, _by = HALTER_PLATTE
    halter = rrect(_bx, _by, R_ECKE, Z_HALTER, -Z_HALTER)
    # Verbindung Platte → Gehäusekante, Oberseite an der Gehäuseunterseite
    halter = halter.fuse(Part.makeBox(HALTER_ARM_B, H / 2 - _by / 2 + 1.0, -Z_HALTER,
                                      V(-HALTER_ARM_B / 2, -H / 2, Z_HALTER)))
    # Arm unter dem Flansch, Oberseite an der Rahmenrückseite, Ende gerundet
    _arm_l = -H / 2 - Y_FLANSCH
    _arm = rrect(HALTER_ARM_B, 2 * _arm_l, 6.0, Z_HALTER, Z_RAHMEN - Z_HALTER, 0, -H / 2)
    halter = halter.fuse(_arm.common(Part.makeBox(HALTER_ARM_B + 2, _arm_l + 1, 100,
                                                  V(-HALTER_ARM_B / 2 - 1, Y_FLANSCH - 1, -50))))
    # Anschlagleiste nur, wenn zwischen Gehäuse und Rahmen ein Spalt bleibt
    if HALTER_SPALT > 0.05:
        halter = halter.fuse(Part.makeBox(HALTER_ARM_B, HALTER_SPALT, Z_RAHMEN + HALTER_LEISTE_H - Z_HALTER,
                                          V(-HALTER_ARM_B / 2, Y_RAHMEN, Z_HALTER)))
    # M6-Langloch für das Montageloch
    _ll = Part.makeBox(M6_LOCH, HALTER_LANGLOCH, 100, V(-M6_LOCH / 2, Y_LOCH - HALTER_LANGLOCH / 2, -50))
    for _s in (-1, 1):
        _ll = _ll.fuse(Part.makeCylinder(M6_LOCH / 2, 100, V(0, Y_LOCH + _s * HALTER_LANGLOCH / 2, -50)))
    halter = halter.cut(_ll)
    for x, y in m4:
        halter = halter.cut(zyl_loch(M4_DURCH, 100, x, y, -50))
    halter = halter.cut(zyl_loch(DAE_FREI_D, 100, DAE_X, DAE_Y, -50))
    halter = halter.removeSplitter()


def ansicht_extra():
    """Nur für die Live-Ansicht: Rahmenstück (vereinfacht nach dem Datenblattprofil),
    Paneelglas und die Schrauben am Halter. Name → (Form, Farbe)."""
    # Profil in Rahmenkoordinaten: u = ab Außenfläche nach innen, w = ab Rahmenrückseite
    L = 320.0

    def stab(u0, u1, w0, w1):
        return Part.makeBox(L, u1 - u0, w1 - w0, V(-L / 2, Y_RAHMEN - u1, Z_RAHMEN + w0))
    rahmen = stab(0, 1.6, 0, RAHMEN_H)                         # Außenwand
    for teil in (stab(0, 9.0, RAHMEN_H - 1.8, RAHMEN_H),       # Lippe vor dem Glas
                 stab(0, 12.0, 21.0, 22.6),                    # Auflage unter dem Glas
                 stab(9.0, 10.5, 0, 21.0),                     # Innenwand der Kammer
                 stab(0, RAHMEN_FLANSCH, 0, RAHMEN_FLANSCH_D)):  # Fußflansch
        rahmen = rahmen.fuse(teil)
    montageloch = Part.makeBox(10.0 - 7.0, 7.0, 10, V(-1.5, Y_LOCH - 3.5, Z_RAHMEN - 5))
    for s in (-1, 1):
        montageloch = montageloch.fuse(Part.makeCylinder(3.5, 10, V(s * 1.5, Y_LOCH, Z_RAHMEN - 5)))
    rahmen = rahmen.cut(montageloch).removeSplitter()
    glas = stab(3.0, 160.0, 22.8, 27.8)
    stahl = []
    # M6: Kopf innen auf dem Flansch, Scheibe und Mutter unter Halter bzw. Lasche
    z_fl = Z_RAHMEN + RAHMEN_FLANSCH_D
    kopf = sechskant(10.0, 4.0, 0, Y_LOCH, z_fl)
    stahl.append(kopf.common(Part.makeCone(5.0 + 4.0 * 1.732, 5.0, 4.0, V(0, Y_LOCH, z_fl))))   # 30°-Fase am Kopf
    # Schaft mit Gewinde M6 × 1 (ISO 4017, bis zum Kopf): Kern Ø 4,92 und ein Gewindesteg
    # mit 60°-Profil als Schraubenlinie, wie bei den M3-Schrauben der Live-Ansicht
    r_kern, steigung, tiefe = 2.46, 1.0, 0.54
    stahl.append(Part.makeCylinder(r_kern, M6_L, V(0, Y_LOCH, z_fl - M6_L)))
    try:
        wendel = Part.makeHelix(steigung, M6_L - 1.0, r_kern - 0.02)
        wendel.translate(V(0, Y_LOCH, z_fl - M6_L + 0.5))
        p0 = wendel.Vertexes[0].Point
        rad = V(p0.x, p0.y - Y_LOCH, 0)
        rad.normalize()
        b = steigung * 0.42
        profil = Part.makePolygon([p0 + V(0, 0, -b), p0 + rad * (tiefe + 0.02), p0 + V(0, 0, b), p0 + V(0, 0, -b)])
        stahl.append(Part.Wire(wendel).makePipeShell([profil], True, True))
    except Exception:
        stahl.append(Part.makeCylinder(3.0, M6_L, V(0, Y_LOCH, z_fl - M6_L)))
    stahl.append(Part.makeCylinder(9.0, 1.6, V(0, Y_LOCH, Z_HINTEN - 1.6)).cut(
        Part.makeCylinder(3.2, 2, V(0, Y_LOCH, Z_HINTEN - 1.8))))
    stahl.append(sechskant(10.0, 6.0, 0, Y_LOCH, Z_HINTEN - 7.6))
    # M4 Zylinderkopf (ISO 4762) von hinten in die Einsätze
    for x, y in m4:
        stahl.append(Part.makeCylinder(3.5, 4.0, V(x, y, Z_HALTER - 4.0)))
        stahl.append(Part.makeCylinder(2.0, M4_L, V(x, y, Z_HALTER)))
    return {"Rahmen": (rahmen, (0.10, 0.10, 0.11)),
            "Paneelglas": (glas, (0.12, 0.16, 0.30)),
            "Halter": (halter, (0.80, 0.80, 0.78)),     # None bei angedruckter Lasche
            "Halterschrauben": (Part.makeCompound(stahl), (0.72, 0.74, 0.77))}


# --- Kontrollen ------------------------------------------------------------
eingriff = SCHRAUBE_L - (HOEHE - SCHRAUBE_Z)
print(f"Deckelschraube M3 × {SCHRAUBE_L:.0f}: greift {eingriff:.1f} mm in den Deckel "
      f"(Einsatzloch {M3_EINSATZ_T:.1f} mm tief, Deckel darüber {DECKEL_D - M3_EINSATZ_T:.1f} mm)"
      + (f", Kopf {SCHRAUBE_Z:.1f} mm tief im Boden" if SCHRAUBE_Z > 0 else ""))
if not 2.0 <= eingriff <= M3_EINSATZ_T - 0.3:
    print("WARNUNG: Schraubenlänge passt nicht zu Innenhöhe und Einsatz")
# Wandstärke zwischen Einsatzloch und Modultasche, geometrisch gemessen
leer = Part.makeBox(TASCHE_B, TASCHE_H, TASCHE_TIEFE, V(-TASCHE_B / 2, -TASCHE_H / 2, DECKEL_D - TASCHE_TIEFE))
print(f"Außenmaß {B:.1f} × {H:.1f} mm, Tasche {TASCHE_B:.1f} × {TASCHE_H:.1f} mm, "
      f"Rand {RAND_X:.2f} (Stirn) / {RAND_Y:.2f} (Längsseite)")
abstand = min(zyl_loch(M3_EINSATZ_D, M3_EINSATZ_T, x, y, 0).distToShape(leer)[0] for x, y in SCHRAUB_MITTEN)
print(f"Einsatzloch neben der Modultasche: {abstand:.2f} mm Wand")
if abstand < 2.0:
    print("WARNUNG: Einsatzloch zu nah an der Modultasche (< 2 mm)")
# Senkung im Boden bis zur Außenhaut
seiten = Part.Compound([f for f in aussenkontur(-1, 3).Faces if abs(f.normalAt(0.5, 0.5).z) < 0.01
                        or f.Surface.__class__.__name__ == "Cylinder"])
senk_wand = min(Part.makeCylinder(SENK_D / 2, 1, V(x, y, 0)).distToShape(seiten)[0]
                for x, y in SCHRAUB_MITTEN)
print(f"Senkung bis Außenhaut: {senk_wand:.2f} mm")
nut_loch = DOM_D / 2 - NUT_AUSSEN - M3_DURCH / 2
nut_einsatz = DOM_D / 2 - NUT_AUSSEN - M3_EINSATZ_D / 2
print(f"Nut innen am Dom: {nut_loch:.1f} mm bis Schraubenloch, {nut_einsatz:.1f} mm bis Einsatzloch im Deckel")
_schlitz_u = (DAE_KOPF_H - DAE_SCHLITZ_H) / 2   # Schlitzunterkante ab der Kopfauflage
print(f"Druckausgleich: Belüftungsschlitz {_schlitz_u:.2f}–{_schlitz_u + DAE_SCHLITZ_H:.2f} mm über der Auflage, "
      f"Sechskantsitz {DAE_SECHSKANT_T:.1f} mm tief, {_schlitz_u - DAE_SECHSKANT_T:.2f} mm Abstand")
if DAE_SECHSKANT_T > _schlitz_u - 0.3:
    print("WARNUNG: Sechskantsitz verdeckt den Belüftungsschlitz des Druckausgleichs")
print(f"Druckausgleich: Dom {DAE_DOM_H:.1f} mm hoch, {DAE_DOM_H - DAE_TASCHE_T:.1f} mm Material über der "
      f"Tasche, Gewinde ragt {DAE_TASCHE_T + DAE_GEWINDE_L - DAE_DOM_H:.1f} mm für die Mutter ({MUTTER_H:.0f} mm) heraus")
print(f"Nut {NUT_B:.2f} × {NUT_T:.2f} mm, Füllung {math.pi * ORING_D ** 2 / 4 / (NUT_B * NUT_T) * 100:.0f} %, "
      f"Mittellinie {NUT_LAENGE:.1f} mm")
print(f"O-Ring {ORING_ID:.0f} × {ORING_D:.1f}: Dehnung {ORING_DEHNUNG * 100:+.2f} % "
      f"(Soll {ORING_DEHNUNG_SOLL * 100:.0f} % → Innendurchmesser {ORING_ID_IDEAL:.1f} mm)")
if not 0.005 <= ORING_DEHNUNG <= 0.04:
    print("WARNUNG: O-Ring passt nicht zur Nutlänge (Dehnung außerhalb 0,5–4 %)")
if min(nut_loch, nut_einsatz) < 1.0:
    print("WARNUNG: Nut zu nah an Schraube oder Einsatz – Dom vergrößern")
print(f"Modultasche {TASCHE_TIEFE:.1f} mm tief (Modul {PANEL_D:.1f} + Klebefuge {KLEBER_D:.1f}), "
      f"Taschenboden {DECKEL_D - TASCHE_TIEFE:.1f} mm, Modul bündig bei {DECKEL_D - TASCHE_TIEFE + KLEBER_D + PANEL_D:.1f} = {DECKEL_D:.1f} mm")
# Platinenschraube: Spitze muss im Loch des Abstandshalters enden (Loch endet am Boden)
p_eingriff = PLATINE_SCHRAUBE_L - 1.6
print(f"Platinenschraube M3 × {PLATINE_SCHRAUBE_L:.0f}: {p_eingriff:.1f} mm im Abstandshalter, "
      f"Spitze {ABSTAND_H - p_eingriff:.1f} mm über dem Boden")
if p_eingriff > ABSTAND_H - 0.3 or p_eingriff < 3.0:
    print("WARNUNG: Platinenschraube zu lang (stößt auf den Boden) oder zu kurz")
# Schnappklammer: Auslenkung beim Eindrücken und Randdehnung des Arms (Biegebalken)
k_weg = KOND_ZELLE_D - (k_nase_y - KLAMMER_NASE_R)
k_arm = k_nase_z - BODEN
k_dehnung = 1.5 * KLAMMER_T * k_weg / k_arm ** 2
print(f"Schnappklammer: Arm {k_arm:.1f} mm lang, federt beim Einrasten {k_weg:.2f} mm aus, "
      f"Dehnung {k_dehnung * 100:.1f} % ({MATERIAL} quer zu den Lagen: höchstens {MATERIAL_DEHNUNG * 100:.0f} %)")
if k_dehnung > MATERIAL_DEHNUNG:
    print("WARNUNG: Klammerarm wird beim Einrasten überdehnt – dünner oder länger machen")
# Halter: Schraubenlängen aus Klemmlänge, Abstand zu den Deckelschrauben und zum Druckausgleich
NORM_L = (8, 10, 12, 16, 20, 25, 30, 35, 40)
Z_HINTEN = Z_HALTER if HALTER_ART == "getrennt" else 0.0          # Rückseite unter dem Flansch
_m6_klemm = RAHMEN_FLANSCH_D + (Z_RAHMEN - Z_HINTEN) + 1.6        # Flansch + Arm/Lasche + Scheibe
M6_L = next(l for l in NORM_L if l >= _m6_klemm + 6.0 + 1.5)       # Sicherungsmutter 6 mm + Überstand
M4_L = max(l for l in NORM_L if l - HALTER_D <= M4_EINSATZ_T - 1.0)
_lage = (f"Deckel bündig mit der Rahmenvorderkante, Rahmenrückseite {Z_RAHMEN:+.1f} mm über der "
         f"Gehäuseunterseite, Montageloch {-Y_LOCH - H / 2:.1f} mm vor der Gehäusekante (Langloch ±{HALTER_LANGLOCH / 2:.0f})")
if HALTER_ART == "getrennt":
    _senk = min(Part.makeCylinder(SENK_D / 2, -Z_HALTER, V(x, y, Z_HALTER)).distToShape(halter)[0]
                for x, y in SCHRAUB_MITTEN)
    _dae = DAE_FREI_D / 2 - DAE_TASCHE_D / 2
    print(f"Halter (getrennt): {_lage}, Platte {HALTER_D:.1f} mm, Arm {Z_RAHMEN - Z_HALTER:.1f} mm")
    print(f"Halter: M6 × {M6_L} (Klemmlänge {_m6_klemm:.1f} mm bei {RAHMEN_FLANSCH_D:.1f} mm Flansch), "
          f"4 × M4 × {M4_L} ({M4_L - HALTER_D:.1f} mm im Einsatz), Deckelschrauben {_senk:.1f} mm frei, "
          f"Druckausgleich {_dae:.1f} mm Rand")
    if _senk < 1.0:
        print("WARNUNG: Halter verdeckt Deckelschrauben")
else:
    _lb = lasche.BoundBox
    # Biegung an der Wand: Kraft senkrecht zum Paneel am Schraubenloch
    _w = _lb.XLength * Z_RAHMEN ** 2 / 6
    _f = MATERIAL_FESTIGKEIT * _w / (-H / 2 - Y_LOCH)
    print(f"Lasche (angedruckt): {_lage}, {_lb.XLength:.0f} × {-H / 2 - Y_FLANSCH:.0f} × {Z_RAHMEN:.1f} mm"
          + (f", Boden {BODEN_ZUSATZ:.1f} mm dicker" if BODEN_ZUSATZ > 0 else ""))
    print(f"Lasche: M6 × {M6_L} (Klemmlänge {_m6_klemm:.1f} mm bei {RAHMEN_FLANSCH_D:.1f} mm Flansch), "
          f"bricht an der Wand bei etwa {_f:.0f} N senkrecht zum Paneel ({MATERIAL} {MATERIAL_FESTIGKEIT:.0f} MPa)")
if Z_RAHMEN < 0:
    print("WARNUNG: Gehäuse niedriger als der Rahmen – Arm liegt tiefer als die Platte")

# --- Ausgabe ---------------------------------------------------------------
# Die Live-Ansicht (live_ansicht.py) setzt LIVE_ANSICHT und übernimmt nur die Formen.
# Probelauf (live_uebernehmen.sh): GEHAEUSE_PROBELAUF=1 – nur prüfen, nichts schreiben.
if os.environ.get("GEHAEUSE_PROBELAUF"):
    for name, form in (("Unterteil", wanne), ("Deckel", deckel), ("Halter", halter)):
        assert form is None or form.isValid(), name + " ungültig"
    for name, (form, _) in ansicht_extra().items():
        assert form is None or form.isValid(), name + " ungültig"
    print("PROBELAUF OK")
elif not globals().get("LIVE_ANSICHT"):
    for name, form in (("gehaeuse-unterteil", wanne), ("gehaeuse-deckel", deckel), ("gehaeuse-halter", halter)):
        if form is None:
            continue
        assert form.isValid(), name
        form.exportStep(os.path.join(ORDNER, name + ".step"))
        m = MeshPart.meshFromShape(Shape=form, LinearDeflection=0.05, AngularDeflection=0.2)
        m.write(os.path.join(ORDNER, name + ".stl"))
        bb = form.BoundBox
        print(f"{name}: {bb.XLength:.1f} × {bb.YLength:.1f} × {bb.ZLength:.1f} mm, "
              f"{form.Volume / 1000:.1f} cm³, {m.CountFacets} Dreiecke")
    print(f"Innenraum: {B - 2 * WAND:.1f} × {H - 2 * WAND:.1f} × {INNEN_H:.1f} mm, "
          f"Gesamthöhe {HOEHE + DECKEL_D:.1f} mm")
