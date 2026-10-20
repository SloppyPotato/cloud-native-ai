"""Prompts als versionierte Artefakte.

Jeder Prompt liegt als eigene YAML-Datei unter prompts/, zum Beispiel
prompts/einordnen.v1.yaml. Die Datei enthält den Text und die Metadaten,
die zum Prompt gehören: Version, Zweck, Autor, Datum und Temperature.

Regel: Eine veröffentlichte Version wird nie mehr geändert. Wer etwas
verbessern will, legt eine neue Datei mit der nächsten Versionsnummer an.
"""

from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel

PLATZHALTER = "{eingabe}"


class Prompt(BaseModel):
    name: str
    version: int
    beschreibung: str
    autor: str
    erstellt: date
    temperature: float = 0.0
    system: str
    user: str = PLATZHALTER

    @property
    def kennung(self) -> str:
        return f"{self.name}.v{self.version}"

    def nachrichten(self, eingabe: str) -> list[dict]:
        """Baut die Nachrichten für die API und setzt die Eingabe ein.

        Wir ersetzen nur den Platzhalter {eingabe} und benutzen bewusst
        kein str.format: Prompts enthalten oft JSON mit geschweiften
        Klammern, die format() als Platzhalter missverstehen würde.
        """
        return [
            {"role": "system", "content": self.system.replace(PLATZHALTER, eingabe)},
            {"role": "user", "content": self.user.replace(PLATZHALTER, eingabe)},
        ]


def lade(pfad: str | Path) -> Prompt:
    """Liest eine Prompt-Datei und prüft sie gegen das Schema oben."""
    with open(pfad, encoding="utf-8") as f:
        return Prompt.model_validate(yaml.safe_load(f))


if __name__ == "__main__":
    # Zeigt alle Prompts mit ihren Metadaten:
    #   docker compose run --rm app prompts.py
    for datei in sorted(Path("prompts").glob("*.yaml")):
        p = lade(datei)
        print(f"{p.kennung:<16} {p.erstellt}  T={p.temperature}  {p.beschreibung}")
