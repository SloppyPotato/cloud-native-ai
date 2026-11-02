"""Teil 4.5: hybride Suche, Kennungen per Textsuche, alles andere per RAG.

Aufruf:
    docker compose run --rm app hybrid.py "Wer sitzt in Raum F-201?"
    docker compose run --rm app vergleich_wissen.py rag hybrid

Embeddings fassen die Bedeutung, kennen aber Kennungen wie F-201 kaum:
Für das Modell ist das eine beliebige Zeichenfolge. Die Textsuche findet
sie dagegen zuverlässig. Steht eine Kennung in der Frage, kommen deshalb
zuerst die Abschnitte, die sie wörtlich enthalten, und RAG füllt den Rest
auf. Ohne Kennung ist das Ergebnis genau dasselbe wie bei rag.py.
"""

import re
import sys
import time

import rag
from wissen import Treffer, antworten, dokumente, zeigen

# raumnummern und formulare (F-201, PA-12) und paragraphen (§ 17, Paragraph 17)
KENNUNG = re.compile(r"\b[A-Z]{1,3}-\d+\b|§\s*\d+|\bParagraph\s+\d+", re.IGNORECASE)


def kennungen(frage: str) -> list[str]:
    """Die Kennungen der Frage, "Paragraph 17" wird zur Schreibweise "§ 17"."""
    return [
        re.sub(r"^(§|paragraph)\s*", "§ ", k, flags=re.IGNORECASE)
        for k in KENNUNG.findall(frage)
    ]


def text_treffer(gesucht: list[str]) -> list[Treffer]:
    """Alle Abschnitte, die eine Kennung wörtlich enthalten."""
    # \b am ende, sonst fände "§ 1" auch "§ 12"
    muster = [re.compile(re.escape(k) + r"\b", re.IGNORECASE) for k in gesucht]
    return [
        Treffer(a.datei, a.text, 1.0)
        for datei, text in dokumente().items()
        for a in rag.zerlege(datei, text)
        if any(m.search(a.text) for m in muster)
    ]


def abrufen(frage: str, k: int = rag.K) -> tuple[list[Treffer], float]:
    start = time.perf_counter()
    treffer = text_treffer(kennungen(frage))[:k]
    schon_da = {t.text for t in treffer}
    for t in rag.suche(frage, k):
        if len(treffer) < k and t.text not in schon_da:
            treffer.append(t)
    return treffer, time.perf_counter() - start


if __name__ == "__main__":
    frage = " ".join(sys.argv[1:])
    print(f"Kennungen: {kennungen(frage)}")
    treffer, sekunden = abrufen(frage)
    for t in treffer:
        print(f"  {t.wert:.3f}  {t.datei}")
    print()
    zeigen(antworten(frage, treffer, sekunden))
