"""Teil 4.5: einordnen ohne response_format, nur mit dem system-prompt.

Aufruf:
    docker compose run --rm app ohne_schema.py
"""

import json

from pydantic import ValidationError

from einordnen import SYSTEM_PROMPT, AnfrageOhneZusatz
from llm import MODEL, client


def roh_antwort(mail: str) -> str:
    antwort = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": mail}],
        temperature=0,
        max_tokens=400,  # ohne limit schreibt qwen bei der gedicht-mail endlos weiter
    )
    if antwort.choices[0].finish_reason == "length":
        print("  (bei 400 tokens abgeschnitten)")
    return antwort.choices[0].message.content or ""


def gueltig(roh: str) -> bool:
    try:
        AnfrageOhneZusatz.model_validate_json(roh)
        return True
    except ValidationError:
        return False


with open("mails.json", encoding="utf-8") as f:
    faelle = json.load(f)

anzahl = 0
for fall in faelle:
    roh = roh_antwort(fall["mail"])
    print(f"\n{fall['mail']}\n  roh: {roh!r}")
    if gueltig(roh):
        anzahl += 1
        continue
    # gleiche anfrage bei T 0 noch 2x schicken, so wie ein einfacher retry
    zweite, dritte = roh_antwort(fall["mail"]), roh_antwort(fall["mail"])
    print(f"  2. versuch: {'gleich wie 1.' if zweite == roh else 'anders als 1.'}, {'gültig' if gueltig(zweite) else 'ungültig'}")
    print(f"  3. versuch: {'gleich wie 2.' if dritte == zweite else 'anders als 2.'}, {'gültig' if gueltig(dritte) else 'ungültig'}")
print(f"\n{anzahl} von {len(faelle)} antworten gültig ohne response_format ({MODEL})")
