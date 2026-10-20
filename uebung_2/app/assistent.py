"""Der Campus-Assistent beantwortet eine Frage.

Aufruf:
    docker compose run --rm app assistent.py "Wann hat die Bibliothek offen?"
    docker compose run --rm app assistent.py --prompt prompts/assistent.v2.yaml "..."

In Teil 3 greift ihr diesen Assistenten an und härtet ihn danach.
"""

import argparse

from llm import MODEL, client
from prompts import Prompt, lade

STANDARD_PROMPT = "prompts/assistent.v1.yaml"

# angriff.py und angreifer.py schalten den Guardrail mit --ohne-guardrail ab,
# damit ihr seine Wirkung getrennt vom Prompt messen könnt.
GUARDRAIL_AN = True


def ausgabe_pruefen(text: str) -> str:
    """Guardrail am Ausgang: läuft nach dem Modell, im Code.

    TODO 3 (Teil 3): Prüft hier die Antwort, bevor sie an die
    Studierenden geht. Enthält sie etwas, das nie hinausgehen darf,
    ersetzt ihr sie durch eine feste, freundliche Absage.
    Im Moment wird alles unverändert durchgereicht.
    """
    return text


def antworten(frage: str, prompt: Prompt) -> str:
    antwort = client.chat.completions.create(
        model=MODEL,
        temperature=prompt.temperature,
        messages=prompt.nachrichten(frage),
        max_tokens=300,
    )
    text = (antwort.choices[0].message.content or "").strip()
    return ausgabe_pruefen(text) if GUARDRAIL_AN else text


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("frage", nargs="+")
    parser.add_argument("--prompt", default=STANDARD_PROMPT)
    args = parser.parse_args()
    prompt = lade(args.prompt)
    print(f"[{prompt.kennung} · {MODEL}]\n")
    print(antworten(" ".join(args.frage), prompt))
