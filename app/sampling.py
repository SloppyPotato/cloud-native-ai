"""Teil B: Wie stark streuen die Antworten bei verschiedenen Temperaturen?

Aufruf:
    docker compose run --rm app sampling.py
    docker compose run --rm app sampling.py "Eure eigene Frage"
"""

import sys
from collections import Counter

from llm import MODEL, frage

TEMPERATUREN = [0.0, 0.7, 1.2]
DURCHLAEUFE = 5

prompt = " ".join(sys.argv[1:]) or (
    "Erfinde einen Namen für ein neues Gericht in der Mensa. "
    "Antworte nur mit dem Namen."
)

print(f"Modell: {MODEL}\nPrompt: {prompt}\n")
for t in TEMPERATUREN:
    antworten = [frage(prompt, temperature=t, max_tokens=40)
                 for _ in range(DURCHLAEUFE)]
    zaehlung = Counter(antworten)
    print(f"Temperature {t}: {len(zaehlung)} verschiedene "
          f"Antworten bei {DURCHLAEUFE} Durchläufen")
    for text, anzahl in zaehlung.most_common():
        print(f"   {anzahl}× {text}")
    print()
