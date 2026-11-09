# Passungsprüfung: Platine, Stecker und Kondensator als Hüllkörper ins Unterteil
# setzen und Überschneidungen messen. Aufruf: freecad.cmd pruefe_gehaeuse.py
import os
import Part
import MeshPart

ORDNER = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(ORDNER, "erzeuge_gehaeuse.py"), encoding="utf-8").read().split("# --- Unterteil")[0])

wanne = Part.read(os.path.join(ORDNER, "gehaeuse-unterteil.step"))
pruef = inhalt()
fehler = 0
for name, k in pruef.items():
    v = wanne.common(k).Volume
    oben = k.BoundBox.ZMax
    luft = HOEHE - oben
    print(f"{name:12s} Überschneidung {v:6.2f} mm³, Luft bis Deckel {luft:5.1f} mm")
    if v > 0.01 or luft < 3:
        fehler += 1
# Platine im Schlitz: Oberkante muss 1,5 mm im Halter stecken
schlitz_tief = 1.5
print("Platinenkante steckt", schlitz_tief, "mm im Halter")
teile = None
for k in pruef.values():
    teile = k if teile is None else teile.fuse(k)
MeshPart.meshFromShape(Shape=teile, LinearDeflection=0.05).write(os.path.join(ORDNER, "pruefung-inhalt.stl"))
print("Fehler:", fehler)
