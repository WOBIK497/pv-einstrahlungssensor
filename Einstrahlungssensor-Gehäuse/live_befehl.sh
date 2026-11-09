#!/bin/bash
# Schickt Python-Code an die laufende Live-Ansicht in FreeCAD (live_ansicht.py)
# und gibt deren Antwort aus.
#
#   live_befehl.sh datei.py        Code aus einer Datei
#   live_befehl.sh <<'EOF'         Code von der Standardeingabe
#   print(EXPLOSION)
#   EOF
#
# Rückgabe: 0 = ok, 1 = Fehler im Code (Traceback steht in der Ausgabe),
# 2 = keine Antwort (FreeCAD läuft nicht oder das Makro ist nicht geladen).
# Wartezeit in Sekunden über LIVE_WARTEN (Vorgabe 30).
set -u
LIVE="$(dirname "$(readlink -f "$0")")/Live-Ansicht"
WARTEN="${LIVE_WARTEN:-30}"

rm -f "$LIVE/antwort.txt"
if [ $# -gt 0 ]; then cat -- "$1"; else cat; fi > "$LIVE/befehl.py.neu"
# erst vollständig schreiben, dann umbenennen – das Makro liest nie eine halbe Datei
mv "$LIVE/befehl.py.neu" "$LIVE/befehl.py"

for ((i = 0; i < WARTEN * 10; i++)); do
    if [ -s "$LIVE/antwort.txt" ]; then
        sleep 0.2
        cat "$LIVE/antwort.txt"
        if head -n 1 "$LIVE/antwort.txt" | grep -q ' FEHLER$'; then exit 1; fi
        exit 0
    fi
    sleep 0.1
done
echo "Keine Antwort nach $WARTEN s – läuft FreeCAD mit live_ansicht.py?" >&2
exit 2
