"""Teil 4.3: Wie wirkt sich k (Zahl der Abschnitte) bei RAG aus?

Aufruf:
    docker compose run --rm app k_vergleich.py 1 4 8
"""

import json
import sys

import rag
from vergleich_wissen import antwort_richtig
from wissen import antworten

with open("fragen.json", encoding="utf-8") as f:
    faelle = json.load(f)

print("| k | Kontext richtig | Antwort richtig | Eingabe-Tokens (Ø) | Dauer (Ø) |")
print("|---|---|---|---|---|")
for k in [int(a) for a in sys.argv[1:]]:
    kontext = richtig = tokens = 0
    sekunden = 0.0
    falsch = []
    for fall in faelle:
        treffer, sek_suche = rag.abrufen(fall["frage"], k)
        a = antworten(fall["frage"], treffer, sek_suche)
        kontext += fall["quelle"] in a.quellen
        ok = antwort_richtig(a.text, fall)
        richtig += ok
        tokens += a.eingabe_tokens
        sekunden += a.sekunden_suche + a.sekunden_antwort
        if not ok:
            falsch.append(fall["frage"][:40])
    n = len(faelle)
    mit_quelle = sum(1 for f in faelle if f["quelle"])
    print(f"| {k} | {kontext}/{mit_quelle} | {richtig}/{n} | {tokens / n:.0f} | {sekunden / n:.1f} s |", flush=True)
    print(f"  falsch: {falsch}", file=sys.stderr, flush=True)
