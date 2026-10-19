"""Live-Demo aus der Vorlesung: Streuung, Logprobs und Tokens.

Aufruf:
    docker compose run --rm app demo_sampling.py
"""

import math

from llm import MODEL, client, frage

print(f"Modell: {MODEL}\n")

# 1) Streuung: dieselbe Frage fünfmal bei zwei Temperaturen
prompt = ("Erfinde einen Namen für ein neues Gericht in der Mensa. "
          "Antworte nur mit dem Namen.")
for t in (0.0, 1.2):
    print(f"── Temperature {t}")
    for _ in range(5):
        print("  ", frage(prompt, temperature=t, max_tokens=30))
    print()

# 2) Logprobs: Wie sicher ist das Modell beim ersten Token?
print("── Logprobs für das erste Token der Antwort")
try:
    antwort = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content":
                   "Ergänze genau ein Wort und antworte nur "
                   "mit diesem Wort: Die HTWG Konstanz ist "
                   "eine"}],
        max_tokens=1, logprobs=True, top_logprobs=5,
    )
    for kandidat in antwort.choices[0].logprobs.content[0].top_logprobs:
        p = math.exp(kandidat.logprob)
        print(f"   {kandidat.token!r:18} {p:6.1%}")
except Exception as fehler:  # nicht jeder Anbieter liefert Logprobs
    print("   Logprobs nicht verfügbar:", fehler)
print()

# 3) Tokens: Deutsch gegen Englisch
print("── Eingabe-Tokens")
for text in ("Wie melde ich mich zur Prüfung in Mathematik 3 an?",
             "How do I register for the Mathematics 3 exam?"):
    antwort = client.chat.completions.create(
        model=MODEL, max_tokens=1,
        messages=[{"role": "user", "content": text}])
    print(f"   {antwort.usage.prompt_tokens:3} Tokens: {text}")
