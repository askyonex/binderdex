# Grading-Check (Vorab-Einschätzung)

Eine **Schätzung**, welche Note eine Karte bei PSA oder ähnlichen Firmen bekommen könnte, plus eine Rechnung, ob sich das Einschicken lohnt. Kein Ersatz für die echte Bewertung und nicht mit PSA verbunden.

## Was verlässlich ist und was nicht

| Teil | Wie | Verlässlichkeit |
| --- | --- | --- |
| **Zentrierung** | du misst sie am Foto mit verschiebbaren Linien, die App wendet die veröffentlichten PSA-Grenzen an | **objektiv und gut**, wenn die Linien sauber sitzen (eine Lupe hilft). Moderne Pokémon-Ränder sind nur etwa 2 bis 3 mm breit, jeder Pixel zählt |
| **Ecken, Kanten, Oberfläche, Druck** | die Bild-KI beurteilt deine Fotos (inklusive Ecken-Ausschnitten) | **grobe Schätzung**: Kratzer, Dellen und feine Druckfehler sieht man auf Handyfotos schlecht, Hüllen und Spiegelung verdecken vieles |
| **Gesamtnote** | Zentrierung und Teilnoten werden zusammengeführt ("der schwächste Punkt bestimmt") | als **Spanne** mit Sicherheit. Eine 10 wird nur bei sauberen, scharfen Fotos ohne Hülle und Spiegelung vorhergesagt |

## Ablauf

1. Öffnen über das Menü (*Grading-Check*) oder über den Knopf *Grading* bei einer Karte in einer Kartenliste (Name und Rohwert sind dann eingetragen).
2. **Fotos:** mit der Kamera des Geräts (hohe Auflösung) aufnehmen oder aus der Galerie wählen. Vorderseite Pflicht, Rückseite optional.
3. **Zentrierung messen:** die **blauen** Linien an den äußeren Kartenrand, die **gelben** an den inneren Rand des Rahmens (wo das Bild beginnt) ziehen. Beim Ziehen zeigt eine Lupe den Ausschnitt. Bei Karten ohne Rand (Fullart): Häkchen *Zentrierung nicht messbar*.
4. **Einschätzen:** mit eingerichteter KI-Hilfe (siehe [ki-scan.md](ki-scan.md)) gehen das Foto und vier Ecken-Ausschnitte je Seite an das Modell, ohne KI wird nur die Zentrierung ausgewertet.
5. **Ergebnis:** Note mit Namen (z. B. PSA 8 NM-MT), Spanne, Sicherheit und **was am meisten bremst**. Die Teilnoten (Ecken, Kanten, Oberfläche, Druck; 1 bis 10, halbe Punkte) kannst du ändern und neu berechnen, um die KI zu korrigieren oder ganz ohne sie zu arbeiten.
6. **Lohnt es sich?** Grading-Kosten und Marktpreise für graduierte Exemplare (PSA 7, 8, 9, 10) eingeben. Die App kennt keine Preise für graduierte Karten, nimm Richtwerte, z. B. aus verkauften eBay-Artikeln. Sie zeigt Wahrscheinlichkeit, Wert und Gewinn je Note, den erwarteten Gewinn gegenüber dem Rohverkauf, die Break-even-Note und ein Fazit. Die Wahrscheinlichkeiten sind eine grobe Annahme um die geschätzte Note.
7. **Speichern** als Grading-Kandidat, die Liste *Gespeichert* ist nach Note sortiert.

## Verwendete Zentrierungsgrenzen (veröffentlichte PSA-Werte, ungefähr)

Es zählt der schlechtere Wert aus links/rechts und oben/unten (Prozent der breiteren Randseite).

| Note | Vorderseite | Rückseite |
| --- | --- | --- |
| PSA 10 | bis 55/45 | bis 75/25 |
| PSA 9 | bis 60/40 | bis 90/10 |
| PSA 8 | bis 65/35 | bis 90/10 |
| PSA 7 | bis 70/30 | bis 90/10 |
| PSA 6 | bis 80/20 | |
| PSA 5 | bis 85/15 | |
| PSA 3 | bis 90/10 | |

Prüfe die aktuellen Grenzen vor einer Einsendung auf der Seite der Grading-Firma, sie können sich ändern.

## Foto-Tipps

Normale Kamera-App (nicht das Scan-Video), Tageslicht oder gleichmäßiges Licht ohne Blitz, keine Spiegelung (Karte kippen, mehrmals fotografieren), einfarbiger Untergrund mit Kontrast zur Karte, **keine Hülle und kein Toploader**, Kamera gerade über der Karte.

## Welche KI?

Den Zustand zu beurteilen ist schwerer als eine Kartennummer zu lesen. Google Gemini (Flash) liefert meist bessere Ergebnisse, ein lokales Modell über Ollama (z. B. `qwen3-vl:8b`) ist gröber und braucht bei vielen Bildern länger. Siehe [ki-scan.md](ki-scan.md). Bei der kostenlosen Gemini-Stufe kann Google die Bilder zur Produktverbesserung nutzen.
