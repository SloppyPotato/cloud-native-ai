"""Zum Vergleich: ein fester Workflow statt eines Agenten.

Aufruf:
    docker compose run --rm app workflow.py "Was gibt es morgen in der Mensa?"

Hier entscheidet nicht das Modell über den Ablauf, sondern unser Code.
Der Ablauf ist immer derselbe (Muster "Routing" aus Anthropic,
Building Effective Agents):

  1. Code:   heutiges Datum bestimmen (kein Modell nötig)
  2. Modell: die Frage einordnen, strukturiert (Kategorie, Datum, Raum, Suchbegriff)
  3. Code:   je nach Kategorie genau ein festes Werkzeug aufrufen
  4. Modell: aus dem Ergebnis die Antwort formulieren

Immer genau zwei Modellaufrufe. Vorhersagbar, billig, leicht zu testen.
Aber: Was nicht in eine Kategorie passt, kann der Workflow nicht.
"""

import argparse
import re
import time
from typing import Literal

from pydantic import BaseModel

from agent import Ergebnis, Schritt, alle_werkzeuge, zeige_schritt
from llm import MODEL, client
from prompts import lade
from werkzeuge import Werkzeug, heute


class Einordnung(BaseModel):
    kategorie: Literal["wissen", "mensa", "raum", "sonstiges"]
    datum: str | None = None        # JJJJ-MM-TT
    raum: str | None = None         # z. B. O-108
    suchbegriff: str | None = None  # ein Fachbegriff für die Wissenssuche


def schema_von(modell: type[BaseModel]) -> dict:
    return {"type": "json_schema", "json_schema": {"name": modell.__name__.lower(),
                                                   "schema": modell.model_json_schema()}}


def workflow(frage: str, werkzeuge: list[Werkzeug]) -> Ergebnis:
    verzeichnis = {w.name: w for w in werkzeuge}
    ergebnis = Ergebnis(antwort="")
    start = time.perf_counter()

    def rufe(name: str, **argumente) -> str:
        text = verzeichnis[name].funktion(**argumente)
        ergebnis.schritte.append(Schritt(name, argumente, text, "wert" if text.startswith("Fehler") else None))
        return text

    def modell(prompt_pfad: str, eingabe: str, **extra):
        prompt = lade(prompt_pfad)
        antwort = client.chat.completions.create(
            model=MODEL, temperature=prompt.temperature, messages=prompt.nachrichten(eingabe),
            max_tokens=300, **extra)
        ergebnis.modellaufrufe += 1
        ergebnis.eingabe_tokens += antwort.usage.prompt_tokens
        ergebnis.ausgabe_tokens += antwort.usage.completion_tokens
        return antwort.choices[0].message.content or ""

    # 1. Datum: deterministisch im Code
    datum_heute = heute()

    # 2. Einordnen mit strukturierter Ausgabe (VL 2)
    roh = modell("prompts/router.v1.yaml", f"{datum_heute}\nFrage: {frage}",
                 response_format=schema_von(Einordnung))
    try:
        e = Einordnung.model_validate_json(roh)
    except ValueError:
        e = Einordnung(kategorie="sonstiges")

    # 3. Genau ein fester Pfad pro Kategorie
    kontext = ""
    if e.kategorie == "mensa" and e.datum:
        kontext = rufe("mensa_speiseplan", datum=e.datum)
    elif e.kategorie == "raum":
        kontext = rufe("raum_frei", raum=e.raum, datum=e.datum) if e.raum and e.datum \
            else rufe("raeume_auflisten")
    elif e.kategorie == "wissen" and e.suchbegriff:
        treffer = rufe("suche_wissen", begriff=e.suchbegriff)
        beste = re.match(r"(\S+\.md)", treffer)
        kontext = rufe("lies_datei", datei=beste.group(1)) if beste else treffer

    # 4. Antwort formulieren
    eingabe = f"{datum_heute}\n<werkzeug>\n{kontext or '(nichts)'}\n</werkzeug>\n\nFrage: {frage}"
    ergebnis.antwort = modell("prompts/antwort.v1.yaml", eingabe).strip()
    ergebnis.sekunden = time.perf_counter() - start
    return ergebnis


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("frage", nargs="?", default="Was gibt es heute in der Mensa?")
    args = parser.parse_args()
    e = workflow(args.frage, alle_werkzeuge())
    for s in e.schritte:
        zeige_schritt(s)
    print(f"\n{e.antwort}\n\n  {e.modellaufrufe} Modellaufrufe · {e.eingabe_tokens} Eingabe-Tokens · "
          f"{e.sekunden:.1f} s · {MODEL}")
