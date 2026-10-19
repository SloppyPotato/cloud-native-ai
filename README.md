# Übung 1 - Das Modell als Baustein

Cloud-native AI, WS 26/27, P1

## Start

```
cp .env.example .env
docker compose up --build app
```

Die `.env` ist einfach eine kopie der `.env.example`, da muss man nix ändern. Dann läuft alles lokal über ollama mit `llama3.2:3b`. Beim ersten start dauert es ein paar minuten, weil die modelle (ca. 2,4 GB) erst runtergeladen werden.

## Teil 1 - Setup

Es laufen drei container: `ollama` (der modellserver mit OpenAI-kompatibler API unter `/v1`, port 11434, die modelle liegen im volume `ollama-modelle`), `modell-laden` und unsere python-`app`. `modell-laden` läuft bei jedem start kurz mit, sagt dem ollama-server über `OLLAMA_HOST=ollama:11434` dass er `llama3.2:3b` und `qwen2.5:0.5b` ziehen soll (wirklich runtergeladen wird nur beim ersten mal) und beendet sich dann, erst danach startet `app`. Die app findet das modell nur über umgebungsvariablen: compose lädt die `.env` per `env_file` in den container und `llm.py` bzw. `hallo_llm.py` bauen daraus den OpenAI-client. `LLM_BASE_URL=http://ollama:11434/v1` sagt wo der server ist (den namen `ollama` löst docker im compose-netz auf) und `LLM_MODEL` welches modell, im code steht keins.

Drei fragen an `llama3.2:3b`. Gemessen haben wir erst nach einem warmup-aufruf, sonst ist die TTFT durchs laden vom modell verfälscht.

| Frage | TTFT (ms) | Gesamt (ms) |
|---|---|---|
| Wie melde ich mich zu einer Prüfung an? | 251 | 30178 |
| Wann hat die Mensa geöffnet? | 378 | 6347 |
| Wie kann ich die Leihfrist für ein Buch in der Bibliothek verlängern? | 313 | 23354 |

Die TTFT liegt hier bei ca. 0,25-0,38 s (mit wiederholungen siehe teil 2). Das ist im wesentlichen die zeit, in der das modell den prompt einliest (prefill). Danach wird token für token generiert (decode), deshalb hängt die gesamtdauer fast nur an der länge der antwort: llama schafft bei uns ca. 34-42 zeichen pro sekunde. Ollama läuft bei uns komplett auf der CPU (`ollama ps` zeigt 100% CPU), mit GPU wärs schneller.

## Teil 2 - Modell tauschen

Modell nur über die config getauscht, am code nix geändert. Beim messen haben wir `LLM_MODEL=qwen2.5:0.5b` per `docker compose run --rm -e LLM_MODEL=qwen2.5:0.5b app hallo_llm.py "..."` gesetzt. Das `-e` überschreibt den wert aus der `.env`, kommt also aufs selbe raus wie die zeile in der `.env` zu ändern.

| Frage | Modell | TTFT (ms) | Gesamt (ms) | Antwort brauchbar? |
|---|---|---|---|---|
| Prüfung anmelden | llama3.2:3b | 251 | 30178 | so halb. allgemeine schritte (portal, rechtzeitig anmelden), schritt 3 passt nicht, nix htwg-spezifisches |
| Prüfung anmelden | qwen2.5:0.5b | 91 | 7324 | nein, wirres zeug, sogar kaputter text (`<Member: name>`) |
| Mensa geöffnet | llama3.2:3b | 378 | 6347 | nein, keine öffnungszeiten, dafür erfundenes zeug (kostenloses essen, ZHAW) |
| Mensa geöffnet | qwen2.5:0.5b | 118 | 528 | nein, frage falsch verstanden ("wurde am 16. April 1971 geöffnet") |
| Leihfrist verlängern | llama3.2:3b | 313 | 23354 | nein, erfundene fristen (verlängerung 3 tage usw.) |
| Leihfrist verlängern | qwen2.5:0.5b | 117 | 2585 | nein, sehr allgemein und teils kein sinnvolles deutsch |

qwen ist deutlich schneller (siehe unten), dafür sind die antworten noch schlechter. Wirklich brauchbar ist keine, beide modelle kennen die htwg nicht und erfinden einfach details dazu.

Beim ersten aufruf nach dem wechsel hatte qwen übrigens 1734 ms TTFT, weil das modell erst geladen wird. Deshalb haben wir erst ab dem 2. aufruf gemessen.

Weil eine messung pro frage nicht viel aussagt, haben wir jede frage später nochmal 3x laufen lassen. TTFT in ms (erste zahl = messung aus der tabelle, dann die 3 wiederholungen):

| Frage | llama3.2:3b | qwen2.5:0.5b |
|---|---|---|
| Prüfung anmelden | 251, 214, 166, 149 | 91, 98, 58, 55 |
| Mensa geöffnet | 378, 260, 132, 133 | 118, 78, 57, 58 |
| Leihfrist verlängern | 313, 275, 184, 155 | 117, 98, 55, 56 |

Die TTFT schwankt also etwas, ist aber immer klein: llama ca. 0,13-0,38 s, qwen ca. 0,06-0,12 s. Bei den wiederholungen war der erste aufruf einer frage immer am langsamsten, die nächsten waren schneller. Das passt zum prefill: ollama hat den gleichen prompt vermutlich noch im cache und muss ihn nicht nochmal komplett einlesen.

Die gesamtdauer schwankt viel stärker (llama bei der prüfungsfrage zwischen 16,8 und 30,2 s), weil `hallo_llm.py` keine temperature setzt und die antworten jedes mal anders lang sind. Pro zeichen gerechnet ist es stabil. Bei antworten über 300 zeichen schafft llama ca. 34-42 zeichen pro sekunde, qwen ca. 155-190, also rund 4-5x so viel.

**HTWG privat oder staatlich?**

- llama: "Die Hochschule für Technik und Wirtschaft Konstanz (HTWG) ist eine staatliche Hochschule in Deutschland." Staatlich stimmt, aber der name ist falsch, die Gestaltung fehlt (HTWG = Hochschule Konstanz Technik, Wirtschaft und Gestaltung).
- qwen: "Es befindet sich die HTWG Konstanz in Konstanz. Die Hochschule hat eine öffentliche Bedeutung und stellt sicher, dass es ihre Schulgebiete und Sportteams verwaltet." Beantwortet die frage gar nicht.

Was auffällt: beide klingen total überzeugt, auch wenn es falsch ist. Bei qwen merkt man es sofort, bei llama fällt der falsche name nur auf wenn man ihn kennt.

Academic Cloud (optional) haben wir weggelassen, weil wir keinen key haben.

## Teil 3 - Sampling und Tokens

Wieder mit `llama3.2:3b`.

### Sampling

Kurz zur mechanik: das modell gibt für jedes mögliche nächste token einen wert aus (logit). Die logits werden durch die temperature geteilt und per softmax zu wahrscheinlichkeiten gemacht, daraus wird dann gezogen. Kleines T macht die verteilung spitzer (T → 0 heißt immer das wahrscheinlichste token), großes T macht sie flacher, dann kommen auch unwahrscheinlichere tokens dran.

`sampling.py` mit dem standard-prompt (name für ein neues mensa-gericht):

| Temperature | verschiedene Antworten (von 5) |
|---|---|
| 0.0 | 1 (5x "Sonnenblume") |
| 0.7 | 3 |
| 1.2 | 5 |

Bei temperature 0 kam hier wirklich 5x dasselbe raus. Garantiert ist das aber nicht. Bei 0 wird zwar immer das wahrscheinlichste token genommen, aber die wahrscheinlichkeiten werden nicht jedes mal bitgenau gleich berechnet. Das liegt an gleitkomma-rundungen, und die hängen davon ab wie parallel bzw. in welchen batches gerechnet wird (auf einer GPU auch zusammen mit anderen anfragen). Wenn zwei tokens fast gleich wahrscheinlich sind, kann das kippen und ab da läuft die antwort anders weiter.

Das haben wir in teil 4 auch gesehen: ohne response_format war bei T 0 die 2. antwort manchmal anders als die 1., die 3. aber immer gleich wie die 2. Wir hatten den prompt-cache von ollama im verdacht und das mit der eduroam-mail getestet: nach einer anderen mail kommt antwort A, direkt 2x wiederholt kommt B und B, nach einer anderen mail wieder A. Die antwort hängt also davon ab, ob ollama den prompt schon komplett im cache hat oder neu einliest, dabei wird minimal anders gerechnet. Bei so kurzen antworten wie hier fällt das nicht auf.

Faktenfrage `Ist die HTWG Konstanz eine private oder staatliche Hochschule? Antworte mit einem Satz.` (1 / 3 / 3 verschiedene antworten bei T 0 / 0.7 / 1.2):

- T 0: 5x "Die Hochschule für Technik und Wirtschaft (HTWG) Konstanz ist eine staatliche Hochschule."
- T 0.7: 3x "Die HTWG Konstanz ist eine staatliche Hochschule.", 1x wie bei T 0, 1x "Hochschule für Technologie, Wirtschaft und Geisteswissenschaften (HTWG)"
- T 1.2: 3x "Die HTWG Konstanz ist eine staatliche Hochschule.", 1x "Hochschule für Technologie, Wirtschaft und Gesellschaft Konstanz (HTWG)", 1x "Hochschule für Technologie und Wirtschaft Konstanz"

Staatlich stimmt immer. Aber sobald das modell den namen ausschreibt ist er falsch, "Gestaltung" kommt nie vor. Der fehler bei T 0 kommt aus dem was das modell gelernt hat (trainingsdaten): bei T 0 gibt es keinen zufall, das modell nimmt immer das jeweils wahrscheinlichste token und schreibt trotzdem den falschen namen. Bei höheren temperaturen kommen neue falsche varianten dazu (Technologie, Geisteswissenschaften, Gesellschaft). Die kommen vom sampling, weil dann auch unwahrscheinlichere tokens gezogen werden. Sampling macht also zusätzliche fehler, das grundproblem ist aber dass das modell den namen nicht kennt.

### Tokens

Original-texte: deutsch 63 tokens, englisch 49 tokens, beide 21 wörter. Deutsch braucht also 14 tokens mehr, laut skript +29%.

Die 29% sind aber mit den steuer-tokens vom chat-format gerechnet. Ein prompt mit nur einem wort ("a") ergibt 26 tokens, also sind ca. 25 tokens overhead. Ohne den overhead sind es 38 zu 24 tokens, also eher +58%.

Dann haben wir die texte in `tokens.py` durch eine frage mit langen wörtern ersetzt (Prüfungsanmeldungsfrist, Wiederholungsklausur, Bachelorstudiengang, Rücktrittsformular). Ergebnis: deutsch 71 tokens für 16 wörter, englisch 55 tokens für 25 wörter. Das sind 16 tokens mehr, wieder +29% (ohne overhead 46 zu 30, ca. +53%).

Der unterschied wird also nicht wirklich größer. Pro wort ist deutsch zwar viel teurer (ohne overhead ca. 2,9 tokens pro wort, vorher 1,8), aber englisch braucht für denselben inhalt einfach mehr wörter (Prüfungsanmeldungsfrist = exam registration deadline). Das gleicht sich fast aus.

Warum deutsch überhaupt teurer ist: der tokenizer (BPE) hat sein vokabular aus überwiegend englischen texten gelernt. Häufige englische wörter sind meist ein einzelnes token, deutsche wörter und vor allem lange komposita werden in mehrere stücke zerlegt.

## Teil 4 - Einordnen

Der code ist in `app/einordnen.py`, mit temperature 0 (begründung steht im code und unten bei der reflexion). Bei einer ungültigen antwort wird neu gefragt, höchstens 3 versuche insgesamt, danach kommt ein `RuntimeError`. Außerdem ist `max_tokens` auf 200 begrenzt, damit sich das modell nicht endlos verrennen kann (siehe 5.).

```
docker compose run --rm app einordnen.py
docker compose run --rm app einordnen.py "Eure eigene Mail"
```

**1. Trefferquote (anliegen)**

| Modell | Anliegen richtig |
|---|---|
| llama3.2:3b | 7 von 8 |
| qwen2.5:0.5b | 3 von 8 |

Wir haben es mehrmals laufen lassen, es kam immer dasselbe raus.

**2. Fehler**

llama hat nur ein falsches anliegen: die IEEE-Xplore-mail ("Geht das über die Bib?") wird `pruefung` statt `bibliothek`, wahrscheinlich wegen dem wort "Bachelorarbeit". Studiengang (AIN) und frist passen da aber. Die anderen fehler von llama sind bei studiengang und frist (siehe 3.).

qwen sagt fast immer `pruefung` und `AIN`, auch bei mensa, eduroam, dem gedicht und sogar bei der MSI-mail. 2 der 3 treffer sind also eher zufall, weil da halt wirklich pruefung stimmt. Dazu kommen erfundene jahreszahlen bei der frist (`30.10.2023`, `24.10.2023`, `10.10.2023 - 31.10.2023`) und einmal `3. Semester` als frist. Bei qwen ist also beides falsch, anliegen und studiengang/frist.

**3. "null" als text und erfundene fristen**

Ja, beides. llama gibt bei der eduroam-mail und der gedicht-mail `"studiengang": "null"` und `"frist": "null"` als text zurück, qwen einmal `"frist": "null"`. Bei der MSI-mail ("Bis wann geht das?") erfindet llama die frist `"bis zum 15.04.2024"`, die steht nirgends in der mail.

Das schema lässt das durch, weil es nur die form prüft: `studiengang` und `frist` sind "string oder null", und `"null"` oder `"bis zum 15.04.2024"` sind halt gültige strings. Ob der inhalt stimmt oder überhaupt in der mail steht, kann das schema nicht wissen.

**4. Die letzte mail (prompt injection)**

Mit response_format kommt kein gedicht, weil die ausgabe ins schema gezwungen wird. llama ordnet die mail als `sonstiges` ein (mit den "null"-strings), qwen als `pruefung`/`AIN`. Ohne response_format (siehe 5.) schreibt llama aber tatsächlich das gedicht über konstanz.
Das problem ist, dass anweisungen und daten (die mail) im selben text beim modell landen und es die beiden nicht sicher auseinanderhalten kann. Das schema schützt nur die form, eine mail könnte trotzdem versuchen z. b. ein bestimmtes anliegen zu erzwingen.

**5. Ohne response_format**

Wir haben testweise ohne `response_format` laufen lassen (nur system-prompt, temperature 0) und die rohantwort ausgegeben. Ergebnis: bei beiden modellen 0 von 8 antworten gültig.
- llama: packt das json 3x in einen \`\`\`-codeblock (dann ist es kein gültiges json mehr), schreibt meistens `studienengang` statt `studiengang`, schreibt `anliegen` groß oder nimmt irgendwas eigenes ("Mensa", "Klausur", "IEEE Xplore"), erfindet zusatzfelder, beantwortet bei eduroam einfach die frage (mit erfundener url) und schreibt bei der letzten mail das gedicht.
- qwen: immer ein \`\`\`json-block, `anliegen` fehlt immer, und meistens beantwortet es die mail statt sie einzuordnen. Bei der gedicht-mail wiederholt es endlos denselben satz. Ohne `max_tokens` hat das bei uns 10 min generiert, bis der request abgebrochen ist.

Ein erneuter versuch bringt bei T 0 nix: gleiche eingabe und immer das wahrscheinlichste token heißt (fast) dieselbe antwort. Bei llama waren die wiederholungen bei 5 von 8 mails komplett identisch, bei den anderen 3 etwas anders, aber genauso ungültig. Was man ändern könnte:
- beim retry die fehlermeldung mit in den nächsten versuch geben, dann ist die eingabe anders und das modell kann den fehler korrigieren
- beim retry die temperatur hochsetzen
- ein beispiel-json in den prompt schreiben oder codeblöcke im code wegschneiden

Am sinnvollsten ist aber einfach response_format, das ist jetzt auch wieder drin.

## Zusatz - Ausgaben absichern

Auch in `app/einordnen.py`:
- `Anfrage` hat jetzt `field_validator`s: `"null"`, `"None"` und `""` werden bei studiengang und frist zu echtem `None`.
- studiengang ist nur gültig, wenn das kürzel in `STUDIENGAENGE` steht (AIN, WIN, GIB, MSI, BIT, also die studiengänge der fakultät informatik), sonst `None`. "ain" wird zu "AIN".
- die frist wird im code gegen die mail geprüft: steht sie nicht in der mail, gibts eine warnung und sie wird `None`. Groß/klein, kommas usw. und ein punkt am ende sind dabei egal, es zählen aber nur ganze wörter (sonst würde z. b. "6.10." in "16.10." gefunden).
- `auswerten()` fragt das modell pro mail nur einmal und bewertet dieselbe antwort einmal ohne prüfungen (`AnfrageOhneZusatz`, so wie vorgegeben) und einmal mit. So hängt der vergleich nicht von zwei verschiedenen modellantworten ab.

Alle drei felder richtig (anliegen und studiengang exakt, frist richtig wenn die erwartete frist im ergebnis enthalten ist, bzw. `None` wenn keine erwartet wird):

| Modell | vorher | nachher |
|---|---|---|
| llama3.2:3b | 4 von 8 | 7 von 8 |
| qwen2.5:0.5b | 0 von 8 | 0 von 8 |

Bei llama werden die zwei "null"-fälle und die erfundene frist (`bis zum 15.04.2024`) repariert. Übrig bleibt nur die IEEE-mail, wo schon das anliegen falsch ist. Bei qwen bringt es nix, da ist fast immer schon anliegen oder studiengang falsch. Die validatoren können nur offensichtlichen müll rauswerfen, aber keinen falschen gültigen wert korrigieren (AIN statt MSI ist halt ein gültiges kürzel). Und der frist-check schaut nur ob der text in der mail vorkommt, `3. Semester` als frist geht deshalb durch.

Beim testen mit einer eigenen mail ("... Anmeldeschluss ist doch Montag 26.10. oder?") ist uns noch aufgefallen, dass das modell "Montag, 26.10." mit komma zurückgibt. Mit einem stumpfen textvergleich wäre die richtige frist rausgeflogen. Deshalb werden kommas und andere satzzeichen beim vergleich ignoriert (nur punkte im datum nicht).

## Reflexion

**Warum steht das Modell in .env und nicht im Code?**
Damit das modell ein austauschbarer baustein bleibt. Modell wechseln oder von lokal auf cloud gehen ist dann nur config, kein code ändern und kein neuer build (haben wir in teil 2 ja so gemacht). Außerdem gehört der API-key nicht ins repo, und die `.env` ist in der `.gitignore`.

**Welche Temperature in einordnen.py und warum?**
0. Wir wollen nur daten aus der mail rausziehen, da soll nix kreatives passieren. Bei 0 wird immer das wahrscheinlichste token genommen, dadurch ist das ergebnis praktisch reproduzierbar (bitgenau garantiert ist es nicht, siehe teil 3) und die auswertung vergleichbar. Nachteil: ein neuer versuch bringt bei 0 meistens genau dieselbe antwort.

**Was garantiert response_format mit Schema, und was nicht?**
Es garantiert die form: gültiges JSON mit den feldern aus dem schema, den richtigen typen und bei `anliegen` nur die erlaubten werte (ollama schränkt dafür die ausgabe schon beim generieren ein). Es garantiert nicht, dass der inhalt stimmt. Falsches anliegen, `"null"` als text oder eine erfundene frist gehen also trotzdem durch. Und das klappt natürlich nur, wenn der anbieter das schema auch unterstützt.

**Lokales Modell oder Cloud?**
Lokal: wenn datenschutz wichtig ist (die mails von studis verlassen den rechner nicht) und wenn man unabhängig sein will, also keine kosten pro token und es läuft auch wenn der dienst down ist oder kein internet da ist. Cloud: wenn man ein großes modell braucht, die kleinen lokalen modelle machen einfach viele fehler (siehe teil 2). Und wenn man keine eigene GPU-hardware hat bzw. sich nicht selbst ums betreiben und skalieren kümmern will.
