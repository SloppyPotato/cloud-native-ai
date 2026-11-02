"""Variante 0: die ganze Wissensbasis in den Kontext.

Aufruf:
    docker compose run --rm app alles.py "Wann hat die Mensa offen?"

Keine Suche, kein Index. Das ist die Messlatte für die beiden anderen
Varianten: Solange alles in den Kontext passt, ist das der einfachste Weg.
Schaut auf die Eingabe-Tokens und überlegt, was bei 2.000 statt 21
Dateien passiert.
"""

import sys

from wissen import Treffer, antworten, dokumente, zeigen


def alles() -> list[Treffer]:
    return [Treffer(datei, text) for datei, text in dokumente().items()]


if __name__ == "__main__":
    zeigen(antworten(" ".join(sys.argv[1:]), alles()))
