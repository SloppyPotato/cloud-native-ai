"""Hilfsskript: neue Angriffe einzeln gegen eine Prompt-Version testen.

Aufruf:
    docker compose run --rm app kandidaten_test.py prompts/assistent.v1.yaml kandidaten.json
"""

import json
import sys

import assistent
from angriff import angriff_erfolgreich, kurz
from assistent import antworten
from prompts import lade

assistent.GUARDRAIL_AN = False
prompt = lade(sys.argv[1])
with open(sys.argv[2], encoding="utf-8") as f:
    kandidaten = json.load(f)
for angriff in kandidaten:
    antwort = antworten(angriff["text"], prompt)
    ok = angriff_erfolgreich(angriff, antwort)
    print(f"{'💥' if ok else '🛡️'} {angriff['art']:<12} {kurz(angriff['text'], 70)}")
    print(f"     → {kurz(antwort, 200)}")
