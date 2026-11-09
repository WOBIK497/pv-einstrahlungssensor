#!/usr/bin/env python3
"""Erzeugt die Platine des PV-Einstrahlungssensors (KiCad 9, pcbnew-API).

Aufruf:  python3 erzeuge_platine.py
Ergebnis: einstrahlungssensor.kicad_pcb sowie BOM/CPL für JLCPCB im selben Ordner.

Koordinaten in mm, Ursprung oben links bei (100, 100), y wächst nach unten.
"""
import csv
import os
import pcbnew

HIER = os.path.dirname(os.path.abspath(__file__))
FP = "/usr/share/kicad/footprints/"
MM = pcbnew.FromMM

# Platinenumriss
X0, Y0, X1, Y1 = 100.0, 100.0, 138.0, 146.0
ANT_Y = 103.9          # kupferfreier Streifen für die Antenne: Y0 … ANT_Y

board = pcbnew.BOARD()
ds = board.GetDesignSettings()
ds.SetCopperLayerCount(2)
ds.m_TrackMinWidth = MM(0.2)
ds.m_ViasMinSize = MM(0.6)
ds.m_MinThroughDrill = MM(0.3)
ds.m_CopperEdgeClearance = MM(0.3)
nc = ds.m_NetSettings.GetDefaultNetclass()
nc.SetClearance(MM(0.2))
nc.SetTrackWidth(MM(0.25))
nc.SetViaDiameter(MM(0.6))
nc.SetViaDrill(MM(0.3))

# ---------------------------------------------------------------- Netze
NETZE = {}
def net(name):
    if name not in NETZE:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        NETZE[name] = n
    return NETZE[name]

# ---------------------------------------------------------------- Bauteile
TEILE = {}   # ref -> dict(fp, wert, lcsc, smd)
def teil(ref, lib, name, x, y, rot, wert, lcsc=None, pads=None, bestuecken=True):
    fp = pcbnew.FootprintLoad(FP + lib + ".pretty", name)
    assert fp is not None, (lib, name)
    fp.SetReference(ref)
    fp.SetValue(wert)
    fp.SetPosition(pcbnew.VECTOR2I_MM(x, y))
    fp.SetOrientationDegrees(rot)
    board.Add(fp)
    if not bestuecken:
        fp.SetAttributes(fp.GetAttributes()
                         | pcbnew.FP_EXCLUDE_FROM_POS_FILES
                         | pcbnew.FP_EXCLUDE_FROM_BOM)
    for nummer, netzname in (pads or {}).items():
        for p in fp.Pads():
            if p.GetNumber() == str(nummer):
                p.SetNet(net(netzname))
    # Bauteilbezeichnung nur bei Steckverbindern drucken, sonst überlappt der Druck
    if ref not in ("J4", "J5"):
        fp.Reference().SetVisible(False)
    TEILE[ref] = dict(fp=fp, wert=wert, lcsc=lcsc, name=name, bestuecken=bestuecken)
    return fp

def P(ref, nummer):
    """Mittelpunkt eines Pads in mm."""
    for p in TEILE[ref]["fp"].Pads():
        if p.GetNumber() == str(nummer):
            v = p.GetPosition()
            return (pcbnew.ToMM(v.x), pcbnew.ToMM(v.y))
    raise KeyError((ref, nummer))

R0603 = ("Resistor_SMD", "R_0603_1608Metric")
C0603 = ("Capacitor_SMD", "C_0603_1608Metric")
C0805 = ("Capacitor_SMD", "C_0805_2012Metric")
R2512 = ("Resistor_SMD", "R_2512_6332Metric")
SOT23 = ("Package_TO_SOT_SMD", "SOT-23")
HDR2 = ("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical")
# Buchse für die Stecker der Solarmodule (ZH 1,5 mm, 2-polig, stehend). Seit 09.11.2026 lötet
# USER J1–J3 selbst (HC-ZH1.5-2A, LCSC C2845550) – nicht in BOM/CPL für JLC.
ZH2 = ("Connector_JST", "JST_ZH_B2B-ZR_1x02_P1.50mm_Vertical")
HDR6 = ("Connector_PinHeader_2.54mm", "PinHeader_1x06_P2.54mm_Vertical")

# Funkmodul (wird von Hand aufgelötet)
teil("U3", "RF_Module", "Raytac_MDBT42Q", 119.0, 108.0, 0, "MDBT42Q (Espruino)",
     pads={1: "GND", 12: "GND", 24: "GND", 39: "GND", 11: "+3V3",
           7: "DIV", 8: "SENSE", 13: "BTN", 14: "LEDSIG",
           36: "SWDCLK", 37: "SWDIO", 21: "RX", 19: "TX"},
     bestuecken=False)
# Die Innenpads 40/41 (P0.24/P0.23) werden nicht gebraucht und liegen in der
# Sperrfläche des Footprints selbst: entfernen, das Modul liegt dort auf Lötstopplack.
for p in list(TEILE["U3"]["fp"].Pads()):
    if p.GetNumber() in ("40", "41"):
        TEILE["U3"]["fp"].Remove(p)

# Messung (links)
teil("R1", *R2512, 107.0, 125.0, 90, "10R 1% 2W", "C414890", {1: "GND", 2: "PV_M"})
teil("R3", *R0603, 111.6, 118.0, 90, "10k", "C25804", {1: "PV_M", 2: "SENSE"})
teil("C8", *C0603, 110.0, 114.6, 90, "100nF", "C14663", {1: "GND", 2: "SENSE"})
teil("C9", *C0603, 107.0, 112.4, 90, "100nF", "C14663", {1: "GND", 2: "DIV"})
teil("C7", *C0603, 112.6, 115.0, 90, "100nF", "C14663", {1: "GND", 2: "+3V3"})
teil("J2", *ZH2, 103.0, 124.0, 270, "HC-ZH1.5-2A", "C2845550", {1: "PV_M", 2: "GND"}, bestuecken=False)

# LED und Taster-Kontakt
teil("R6", *R0603, 117.6, 119.0, 90, "1k", "C21190", {1: "LEDA", 2: "LEDSIG"})
teil("D2", "LED_SMD", "LED_0603_1608Metric", 117.6, 122.0, 90, "LED rot", "C2286",
     {1: "GND", 2: "LEDA"})
teil("J5", *HDR2, 114.8, 120.0, 0, "BTN", pads={1: "BTN", 2: "+3V3"}, bestuecken=False)

# Versorgung (unten)
teil("J1", *ZH2, 114.0, 142.5, 0, "HC-ZH1.5-2A", "C2845550", {1: "PV_V", 2: "GND"}, bestuecken=False)
teil("R2", *R2512, 114.0, 136.0, 90, "10R 1% 2W", "C414890", {1: "PV_V", 2: "PV_R"})
teil("C1", *C0805, 110.4, 132.6, 90, "10uF 25V", "C15850", {1: "GND", 2: "PV_R"})
teil("U1", *SOT23, 117.6, 130.2, 0, "HT7550-1", "C5379082", {1: "GND", 2: "PV_R", 3: "+5V"})
teil("C2", *C0805, 118.6, 134.0, 0, "10uF 25V", "C15850", {1: "GND", 2: "+5V"})
teil("D1", "Diode_SMD", "D_SOD-323", 122.2, 130.2, 180, "B5819WS", "C7420331",
     {1: "VCAP", 2: "+5V"})
teil("C3", *C0805, 125.2, 132.6, 90, "22uF 25V", "C45783", {1: "GND", 2: "VCAP"})
teil("C4", *C0805, 127.2, 132.6, 90, "22uF 25V", "C45783", {1: "GND", 2: "VCAP"})
# Superkondensator steckbar: dieselbe ZH-Buchse wie J1/J2, am Kondensator ein
# fertig gecrimptes ZH-Kabel anlöten
teil("J3", *ZH2, 124.0, 142.5, 0, "HC-ZH1.5-2A", "C2845550", {1: "VCAP", 2: "GND"}, bestuecken=False)
teil("R5", *R0603, 124.0, 127.4, 0, "1M", "C22935", {1: "GND", 2: "DIV"})
teil("R4", *R0603, 127.0, 127.4, 0, "1M", "C22935", {1: "DIV", 2: "VCAP"})
teil("U2", *SOT23, 131.5, 131.0, 180, "XC6206P332MR", "C5446", {1: "GND", 2: "+3V3", 3: "VCAP"})
teil("C6", *C0805, 134.6, 129.6, 90, "10uF 25V", "C15850", {1: "GND", 2: "+3V3"})

# Programmier- und Notfallleiste (rechts)
teil("J4", *HDR6, 134.5, 106.0, 0, "Debug", pads={1: "GND", 2: "+3V3", 3: "SWDIO",
     4: "SWDCLK", 5: "RX", 6: "TX"}, bestuecken=False)
teil("R7", *R0603, 130.0, 115.4, 90, "1M", "C22935", {1: "RX", 2: "GND"})

# Befestigungslöcher
teil("H1", "MountingHole", "MountingHole_3.2mm_M3", 103.5, 142.5, 0, "M3", bestuecken=False)
teil("H2", "MountingHole", "MountingHole_3.2mm_M3", 134.5, 142.5, 0, "M3", bestuecken=False)

# ---------------------------------------------------------------- Leiterbahnen
def bahn(netz, punkte, breite=0.25, lage=pcbnew.F_Cu):
    for (xa, ya), (xb, yb) in zip(punkte, punkte[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I_MM(xa, ya))
        t.SetEnd(pcbnew.VECTOR2I_MM(xb, yb))
        t.SetWidth(MM(breite))
        t.SetLayer(lage)
        t.SetNet(net(netz))
        board.Add(t)

def via(netz, x, y):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I_MM(x, y))
    v.SetDrill(MM(0.3))
    v.SetWidth(MM(0.6))
    v.SetNet(net(netz))
    board.Add(v)

B = pcbnew.B_Cu
LEIST = 0.5   # Bahnbreite für Leistungsnetze

# Messung: PV_M -> Shunt R1 -> Filter R3/C8 -> P0.31
bahn("PV_M", [P("J2", 1), (103.0, 121.0), (111.6, 121.0), P("R3", 1)], LEIST)
bahn("PV_M", [(107.0, 121.0), P("R1", 2)], LEIST)
via("GND", 107.0, 130.2); bahn("GND", [P("R1", 1), (107.0, 130.2)], LEIST)
bahn("SENSE", [P("R3", 2), (111.6, 111.4), P("U3", 8)])
bahn("SENSE", [(111.6, P("C8", 2)[1]), P("C8", 2)])
via("GND", 110.0, 116.8); bahn("GND", [P("C8", 1), (110.0, 116.8)])

# Spannungsteiler: Mittelpunkt DIV über B.Cu zum Modul (P0.30)
bahn("DIV", [P("R5", 2), P("R4", 1)])
via("DIV", 125.5, 126.0); bahn("DIV", [(125.5, 127.4), (125.5, 126.0)])
bahn("DIV", [(125.5, 126.0), (109.0, 126.0), (109.0, 110.0)], lage=B)
via("DIV", 109.0, 110.0)
bahn("DIV", [(109.0, 110.0), (109.0, 110.7), P("U3", 7)])
bahn("DIV", [(109.0, 110.7), (107.0, 110.7), P("C9", 2)])
via("GND", 107.0, 114.6); bahn("GND", [P("C9", 1), (107.0, 114.6)])
via("GND", 123.2, 128.7); bahn("GND", [P("R5", 1), (123.2, 128.7)])
bahn("VCAP", [P("R4", 2), (128.8, 127.4), (128.8, 131.0)])

# 3,3 V am Modul
bahn("+3V3", [P("U3", 11), (112.9, 113.5), P("C7", 2)])
bahn("+3V3", [(112.9, 113.5), (112.9, 112.4)])
via("+3V3", 112.9, 112.4)
bahn("GND", [P("C7", 1), (P("U3", 12)[0], P("C7", 1)[1]), P("U3", 12)])
via("GND", 113.6, 117.2); bahn("GND", [P("C7", 1), (113.6, 117.2)])
via("GND", 112.6, 104.4); bahn("GND", [P("U3", 1), (112.6, 104.4)])
via("GND", 125.0, 104.3); bahn("GND", [P("U3", 39), (125.0, 104.3)])
via("GND", 123.2, 116.75); bahn("GND", [P("U3", 24), (123.2, 116.75)])

# LED und Taster
bahn("LEDSIG", [P("U3", 14), (P("U3", 14)[0], 116.8), (117.6, 116.8), P("R6", 2)])
bahn("LEDA", [P("R6", 1), P("D2", 2)])
via("GND", 117.6, 123.6); bahn("GND", [P("D2", 1), (117.6, 123.6)])
bahn("BTN", [P("U3", 13), (P("U3", 13)[0], 118.5), (114.8, 119.2), P("J5", 1)])

# Versorgung
bahn("PV_V", [P("J1", 1), P("R2", 1)], LEIST)
bahn("PV_R", [P("R2", 2), (114.0, 131.95), P("U1", 2)], LEIST)
bahn("PV_R", [(114.0, 131.95), (110.4, 131.95), P("C1", 2)], LEIST)
via("GND", 110.4, 135.2); bahn("GND", [P("C1", 1), (110.4, 135.2)], LEIST)
via("GND", 116.66, 127.9); bahn("GND", [P("U1", 1), (116.66, 127.9)], LEIST)
bahn("+5V", [P("U1", 3), (120.2, 130.2), P("D1", 2)], LEIST)
bahn("+5V", [(120.2, 130.2), (120.2, 134.0), P("C2", 2)], LEIST)
via("GND", 117.65, 135.7); bahn("GND", [P("C2", 1), (117.65, 135.7)], LEIST)
bahn("VCAP", [P("D1", 1), (124.0, 131.0), P("U2", 3)], LEIST)
bahn("VCAP", [(124.0, 131.0), P("J3", 1)], LEIST)
bahn("VCAP", [(125.2, 131.0), P("C3", 2)], LEIST)
bahn("VCAP", [(127.2, 131.0), P("C4", 2)], LEIST)
via("GND", 125.2, 135.2); bahn("GND", [P("C3", 1), (125.2, 135.2)], LEIST)
via("GND", 127.2, 135.2); bahn("GND", [P("C4", 1), (127.2, 135.2)], LEIST)
via("GND", 132.44, 133.3); bahn("GND", [P("U2", 1), (132.44, 133.3)], LEIST)
bahn("+3V3", [P("U2", 2), (132.44, 128.65), P("C6", 2)], LEIST)
via("GND", 134.6, 132.2); bahn("GND", [P("C6", 1), (134.6, 132.2)], LEIST)
via("+3V3", 132.44, 127.4); bahn("+3V3", [(132.44, 128.65), (132.44, 127.4)])
bahn("+3V3", [(132.44, 127.4), (132.44, 124.5), (112.9, 124.5), (112.9, 112.4)], lage=B)
bahn("+3V3", [(132.44, 124.5), (136.6, 124.5), (136.6, 108.54), P("J4", 2)], lage=B)
bahn("+3V3", [P("J5", 2), (114.8, 124.5)], lage=B)

# Programmierleiste
bahn("SWDIO", [P("U3", 37), (127.0, 105.8), (127.0, P("J4", 3)[1]), P("J4", 3)])
bahn("SWDCLK", [P("U3", 36), (126.2, 106.5), (126.2, P("J4", 4)[1]), P("J4", 4)])
bahn("RX", [P("U3", 21), (P("U3", 21)[0], 117.6), (132.9, 117.6),
            (132.9, P("J4", 5)[1]), P("J4", 5)])
bahn("RX", [(130.0, 117.6), P("R7", 1)])
via("GND", 128.6, 114.6); bahn("GND", [P("R7", 2), (128.6, 114.6)])
bahn("TX", [P("U3", 19), (P("U3", 19)[0], 118.7), (P("J4", 6)[0], 118.7)])

# ---------------------------------------------------------------- Umriss, Zonen
def rechteck(lage, x0, y0, x1, y1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_RECT)
    s.SetStart(pcbnew.VECTOR2I_MM(x0, y0))
    s.SetEnd(pcbnew.VECTOR2I_MM(x1, y1))
    s.SetLayer(lage)
    s.SetWidth(MM(0.1))
    board.Add(s)

rechteck(pcbnew.Edge_Cuts, X0, Y0, X1, Y1)

def zone(punkte, lagen, netz=None, regel=False, kein_kupfer=True, keine_bahnen=False,
         keine_vias=False):
    z = pcbnew.ZONE(board)
    ls = pcbnew.LSET()
    for l in lagen:
        ls.AddLayer(l)
    z.SetLayerSet(ls)
    if regel:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowCopperPour(kein_kupfer)
        z.SetDoNotAllowTracks(keine_bahnen)
        z.SetDoNotAllowVias(keine_vias)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
    else:
        z.SetNet(net(netz))
        z.SetLocalClearance(MM(0.25))
        z.SetMinThickness(MM(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in punkte:
        ol.Append(MM(x), MM(y))
    board.Add(z)
    return z

flaeche = [(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)]
zone(flaeche, [pcbnew.F_Cu], "GND")
zone(flaeche, [pcbnew.B_Cu], "GND")
# Antennenstreifen: kein Kupfer, keine Bahnen, keine Vias auf beiden Lagen
zone([(X0, Y0), (X1, Y0), (X1, ANT_Y), (X0, ANT_Y)], [pcbnew.F_Cu, pcbnew.B_Cu],
     regel=True, keine_bahnen=True, keine_vias=True)
# Unter dem Modul auf F.Cu keine Kupferfläche
zone([(115.2, ANT_Y), (121.2, ANT_Y), (121.2, 114.6), (115.2, 114.6)], [pcbnew.F_Cu],
     regel=True, keine_bahnen=True)

# Massedurchkontaktierungen zwischen den Lagen
for x, y in [(101.5, 106.0), (101.5, 116.0), (101.5, 133.0), (108.0, 140.0),
             (119.5, 140.0), (130.0, 140.0), (136.8, 134.0), (136.8, 138.0),
             (129.5, 107.0), (129.5, 109.5), (104.0, 118.0)]:
    via("GND", x, y)

# ---------------------------------------------------------------- Beschriftung
def text(t, x, y, groesse=0.9, lage=pcbnew.F_SilkS, rot=0):
    tx = pcbnew.PCB_TEXT(board)
    tx.SetText(t)
    tx.SetPosition(pcbnew.VECTOR2I_MM(x, y))
    tx.SetTextSize(pcbnew.VECTOR2I_MM(groesse, groesse))
    tx.SetTextThickness(MM(groesse * 0.15))
    tx.SetLayer(lage)
    tx.SetTextAngleDegrees(rot)
    if lage == pcbnew.B_SilkS:
        tx.SetMirrored(True)
    board.Add(tx)

# Eckiges Pad = Pin 1 = Plus bei allen zweipoligen Anschlüssen
text("PV-V", 108.6, 142.5); text("+", 111.2, 142.5); text("-", 118.3, 142.5)
text("Superkond.", 124.75, 139.3); text("+", 121.2, 142.5); text("-", 128.3, 142.5)
text("PV-M +/-", 105.0, 119.9)
text("BTN", 116.9, 120.0, 0.8, rot=90)
for i, name in enumerate(["GND", "3V3", "DIO", "CLK", "RX", "TX"]):
    text(name, 131.6, 106.0 + 2.54 * i, 0.8)
text("PV-Einstrahlungssensor v1", 119.0, 138.0, 1.2, pcbnew.B_SilkS)
text("MDBT42Q + Espruino", 119.0, 111.0, 1.0, pcbnew.B_SilkS)
text("Antenne", 106.0, 102.0, 0.8)

# ---------------------------------------------------------------- Füllen, Speichern
ziel = os.path.join(HIER, "einstrahlungssensor.kicad_pcb")
board.SetFileName(ziel)
pcbnew.SaveBoard(ziel, board)
# Füllen klappt nur auf einer geladenen Platine (auf der frisch erzeugten stürzt es ab)
geladen = pcbnew.LoadBoard(ziel)
pcbnew.ZONE_FILLER(geladen).Fill(geladen.Zones())
pcbnew.SaveBoard(ziel, geladen)

# ---------------------------------------------------------------- BOM und CPL für JLCPCB
# JLCs Bauteilmodelle liegen bei manchen Gehäusen anders gedreht als die KiCad-Footprints.
# Am 09.11.2026 im PCBA-Viewer geprüft: SOT-23 (U1, U2) und SOD-323 (D1) lagen um 180°
# verkehrt, LED 0603 (D2) stimmte.
JLC_DREHKORREKTUR = {"SOT-23": 180, "D_SOD-323": 180}
bom = {}
with open(os.path.join(HIER, "jlcpcb-cpl.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for ref, t in sorted(TEILE.items()):
        if not t["bestuecken"]:
            continue
        fp = t["fp"]
        pos = fp.GetPosition()
        drehung = fp.GetOrientationDegrees() + JLC_DREHKORREKTUR.get(t["name"], 0)
        # Gleicher Nullpunkt wie die Gerber-Dateien (absolute KiCad-Koordinaten, y nach oben)
        w.writerow([ref, f"{pcbnew.ToMM(pos.x):.3f}mm", f"{-pcbnew.ToMM(pos.y):.3f}mm",
                    "Top", f"{drehung % 360:.0f}"])
        key = (t["wert"], t["name"], t["lcsc"])
        bom.setdefault(key, []).append(ref)
with open(os.path.join(HIER, "jlcpcb-bom.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for (wert, name, lcsc), refs in sorted(bom.items(), key=lambda kv: kv[1][0]):
        w.writerow([wert, ",".join(sorted(refs)), name, lcsc])
print("gespeichert:", ziel)
