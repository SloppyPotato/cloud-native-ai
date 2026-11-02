"""Alle Varianten auf denselben Testfragen vergleichen.

Aufruf:
    docker compose run --rm app vergleich_wissen.py               # woerter, datei, rag
    docker compose run --rm app vergleich_wissen.py alles rag     # beliebige Auswahl

Die Variante alles läuft nur, wenn ihr sie nennt: Der erste Aufruf dauert
auf dem Laptop gut eine Minute.

Vorher einmal den RAG-Index bauen: docker compose run --rm app rag.py --index

Für jede Frage aus fragen.json prüft das Skript zwei Dinge getrennt:
    Kontext  Stand die richtige Datei im Kontext? (Fehler der Suche)
    Antwort  Steht ein erwartetes Stichwort in der Antwort? (Fehler des Modells)
Dazu misst es Eingabe-Tokens und Dauer. Die Antwort-Prüfung per Stichwort
ist grob, schaut euch die Antworten bei Zweifeln selbst an.
"""

import json
import sys

import datei_suche
import hybrid
import rag
from alles import alles
from llm import MODEL
from wissen import antworten


def abrufen(variante: str, frage: str):
    if variante == "alles":
        return alles(), 0.0
    if variante == "woerter":
        treffer, _, sekunden = datei_suche.abrufen(frage, nur_woerter=True)
        return treffer, sekunden
    if variante == "datei":
        treffer, _, sekunden = datei_suche.abrufen(frage)
        return treffer, sekunden
    if variante == "rag":
        return rag.abrufen(frage)
    if variante == "hybrid":  # teil 4.5
        return hybrid.abrufen(frage)
    raise ValueError(f"Unbekannte Variante: {variante}")


def antwort_richtig(text: str, fall: dict) -> bool:
    return any(e.lower() in text.lower() for e in fall["erwartet"])


def vergleiche(varianten: list[str]) -> None:
    with open("fragen.json", encoding="utf-8") as f:
        faelle = json.load(f)
    print(f"Modell: {MODEL} · Embedding: {rag.EMBED_MODEL} · {len(faelle)} Fragen\n")
    kopf = "".join(f"{v:>10}" for v in varianten)
    print(f"{'Frage':<52} {'Typ':<12}{kopf}")
    summen = {v: {"kontext": 0, "antwort": 0, "tokens": 0, "sekunden": 0.0} for v in varianten}
    mit_quelle = sum(1 for f in faelle if f["quelle"])
    for fall in faelle:
        zelle = []
        for v in varianten:
            treffer, sek_suche = abrufen(v, fall["frage"])
            a = antworten(fall["frage"], treffer, sek_suche)
            kontext_ok = fall["quelle"] in a.quellen if fall["quelle"] else None
            antwort_ok = antwort_richtig(a.text, fall)
            s = summen[v]
            s["kontext"] += bool(kontext_ok)
            s["antwort"] += antwort_ok
            s["tokens"] += a.eingabe_tokens
            s["sekunden"] += a.sekunden_suche + a.sekunden_antwort
            k = "-" if kontext_ok is None else ("K" if kontext_ok else "·")
            zelle.append(f"{k} {'A' if antwort_ok else '·'}".rjust(10))
        print(f"{fall['frage'][:51]:<52} {fall['typ']:<12}{''.join(zelle)}", flush=True)

    n = len(faelle)
    print("\nK = richtige Datei im Kontext, A = Antwort enthält ein erwartetes Stichwort\n")
    print(f"| Variante | Kontext richtig | Antwort richtig | Eingabe-Tokens (Ø) | Dauer (Ø) |")
    print(f"|---|---|---|---|---|")
    for v in varianten:
        s = summen[v]
        print(
            f"| {v} | {s['kontext']}/{mit_quelle} | {s['antwort']}/{n} |"
            f" {s['tokens'] / n:.0f} | {s['sekunden'] / n:.1f} s |"
        )


if __name__ == "__main__":
    vergleiche(sys.argv[1:] or ["woerter", "datei", "rag"])
