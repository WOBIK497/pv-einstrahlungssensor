#!/bin/bash
# Übernimmt Live-Ansicht/arbeitskopie.py nach erzeuge_gehaeuse.py – aber nur,
# wenn ein Probelauf in FreeCAD (headless) fehlerfrei durchläuft. Der Austausch
# geschieht in einem Schritt (mv), die Live-Ansicht sieht nie einen Zwischenstand.
# Aufruf ohne Argumente; Ausgabe des Probelaufs ohne FreeCAD-Fortschrittsrauschen.
set -u
ORDNER="$(cd "$(dirname "$0")" && pwd)"
KOPIE="$ORDNER/Live-Ansicht/arbeitskopie.py"
ZIEL="$ORDNER/erzeuge_gehaeuse.py"

[ -f "$KOPIE" ] || { echo "Keine Arbeitskopie: $KOPIE"; exit 2; }
if cmp -s "$KOPIE" "$ZIEL"; then echo "Arbeitskopie unverändert – nichts zu tun."; exit 0; fi

ausgabe="$(GEHAEUSE_PROBELAUF=1 /snap/bin/freecad.cmd "$KOPIE" 2>&1 | tr '\r' '\n' \
           | grep -v -e '^\s*$' -e '([0-9]* %)' -e '^FreeCAD ' -e '^(C) ' -e 'LGPL2' -e '^saving' -e "snap-specific PYTHONPATH")"
echo "$ausgabe"
# Erfolg nur, wenn die Bestätigung kam UND nirgends eine Ausnahme steht –
# Code hinter der Bestätigung kann noch scheitern.
if ! grep -q "PROBELAUF OK" <<<"$ausgabe" \
   || grep -q -e "Exception while processing" -e "Traceback" -e "Error:" <<<"$ausgabe"; then
    echo "→ Probelauf fehlgeschlagen, erzeuge_gehaeuse.py bleibt unverändert."
    exit 1
fi
cp "$KOPIE" "$ZIEL.neu" && mv "$ZIEL.neu" "$ZIEL"
echo "→ übernommen, Live-Ansicht baut in etwa 3 s neu."
