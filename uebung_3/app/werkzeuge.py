"""Werkzeuge, die der Agent direkt in Python aufruft.

Ein Werkzeug besteht aus drei Teilen:
  - einem Namen, unter dem das Modell es aufruft,
  - einer Beschreibung und einem JSON-Schema für die Parameter.
    Das ist alles, was das Modell vom Werkzeug sieht.
  - einer Python-Funktion, die unser Code ausführt.

Das Modell führt nie selbst etwas aus. Es schreibt nur auf, welches
Werkzeug es mit welchen Argumenten aufrufen möchte. Ausführen tut unser Code.
"""

import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

WISSEN = Path("wissen")
WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


@dataclass
class Werkzeug:
    name: str
    beschreibung: str
    parameter: dict  # JSON-Schema der Argumente
    funktion: Callable[..., str]
    schreibend: bool = False  # verändert es etwas in der Welt?

    def als_tool(self) -> dict:
        """Die Form, in der die OpenAI-kompatible API Werkzeuge erwartet."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.beschreibung,
                "parameters": self.parameter,
            },
        }


# ---------------------------------------------------------------------------
# Wissen: Dateisuche aus Übung 2, jetzt als Werkzeug. Der Agent entscheidet
# selbst, wonach er sucht, und kann nachsuchen (agentische Suche).
# ---------------------------------------------------------------------------

def suche_wissen(begriff: str) -> str:
    """Sucht einen Begriff in allen Dateien der Wissensbasis (wie grep -i)."""
    begriff = begriff.strip()
    if not begriff:
        return "Fehler: Der Suchbegriff ist leer."
    muster = re.compile(re.escape(begriff), re.IGNORECASE)
    treffer = []
    for pfad in sorted(WISSEN.glob("*.md")):
        if pfad.name == "README.md":
            continue
        zeilen = [z.strip() for z in pfad.read_text(encoding="utf-8").splitlines() if muster.search(z)]
        if zeilen:
            treffer.append((len(zeilen), pfad.name, zeilen[:2]))
    if not treffer:
        return f"Keine Datei enthält '{begriff}'. Versuche einen anderen, einfacheren Begriff."
    treffer.sort(reverse=True)
    teile = [f"{name} ({n} Treffer): " + " | ".join(z) for n, name, z in treffer[:5]]
    return "\n".join(teile)


def lies_datei(datei: str) -> str:
    """Gibt den Inhalt einer Datei der Wissensbasis zurück."""
    pfad = WISSEN / Path(datei).name  # Path(...).name verhindert ../-Tricks
    if not pfad.exists():
        vorhanden = ", ".join(p.name for p in sorted(WISSEN.glob("*.md")))
        return f"Fehler: Datei {datei} gibt es nicht. Vorhanden: {vorhanden}"
    return pfad.read_text(encoding="utf-8")


def heute() -> str:
    """Heutiges Datum mit Wochentag. HEUTE in .env fixiert es für Messungen."""
    tag = date.fromisoformat(os.environ["HEUTE"]) if os.environ.get("HEUTE") else date.today()
    return f"Heute ist {WOCHENTAGE[tag.weekday()]}, der {tag.isoformat()}."


# TODO 2: ein eigenes Werkzeug tage_bis(datum)
#
# Sprachmodelle rechnen schlecht mit Datumsangaben. Schreibt eine Funktion
# tage_bis(datum: str) -> str, die zurückgibt, wie viele Tage von heute
# (siehe heute(), also auch HEUTE aus .env beachten) bis zu einem Datum im
# Format JJJJ-MM-TT sind. Liegt das Datum in der Vergangenheit, sagt sie das.
# Ein ungültiges Datum beantwortet sie mit einer Fehlermeldung, nicht mit
# einer Exception.
#
# Tragt das Werkzeug danach in LOKALE_WERKZEUGE ein, mit Beschreibung und
# JSON-Schema. Testet es mit:
#   docker compose run --rm app agent.py "Wie viele Tage habe ich noch, bis die Prüfungsanmeldung endet?"


LOKALE_WERKZEUGE = [
    Werkzeug(
        name="suche_wissen",
        beschreibung=(
            "Durchsucht die Wissensbasis der Hochschule (Regeln, Fristen, Gebühren, "
            "Öffnungszeiten, Ansprechpartner) nach einem Begriff. Gibt die Dateien mit "
            "Treffern und passende Zeilen zurück. Nutze kurze Begriffe, ein Wort ist am besten."
        ),
        parameter={
            "type": "object",
            "properties": {
                "begriff": {"type": "string", "description": "Suchbegriff, z. B. Attest oder Parkausweis"},
            },
            "required": ["begriff"],
        },
        funktion=suche_wissen,
    ),
    Werkzeug(
        name="lies_datei",
        beschreibung="Liest eine Datei der Wissensbasis vollständig, z. B. nachdem suche_wissen sie gefunden hat.",
        parameter={
            "type": "object",
            "properties": {
                "datei": {"type": "string", "description": "Dateiname wie mensa.md"},
            },
            "required": ["datei"],
        },
        funktion=lies_datei,
    ),
    Werkzeug(
        name="heute",
        beschreibung="Gibt das heutige Datum und den Wochentag zurück.",
        parameter={"type": "object", "properties": {}},
        funktion=heute,
    ),
]


if __name__ == "__main__":
    # Werkzeuge ohne Modell ausprobieren:
    #   docker compose run --rm app werkzeuge.py
    print(heute())
    print(suche_wissen("Attest"))
    print(lies_datei("mensa.md")[:200], "...")
