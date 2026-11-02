"""Variante 2: RAG, Abschnitte per Embedding finden.

Aufruf:
    docker compose run --rm app rag.py --index                 # einmal: Index bauen
    docker compose run --rm app rag.py "Wann hat die Mensa offen?"

Indexieren: Jede Datei wird in Abschnitte (Chunks) zerlegt. Ein
Embedding-Modell macht aus jedem Abschnitt einen Vektor, und die Vektoren
landen in Qdrant, einer Vektordatenbank, die als eigener Service läuft.

Abfragen: Die Frage wird mit demselben Modell eingebettet. Qdrant liefert
die Abschnitte, deren Vektoren der Frage am ähnlichsten sind.
"""

import argparse
import os
import re  # für TODO 4b, z. B. re.split
import time

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from openai import OpenAI

from wissen import Treffer, antworten, dokumente, zeigen

# Embeddings kommen immer vom lokalen Ollama, auch wenn das Sprachmodell
# in der Academic Cloud läuft. So bleibt der Index gleich, egal welches
# Modell antwortet.
EMBED_BASE_URL = os.environ.get("EMBED_BASE_URL", "http://ollama:11434/v1")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "granite-embedding:278m")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")
SAMMLUNG = "campus"
K = 4

embedder = OpenAI(base_url=EMBED_BASE_URL, api_key="nicht-noetig")
qdrant = QdrantClient(url=QDRANT_URL)


def zerlege(datei: str, text: str) -> list[Treffer]:
    """Zerlegt ein Dokument in Abschnitte (Chunks).

    Ein Abschnitt pro "## "-Überschrift, ohne Überschriften ein Abschnitt
    pro Absatz. Der Dokumenttitel kommt vor jeden Abschnitt, damit er auch
    allein verständlich bleibt und sein Vektor das Thema mitträgt.
    """
    titel, _, rumpf = text.strip().partition("\n")
    if not titel.startswith("# "):  # kein titel: die erste zeile gehört zum inhalt
        titel, rumpf = datei, text.strip()
    if re.search(r"^## ", rumpf, flags=re.MULTILINE):
        teile = re.split(r"^(?=## )", rumpf, flags=re.MULTILINE)
    else:
        teile = re.split(r"\n\s*\n", rumpf)
    return [Treffer(datei, f"{titel}\n{teil.strip()}") for teil in teile if teil.strip()]


def einbetten(texte: list[str]) -> list[list[float]]:
    """Macht aus Texten Vektoren, über die OpenAI-kompatible API von Ollama."""
    antwort = embedder.embeddings.create(model=EMBED_MODEL, input=texte)
    return [d.embedding for d in antwort.data]


def index_bauen() -> None:
    abschnitte = [a for datei, text in dokumente().items() for a in zerlege(datei, text)]
    start = time.perf_counter()
    vektoren = einbetten([a.text for a in abschnitte])
    if qdrant.collection_exists(SAMMLUNG):
        qdrant.delete_collection(SAMMLUNG)
    qdrant.create_collection(
        SAMMLUNG,
        vectors_config=VectorParams(size=len(vektoren[0]), distance=Distance.COSINE),
    )
    qdrant.upsert(
        SAMMLUNG,
        points=[
            PointStruct(id=i, vector=v, payload={"datei": a.datei, "text": a.text})
            for i, (a, v) in enumerate(zip(abschnitte, vektoren))
        ],
    )
    print(
        f"{len(abschnitte)} Abschnitte aus {len(dokumente())} Dateien indexiert,"
        f" {len(vektoren[0])} Dimensionen, {time.perf_counter() - start:.1f} s ({EMBED_MODEL})"
    )


def suche(frage: str, k: int = K) -> list[Treffer]:
    """Die k Abschnitte, die der Frage am ähnlichsten sind."""
    vektor = einbetten([frage])[0]
    punkte = qdrant.query_points(SAMMLUNG, query=vektor, limit=k).points
    return [Treffer(p.payload["datei"], p.payload["text"], p.score) for p in punkte]


def abrufen(frage: str, k: int = K) -> tuple[list[Treffer], float]:
    start = time.perf_counter()
    treffer = suche(frage, k)
    return treffer, time.perf_counter() - start


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("frage", nargs="*")
    parser.add_argument("--index", action="store_true", help="Index neu bauen")
    parser.add_argument("-k", type=int, default=K, help="Zahl der Abschnitte")
    args = parser.parse_args()
    if args.index:
        index_bauen()
    if args.frage:
        frage = " ".join(args.frage)
        treffer, sekunden = abrufen(frage, args.k)
        for t in treffer:
            erste_zeile = t.text.splitlines()[1] if "\n" in t.text else t.text
            print(f"  {t.wert:.3f}  {t.datei:<26} {erste_zeile[:50]}")
        print()
        zeigen(antworten(frage, treffer, sekunden))
