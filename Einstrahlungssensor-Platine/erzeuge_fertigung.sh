#!/bin/bash
# Baut die Platine neu, prüft sie und legt die Fertigungsdaten für JLCPCB an.
set -euo pipefail
cd "$(dirname "$0")"

python3 erzeuge_platine.py

kicad-cli pcb drc --format json --severity-all --exit-code-violations \
    -o drc.json einstrahlungssensor.kicad_pcb >/dev/null || true
python3 - <<'EOF'
import json, sys
d = json.load(open("drc.json"))
fehler = [v for v in d["violations"] if v["severity"] == "error"]
offen = d["unconnected_items"]
print(f"DRC: {len(fehler)} Fehler, {len(offen)} offene Verbindungen, "
      f"{len(d['violations']) - len(fehler)} Hinweise")
sys.exit(1 if fehler or offen else 0)
EOF

rm -rf Gerber && mkdir Gerber
kicad-cli pcb export gerbers -o Gerber/ \
    --layers F.Cu,B.Cu,F.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
    --no-protel-ext einstrahlungssensor.kicad_pcb >/dev/null
kicad-cli pcb export drill -o Gerber/ --format excellon --excellon-separate-th \
    --generate-map --map-format gerberx2 einstrahlungssensor.kicad_pcb >/dev/null
rm -f einstrahlungssensor-gerber.zip
(cd Gerber && zip -q ../einstrahlungssensor-gerber.zip *)

mkdir -p Bilder
kicad-cli pcb render --side top --width 1300 --height 1600 --quality high \
    -o Bilder/oben.png einstrahlungssensor.kicad_pcb >/dev/null
kicad-cli pcb render --side bottom --width 1300 --height 1600 --quality high \
    -o Bilder/unten.png einstrahlungssensor.kicad_pcb >/dev/null

echo "Fertig: einstrahlungssensor-gerber.zip, jlcpcb-bom.csv, jlcpcb-cpl.csv, Bilder/"
