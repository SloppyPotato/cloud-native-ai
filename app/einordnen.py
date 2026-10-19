"""Teil D: Anfragen an den Campus-Assistenten strukturiert einordnen.

Das Modell soll aus einer Mail drei Dinge herauslesen: das Anliegen,
den Studiengang und eine Frist. Das Ergebnis verarbeitet ein Programm
weiter, es muss also immer die gleiche Form haben.

Aufruf:
    docker compose run --rm app einordnen.py
    docker compose run --rm app einordnen.py "Eure eigene Mail"
"""

import json
import re
import sys
from typing import Literal

from pydantic import BaseModel, ValidationError, ValidationInfo, field_validator

from llm import MODEL, client

SYSTEM_PROMPT = (
    "Du ordnest Mails von Studierenden an die HTWG Konstanz ein. "
    "Antworte ausschließlich mit JSON. "
    "anliegen ist pruefung, mensa, bibliothek oder sonstiges. "
    "studiengang ist das Kürzel (z. B. AIN, WIN, MSI) oder null. "
    "frist ist die Frist aus der Mail, so wie sie dort steht, oder null."
)

# studiengänge der fakultät informatik
STUDIENGAENGE = {"AIN", "WIN", "GIB", "MSI", "BIT"}


# kleinschreiben und satzzeichen raus, sonst scheitert "Montag, 26.10." an "Montag 26.10."
# punkte bleiben drin wegen datum
def klein(text: str) -> str:
    return " ".join(re.sub(r"[^\w.]+", " ", text.lower()).split())


# punkt am ende egal, und nur ganze wörter zählen ("6.10." soll nicht in "16.10." gefunden werden)
def steht_in(teil: str, mail: str) -> bool:
    teil = klein(teil).rstrip(".")
    return bool(teil) and re.search(rf"(?<!\w){re.escape(teil)}(?!\w)", klein(mail)) is not None


class AnfrageOhneZusatz(BaseModel):
    anliegen: Literal["pruefung", "mensa", "bibliothek", "sonstiges"]
    studiengang: str | None
    frist: str | None


class Anfrage(AnfrageOhneZusatz):
    @field_validator("studiengang", "frist", mode="before")
    @classmethod
    def null_text_zu_none(cls, wert):
        if isinstance(wert, str) and wert.strip().lower() in ("", "null", "none"):
            return None
        return wert

    @field_validator("studiengang")
    @classmethod
    def nur_bekannte_kuerzel(cls, wert):
        if wert and wert.strip().upper() in STUDIENGAENGE:
            return wert.strip().upper()
        return None

    @field_validator("frist")
    @classmethod
    def frist_muss_in_mail_stehen(cls, wert, info: ValidationInfo):
        mail = (info.context or {}).get("mail")
        if wert and mail and not steht_in(wert, mail):
            print(f"  warnung: frist {wert!r} steht nicht in der mail, wird None")
            return None
        return wert


def schema_von(modell: type[BaseModel]) -> dict:
    """Verpackt das JSON-Schema einer Pydantic-Klasse für response_format."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": modell.__name__.lower(),
            "schema": modell.model_json_schema(),
        },
    }


def einordnen(mail: str, versuche: int = 3,
              klasse: type[AnfrageOhneZusatz] = Anfrage) -> AnfrageOhneZusatz:
    """Fragt das Modell und gibt eine geprüfte Anfrage zurück."""
    nachricht = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": mail},
    ]
    for versuch in range(1, versuche + 1):
        antwort = client.chat.completions.create(
            model=MODEL,
            messages=nachricht,
            # 0 weil wir nur daten aus der mail rausziehen, kreativ soll da nix sein.
            # es wird immer das wahrscheinlichste token genommen, gleiche mail gibt also praktisch immer das gleiche ergebnis
            temperature=0,
            max_tokens=200,  # json mit 3 feldern ist kurz, so kann sich das modell nicht endlos verrennen
            response_format=schema_von(Anfrage),
        )
        roh = antwort.choices[0].message.content or ""
        try:
            return klasse.model_validate_json(roh, context={"mail": mail})
        except ValidationError as fehler:
            abgeschnitten = " (bei max_tokens abgeschnitten)" if antwort.choices[0].finish_reason == "length" else ""
            print(f"  versuch {versuch}/{versuche} ungültig{abgeschnitten}: {fehler.error_count()} fehler")
            # bei temperature 0 käme sonst genau dieselbe antwort nochmal, deshalb antwort + fehler mitschicken
            nachricht += [
                {"role": "assistant", "content": roh},
                {"role": "user", "content": f"Die Antwort war ungültig:\n{fehler}\nAntworte nur mit dem korrigierten JSON."},
            ]
    raise RuntimeError(f"nach {versuche} versuchen immer noch keine gültige antwort, abbruch")


def alle_felder_richtig(ergebnis: AnfrageOhneZusatz, erwartet: dict) -> bool:
    if ergebnis.anliegen != erwartet["anliegen"] or ergebnis.studiengang != erwartet["studiengang"]:
        return False
    if erwartet["frist"] is None:
        return ergebnis.frist is None
    return erwartet["frist"] in (ergebnis.frist or "")


def auswerten() -> None:
    """Ordnet alle Test-Mails ein und vergleicht mit dem Erwarteten."""
    with open("mails.json", encoding="utf-8") as f:
        faelle = json.load(f)
    richtig = vorher = nachher = 0
    for fall in faelle:
        # einmal fragen, dann dieselbe antwort ohne und mit zusatz-prüfung bewerten
        ohne = einordnen(fall["mail"], klasse=AnfrageOhneZusatz)
        treffer = ohne.anliegen == fall["erwartet"]["anliegen"]
        richtig += treffer
        print(f"\n{'✓' if treffer else '✗'} {fall['mail']}")
        print(f"  ergebnis: {ohne.model_dump()}")
        mit = Anfrage.model_validate(ohne.model_dump(), context={"mail": fall["mail"]})
        if mit.model_dump() != ohne.model_dump():
            print(f"  geprüft:  {mit.model_dump()}")
        vorher += alle_felder_richtig(ohne, fall["erwartet"])
        nachher += alle_felder_richtig(mit, fall["erwartet"])
    print(f"\n{richtig} von {len(faelle)} Anliegen richtig ({MODEL})")
    print(f"alle drei felder richtig: ohne zusatz {vorher}, mit zusatz {nachher} von {len(faelle)}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(einordnen(" ".join(sys.argv[1:])).model_dump_json(indent=2))
    else:
        auswerten()
