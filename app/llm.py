"""Gemeinsamer Zugang zum Modell für alle Skripte.

Adresse, Modell und Key kommen aus Umgebungsvariablen (.env).
Der Code kennt kein bestimmtes Modell.
"""

import os

from openai import OpenAI

BASE_URL = os.environ["LLM_BASE_URL"]
API_KEY = os.environ.get("LLM_API_KEY", "nicht-noetig")  # Ollama braucht keinen Key
MODEL = os.environ["LLM_MODEL"]

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


def frage(text: str, **einstellungen) -> str:
    """Stellt eine einzelne Frage und gibt nur den Antworttext zurück.

    Weitere Parameter wie temperature oder max_tokens werden
    unverändert an die API durchgereicht.
    """
    antwort = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": text}],
        **einstellungen,
    )
    return (antwort.choices[0].message.content or "").strip()
