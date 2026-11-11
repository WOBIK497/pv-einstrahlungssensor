"""Bildflächen der Gehäuse-Dateien (*.FCStd) beim Öffnen mit ihren Texturen belegen.

FreeCAD 1.1 speichert ein Bild im Material eines Part-Objekts zwar mit, zeichnet es aber
nicht. Deshalb trägt jede Datei ein unsichtbares Hilfsobjekt „Texturen“: Es enthält die
PNG-Bilder (eingebettet) und eine Zuordnung Objektname → Bild, Breite, Höhe. Nach dem
Laden legt es die Bilder wie die Live-Ansicht als Coin-Textur auf das Rechteck
(0, 0)–(Breite, Höhe) in den lokalen Koordinaten des Objekts; Bild-oben = +y.

Einrichten: Diese Datei muss für FreeCAD importierbar sein, z. B. als Verknüpfung in
<Benutzerdaten>/Mod/PV-Texturen/pv_textur.py (Snap: ~/snap/freecad/common/Mod/…).
Fehlt sie, öffnet FreeCAD die Datei trotzdem – die Bildflächen bleiben dann grau.
"""
import json

import FreeCAD as App


class Texturen:
    """Proxy des Hilfsobjekts (App::FeaturePython)."""

    def __init__(self, obj):
        obj.Proxy = self

    def dumps(self):
        return None

    def loads(self, state):
        return None

    def execute(self, obj):
        pass

    def onDocumentRestored(self, obj):
        if App.GuiUp:
            from PySide import QtCore
            QtCore.QTimer.singleShot(0, lambda: anwenden(obj))


def anlegen(doc, zuordnung):
    """Hilfsobjekt anlegen. zuordnung: {Objektname: (Bilddatei, Breite, Höhe)}."""
    obj = doc.addObject("App::FeaturePython", "Texturen")
    Texturen(obj)
    obj.addProperty("App::PropertyString", "Zuordnung", "Texturen",
                    "JSON: Objektname -> [Bildeigenschaft, Breite, Höhe]")
    bilder, eintraege = {}, {}
    for name, (datei, breite, hoehe) in zuordnung.items():
        if datei not in bilder:
            prop = f"Bild{len(bilder) + 1}"
            obj.addProperty("App::PropertyFileIncluded", prop, "Texturen", datei.rsplit("/", 1)[-1])
            setattr(obj, prop, datei)
            bilder[datei] = prop
        eintraege[name] = [bilder[datei], breite, hoehe]
    obj.Zuordnung = json.dumps(eintraege, ensure_ascii=False)
    if App.GuiUp:
        anwenden(obj)
    return obj


def anwenden(obj):
    """Texturen auf die zugeordneten Objekte legen (nur mit Oberfläche)."""
    from pivy import coin
    from PySide import QtGui
    doc = obj.Document
    for name, (prop, breite, hoehe) in json.loads(obj.Zuordnung).items():
        ziel = doc.getObject(name)
        if ziel is None or ziel.ViewObject is None:
            App.Console.PrintWarning(f"Texturen: {name} fehlt\n")
            continue
        img = QtGui.QImage(getattr(obj, prop))
        if img.isNull():
            App.Console.PrintWarning(f"Texturen: Bild für {name} nicht lesbar\n")
            continue
        img = img.convertToFormat(QtGui.QImage.Format_RGBA8888).mirrored(False, True)
        w, h = img.width(), img.height()
        root = ziel.ViewObject.RootNode
        for i in reversed(range(root.getNumChildren())):
            if root.getChild(i).getName().getString().startswith("LiveTextur"):
                root.removeChild(i)
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
