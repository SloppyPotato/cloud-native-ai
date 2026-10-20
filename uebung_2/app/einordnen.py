"""Anfragen an den Campus-Assistenten strukturiert einordnen.

Wie in Übung 1, mit einem Unterschied: Der Prompt steht nicht mehr im
Code, sondern in einer versionierten Datei unter prompts/.

Aufruf:
    docker compose run --rm app einordnen.py
    docker compose run --rm app einordnen.py --prompt prompts/einordnen.v2.yaml
    docker compose run --rm app einordnen.py "Eure eigene Mail"
"""

import argparse
import json
import time
from typing import Literal

from pydantic import BaseModel, ValidationError

from llm import MODEL, client
from prompts import Prompt, lade

STANDARD_PROMPT = "prompts/einordnen.v1.yaml"


class Anfrage(BaseModel):
    anliegen: Literal["pruefung", "mensa", "bibliothek", "sonstiges"]
    studiengang: str | None
    frist: str | None


def schema_von(modell: type[BaseModel]) -> dict:
    """Verpackt das JSON-Schema einer Pydantic-Klasse für response_format."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": modell.__name__.lower(),
            "schema": modell.model_json_schema(),
        },
    }


def einordnen(
    mail: str, prompt: Prompt, versuche: int = 3, protokoll: list | None = None
) -> Anfrage:
    """Fragt das Modell und gibt eine geprüfte Anfrage zurück.

    Wer eine Liste als protokoll übergibt, bekommt pro Aufruf ein Paar
    (Eingabe-Tokens, Sekunden) angehängt. vergleich.py nutzt das.
    """
    for versuch in range(1, versuche + 1):
        start = time.perf_counter()
        antwort = client.chat.completions.create(
            model=MODEL,
            temperature=prompt.temperature,
            messages=prompt.nachrichten(mail),
            response_format=schema_von(Anfrage),
        )
        if protokoll is not None:
            protokoll.append(
                (antwort.usage.prompt_tokens, time.perf_counter() - start)
            )
        text = antwort.choices[0].message.content or ""
        try:
            return Anfrage.model_validate_json(text)
        except ValidationError as fehler:
            print(f"  Versuch {versuch} ungültig: {fehler.error_count()} Fehler")
    raise RuntimeError(f"Nach {versuche} Versuchen keine gültige Antwort")


def felder_richtig(ergebnis: Anfrage, erwartet: dict) -> dict[str, bool]:
    """Vergleicht jedes Feld mit dem erwarteten Wert.

    Anliegen und Studiengang müssen exakt stimmen. Eine Frist zählt als
    richtig, wenn die erwartete Frist im Ergebnis enthalten ist:
    "Freitag, 16.10." passt also zu "16.10.".
    """
    frist_ok = (
        ergebnis.frist is None
        if erwartet["frist"] is None
        else erwartet["frist"].lower() in (ergebnis.frist or "").lower()
    )
    return {
        "anliegen": ergebnis.anliegen == erwartet["anliegen"],
        "studiengang": ergebnis.studiengang == erwartet["studiengang"],
        "frist": frist_ok,
    }


def auswerten(prompt: Prompt) -> None:
    """Ordnet alle Test-Mails ein und vergleicht mit dem Erwarteten."""
    with open("mails.json", encoding="utf-8") as f:
        faelle = json.load(f)
    anliegen_ok = alles_ok = 0
    for fall in faelle:
        ergebnis = einordnen(fall["mail"], prompt)
        ok = felder_richtig(ergebnis, fall["erwartet"])
        anliegen_ok += ok["anliegen"]
        alles_ok += all(ok.values())
        zeichen = "".join("✓" if v else "✗" for v in ok.values())
        print(f"{zeichen}  {fall['mail'][:70]}")
        print(f"     {ergebnis.model_dump()}")
    n = len(faelle)
    print(f"\n{prompt.kennung} mit {MODEL}:")
    print(f"  Anliegen richtig:   {anliegen_ok} von {n}")
    print(f"  Alle Felder richtig: {alles_ok} von {n}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mail", nargs="*", help="eigene Mail statt mails.json")
    parser.add_argument("--prompt", default=STANDARD_PROMPT)
    args = parser.parse_args()
    prompt = lade(args.prompt)
    if args.mail:
        print(einordnen(" ".join(args.mail), prompt).model_dump_json(indent=2))
    else:
        auswerten(prompt)
