"""Mehrere Prompt-Versionen auf denselben Test-Mails vergleichen.

Aufruf:
    docker compose run --rm app vergleich.py prompts/einordnen.v1.yaml prompts/einordnen.v2.yaml

Für jede Version zählt das Skript, wie viele Anliegen und wie viele
komplette Einordnungen stimmen, und misst Eingabe-Tokens und Dauer.
So seht ihr, was eine Änderung am Prompt bringt und was sie kostet.
"""

import json
import sys

from einordnen import einordnen, felder_richtig
from llm import MODEL
from prompts import lade


def vergleiche(pfade: list[str]) -> None:
    with open("mails.json", encoding="utf-8") as f:
        faelle = json.load(f)
    n = len(faelle)
    zeilen = []
    for pfad in pfade:
        prompt = lade(pfad)
        print(f"\n{prompt.kennung}: {prompt.beschreibung}")
        protokoll: list = []
        anliegen_ok = alles_ok = 0
        for fall in faelle:
            ergebnis = einordnen(fall["mail"], prompt, protokoll=protokoll)
            ok = felder_richtig(ergebnis, fall["erwartet"])
            anliegen_ok += ok["anliegen"]
            alles_ok += all(ok.values())
            if not all(ok.values()):
                falsch = ", ".join(k for k, v in ok.items() if not v)
                print(f"  ✗ {falsch:<22} {fall['mail'][:55]}")
                print(f"      erhalten:  {ergebnis.model_dump()}")
                print(f"      erwartet:  {fall['erwartet']}")
        tokens = sum(t for t, _ in protokoll) / len(protokoll)
        sekunden = sum(s for _, s in protokoll) / len(protokoll)
        zeilen.append((prompt.kennung, anliegen_ok, alles_ok, tokens, sekunden))

    print(f"\nModell: {MODEL}, {n} Test-Mails\n")
    print("| Prompt | Anliegen richtig | Alle Felder richtig | Eingabe-Tokens (Ø) | Dauer (Ø) |")
    print("|---|---|---|---|---|")
    for kennung, a, alle, t, s in zeilen:
        print(f"| {kennung} | {a}/{n} | {alle}/{n} | {t:.0f} | {s:.2f} s |")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Bitte mindestens eine Prompt-Datei angeben.")
    vergleiche(sys.argv[1:])
