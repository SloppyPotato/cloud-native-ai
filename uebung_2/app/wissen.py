"""Gemeinsame Bausteine für Teil 4: Wissen laden und eine Antwort erzeugen.

Die drei Varianten unterscheiden sich nur darin, welche Texte sie dem
Modell als Kontext mitgeben:

    alles        die ganze Wissensbasis (alles.py)
    datei_suche  passende Dateien, gefunden per Textsuche (datei_suche.py)
    rag          passende Abschnitte, gefunden per Embedding (rag.py)

Die Antwort selbst entsteht immer gleich, mit prompts/wissen.v1.yaml.
"""

import time
from dataclasses import dataclass
from pathlib import Path

from llm import MODEL, client
from prompts import lade

WISSEN = Path("wissen")
STANDARD_PROMPT = "prompts/wissen.v1.yaml"


@dataclass
class Treffer:
    """Ein Stück Wissen, das in den Kontext kommt."""

    datei: str
    text: str
    wert: float = 0.0  # Trefferzahl (Textsuche) oder Ähnlichkeit (RAG)


@dataclass
class Antwort:
    text: str
    quellen: list[str]  # Dateien, die im Kontext standen
    eingabe_tokens: int
    sekunden_suche: float
    sekunden_antwort: float


def dokumente() -> dict[str, str]:
    """Alle Markdown-Dateien der Wissensbasis, ohne README."""
    return {
        p.name: p.read_text(encoding="utf-8")
        for p in sorted(WISSEN.glob("*.md"))
        if p.name != "README.md"
    }


def kontext_bauen(treffer: list[Treffer]) -> str:
    """Setzt die Treffer als markierte Dokumente zusammen."""
    teile = [f'<dokument datei="{t.datei}">\n{t.text.strip()}\n</dokument>' for t in treffer]
    return "\n\n".join(teile)


def antworten(
    frage: str, treffer: list[Treffer], sekunden_suche: float = 0.0,
    prompt_pfad: str = STANDARD_PROMPT,
) -> Antwort:
    prompt = lade(prompt_pfad)
    eingabe = f"<dokumente>\n{kontext_bauen(treffer)}\n</dokumente>\n\nFrage: {frage}"
    start = time.perf_counter()
    antwort = client.chat.completions.create(
        model=MODEL,
        temperature=prompt.temperature,
        messages=prompt.nachrichten(eingabe),
        max_tokens=300,
    )
    return Antwort(
        text=(antwort.choices[0].message.content or "").strip(),
        quellen=sorted({t.datei for t in treffer}),
        eingabe_tokens=antwort.usage.prompt_tokens,
        sekunden_suche=sekunden_suche,
        sekunden_antwort=time.perf_counter() - start,
    )


def zeigen(antwort: Antwort) -> None:
    print(antwort.text)
    print(f"\n  Kontext: {', '.join(antwort.quellen) or '(nichts gefunden)'}")
    print(
        f"  {antwort.eingabe_tokens} Eingabe-Tokens · Suche {antwort.sekunden_suche:.2f} s"
        f" · Antwort {antwort.sekunden_antwort:.1f} s · {MODEL}"
    )
