"""Erster Modellaufruf für den Campus-Assistenten.

Das Skript spricht jedes Modell an, das eine OpenAI-kompatible API anbietet:
lokal Ollama, entfernt die Academic Cloud. Welches Modell genutzt wird,
steht nicht im Code, sondern in Umgebungsvariablen. So bleibt das Modell
ein austauschbarer Baustein.
"""

import os
import sys
import time

from openai import OpenAI

BASE_URL = os.environ["LLM_BASE_URL"]
API_KEY = os.environ.get("LLM_API_KEY", "nicht-noetig")  # Ollama braucht keinen Key
MODEL = os.environ["LLM_MODEL"]

SYSTEM_PROMPT = (
    "Du bist der Campus-Assistent der HTWG Konstanz. "
    "Antworte kurz, freundlich und auf Deutsch. "
    "Wenn du etwas nicht sicher weißt, sag das ehrlich."
)


def frage_stellen(frage: str) -> None:
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

    start = time.perf_counter()
    erstes_token = None
    antwort = []

    # stream=True liefert die Antwort Token für Token. Nur so können wir
    # messen, wann das erste Token ankommt (Time to First Token, TTFT).
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": frage},
        ],
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        teil = chunk.choices[0].delta.content or ""
        if teil and erstes_token is None:
            erstes_token = time.perf_counter()
        antwort.append(teil)
        print(teil, end="", flush=True)

    ende = time.perf_counter()
    print("\n")
    print(f"Modell:              {MODEL} @ {BASE_URL}")
    if erstes_token is not None:
        print(f"Time to First Token: {(erstes_token - start) * 1000:.0f} ms")
    print(f"Gesamtdauer:         {(ende - start) * 1000:.0f} ms")
    print(f"Zeichen Antwort:     {len(''.join(antwort))}")


if __name__ == "__main__":
    frage = " ".join(sys.argv[1:]) or "Was kann ich in der Mensa der HTWG heute essen?"
    frage_stellen(frage)
