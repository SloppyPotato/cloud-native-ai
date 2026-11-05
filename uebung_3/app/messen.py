"""Den Agenten auf festen Aufgaben messen.

Aufruf:
    docker compose run --rm app messen.py                         # agent.v1
    docker compose run --rm app messen.py prompts/agent.v1.yaml prompts/agent.v2.yaml
    docker compose run --rm app messen.py workflow prompts/agent.v1.yaml
    docker compose run --rm app messen.py --zeigen prompts/agent.v1.yaml

Jede Variante ist entweder eine Prompt-Datei (dann läuft der Agent) oder
das Wort "workflow" (dann läuft der feste Routing-Workflow aus workflow.py).

Gemessen wird, was Huyen (AI Engineering, Kap. 6) für Agenten vorschlägt:
  - Antwort richtig: enthält die Antwort einen der erwarteten Begriffe?
  - Werkzeuge richtig: wurden die nötigen Werkzeuge benutzt?
  - ungültige Aufrufe: Werkzeug gibt es nicht oder Argumente passen nicht
  - Fehlerergebnisse: gültiger Aufruf, aber das Werkzeug meldet einen Fehler
    (meist ein falscher Wert, etwa datum="heute")
  - Effizienz: Werkzeugaufrufe, Modellaufrufe, Tokens und Dauer pro Aufgabe

Schreibende Werkzeuge werden beim Messen automatisch bestätigt.
"""

import argparse
import json
import os

import httpx
from dataclasses import dataclass

from agent import Ergebnis, agent, alle_werkzeuge, zeige_schritt
from llm import MODEL
from prompts import lade

AUFGABEN = "aufgaben.json"


@dataclass
class Messung:
    typ: str
    richtig: bool
    werkzeuge_ok: bool
    ergebnis: Ergebnis


def pruefen(antwort: str, erwartet: list[str]) -> bool:
    return any(e.lower() in antwort.lower() for e in erwartet)


def ausfuehren(variante: str, aufgabe: str, werkzeuge) -> Ergebnis:
    if variante == "workflow":
        from workflow import workflow
        return workflow(aufgabe, werkzeuge)
    return agent(aufgabe, werkzeuge, lade(variante), bestaetigen=lambda *_: True)


def buchungen_zuruecksetzen() -> None:
    """Jede Variante startet mit derselben Raumbelegung, ohne alte Buchungen."""
    url = os.environ.get("MCP_URL", "http://campus-mcp:8000/mcp").removesuffix("/mcp") + "/zuruecksetzen"
    try:
        httpx.post(url, timeout=5)
    except httpx.HTTPError:
        print(f"  Hinweis: {url} nicht erreichbar, Buchungen wurden nicht zurückgesetzt.")


def messen(variante: str, aufgaben: list[dict], werkzeuge, zeigen: bool) -> list[Messung]:
    print(f"\n=== {variante} · {MODEL}", flush=True)
    buchungen_zuruecksetzen()
    messungen = []
    for a in aufgaben:
        e = ausfuehren(variante, a["aufgabe"], werkzeuge)
        benutzt = {s.werkzeug for s in e.schritte if s.fehler != "unbekannt"}
        m = Messung(a["typ"], pruefen(e.antwort, a["erwartet"]), set(a["werkzeuge"]) <= benutzt, e)
        messungen.append(m)
        marke = "✓" if m.richtig else "✗"
        print(f"{marke} {a['aufgabe'][:58]:<58} {len(e.schritte)} Aufrufe  {e.sekunden:5.1f} s", flush=True)
        if zeigen or not m.richtig:
            for s in e.schritte:
                zeige_schritt(s)
            print(f"    Antwort: {e.antwort[:200].replace(chr(10), ' ')}")
    return messungen


def tabelle(ergebnisse: dict[str, list[Messung]]) -> None:
    n = len(next(iter(ergebnisse.values())))
    print(f"\nModell: {MODEL} · {n} Aufgaben\n")
    print(f"{'Variante':<24} {'Antwort':>8} {'Werkz.':>7} {'ungültig':>9} {'Fehler':>7} "
          f"{'Abbruch':>8} {'Aufrufe Ø':>10} {'Tokens Ø':>9} {'Dauer Ø':>8}")
    for name, ms in ergebnisse.items():
        schritte = [s for m in ms for s in m.ergebnis.schritte]
        print(
            f"{name:<24} {sum(m.richtig for m in ms):>4}/{n:<3} {sum(m.werkzeuge_ok for m in ms):>3}/{n:<3}"
            f" {sum(s.fehler in ('unbekannt', 'argumente') for s in schritte):>9}"
            f" {sum(s.fehler == 'wert' for s in schritte):>7}"
            f" {sum(m.ergebnis.abgebrochen for m in ms):>8}"
            f" {len(schritte) / n:>10.1f}"
            f" {sum(m.ergebnis.eingabe_tokens for m in ms) / n:>9.0f}"
            f" {sum(m.ergebnis.sekunden for m in ms) / n:>7.1f}s"
        )
    print("\nRichtige Antworten nach Typ:")
    typen = list(dict.fromkeys(m.typ for m in next(iter(ergebnisse.values()))))
    print(f"{'Variante':<24} " + " ".join(f"{t:>11}" for t in typen))
    for name, ms in ergebnisse.items():
        zellen = []
        for t in typen:
            auswahl = [m for m in ms if m.typ == t]
            zellen.append(f"{sum(m.richtig for m in auswahl)}/{len(auswahl)}")
        print(f"{name:<24} " + " ".join(f"{z:>11}" for z in zellen))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("varianten", nargs="*", default=["prompts/agent.v1.yaml"])
    parser.add_argument("--ohne-mcp", action="store_true")
    parser.add_argument("--zeigen", action="store_true", help="alle Schritte zeigen, nicht nur bei Fehlern")
    args = parser.parse_args()

    with open(AUFGABEN, encoding="utf-8") as f:
        aufgaben = json.load(f)
    werkzeuge = alle_werkzeuge(not args.ohne_mcp)
    ergebnisse = {v.removeprefix("prompts/"): messen(v, aufgaben, werkzeuge, args.zeigen) for v in args.varianten}
    tabelle(ergebnisse)
