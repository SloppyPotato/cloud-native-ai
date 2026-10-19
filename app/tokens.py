"""Teil C: Wie viele Tokens kostet derselbe Inhalt auf Deutsch und Englisch?

Die API meldet in usage.prompt_tokens, wie viele Tokens die Eingabe hatte.
Darin stecken auch einige Steuer-Tokens des Chat-Formats, bei beiden
Sprachen gleich viele. Für den Vergleich zählt deshalb die Differenz.

Aufruf:
    docker compose run --rm app tokens.py
"""

from llm import MODEL, client

TEXTE = {
    "Deutsch": "Wie melde ich mich im Studiengang Angewandte Informatik "
               "für die Prüfung in Mathematik 3 an, und bis wann ist "
               "die Anmeldefrist?",
    "Englisch": "How do I register for the Mathematics 3 exam in the "
                "Applied Computer Science program, and what is the "
                "registration deadline?",
}


def eingabe_tokens(text: str) -> int:
    antwort = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": text}],
        max_tokens=1,
    )
    return antwort.usage.prompt_tokens


print(f"Modell: {MODEL}\n")
ergebnis = {}
for sprache, text in TEXTE.items():
    ergebnis[sprache] = eingabe_tokens(text)
    print(f"{sprache:9} {ergebnis[sprache]:3} Tokens "
          f"für {len(text.split())} Wörter")
mehr = ergebnis["Deutsch"] - ergebnis["Englisch"]
print(f"\nDeutsch braucht {mehr} Tokens mehr "
      f"({ergebnis['Deutsch'] / ergebnis['Englisch'] - 1:+.0%}).")
