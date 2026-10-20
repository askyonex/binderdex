# Binderdex

**Selbst gehostete Web-App, um deine Pokémon-Kartensammlung zu digitalisieren, zu bewerten und zu verwalten.**
Die Grundidee: **eine Karte pro Pokémon im Binder** (ein Pokédex aus Karten), alles andere landet im Nebenstapel, den du verkaufen oder tauschen kannst.

> **Inoffizielles Fan-Projekt.** Nicht mit The Pokémon Company, Nintendo, Creatures oder Game Freak verbunden oder von ihnen unterstützt. Siehe [Rechtliche Hinweise](#rechtliche-hinweise).
>
> English version: [README.md](README.md). Die App gibt es auf **Deutsch, Englisch und Spanisch**: Oberfläche, Pokémon-Namen und Pokédex-Einträge. Die Sprachen wählst du beim ersten Start (oder im Windows-Installer) und wechselst jederzeit in den Einstellungen.

Kein Konto, keine Cloud, kein API-Schlüssel. Die App läuft als Desktop-App unter Windows und macOS oder als Web-App auf deinem PC, einem Raspberry Pi oder einem kleinen Server, deine Daten liegen in einer einzigen SQLite-Datei.

## Funktionen

**Pokédex und Binder**
- **Deutsch, Englisch und Spanisch** (Oberfläche, Pokémon-Namen, Pokédex-Einträge, Exporte), pro Gerät umschaltbar; weitere Sprachen lassen sich mit einer Wörterbuch-Datei und wenigen Zeilen Code ergänzen ([docs/translating.md](docs/translating.md))
- Alle Pokémon in der Reihenfolge des Nationalen Pokédex mit Fortschrittsbalken, fehlende als Silhouette
- Pro Pokémon eine Karte im Binder. Kommt eine zweite, siehst du beide nebeneinander: *ersetzen* oder *in den Nebenstapel*
- Pokédex-Eintrag (Text aus den Spielen) und Kategorie zu jedem Pokémon, Favoriten (Stern), Filter (gefangen, fehlt, Favoriten, Generation, Fullart / kein Fullart) und Sortierung (Nummer, Preis, Anzahl der Karten)
- Statistik: Fortschritt pro Generation, Fullart-Anteil, Sprachen, Seltenheiten, teuerste Karten, Wertverlauf, Erfolge, "zufälliges fehlendes Pokémon"

**Karten eintragen**
- `147/196` eintippen: **Set und Sprache (Deutsch, Englisch, Japanisch) werden automatisch erkannt**
- **Kamera-Scan**, der die Kartennummer per Texterkennung **im Browser** liest (Tesseract.js), laufend mitliest, das schärfste Bild wählt und nach zwei gleichen Lesungen bestätigt. Funktioniert mit PC-Webcam oder der Rückkamera am Handy
- **Zwei geführte Modi** nach dem Hinzufügen: *nächste Karte im Set* oder *nächstes Pokémon im Pokédex mit allen seinen Karten* (komplette Datenbank, drei Sprachen)
- **+1 / −1** an jeder Karte (Sets-Ansicht, Nebenstapel, Pokémon-Fenster): ein ganzes Display in Sekunden durchzählen
- **Verkaufsliste mit Kartenbildern:** Excel-Datei mit eingebetteten Vorschaubildern (und Zustand), druckbare Verkaufsseite (als PDF speichern) und CSV mit Bild-Links
- **Optionale KI-Hilfe für die Kamera:** ein kostenloses Bildmodell (Ollama auf dem eigenen PC oder ein kostenloser Gemini-Schlüssel) liest die Karte aus dem Kamerabild, deutlich zuverlässiger als die Texterkennung allein; du bestätigst jede Karte weiterhin ([docs/ki-scan.md](docs/ki-scan.md))
- **Auf Cardmarket verkaufen:** Karten aus dem Nebenstapel mit Anzahl, Zustand und Preisvorschlag (Trend mit Prozent-Anpassung und Rundung) auswählen, ein Listing-Assistent führt mit direktem Cardmarket-Link und Kopier-Knöpfen durch jede Karte, gelistete und verkaufte Karten werden verwaltet (verkaufte Exemplare verlassen die Sammlung), dazu eine CSV für Massen-Werkzeuge. Die Cardmarket-API steht Privatverkäufern derzeit nicht zur Verfügung, es wird also nichts automatisch veröffentlicht ([docs/verkaufen.md](docs/verkaufen.md))
- **Grading-Check:** eine Vorab-Einschätzung der Note (PSA-Skala) per Foto: du misst die **Zentrierung** mit Linien und Lupe gegen die veröffentlichten PSA-Grenzen, die KI beurteilt Ecken, Kanten und Oberfläche, und die App zeigt eine **Notenspanne**, was am meisten bremst und ob sich das **Einschicken lohnt** (Kosten und Marktpreise gibst du ein). Nicht mit PSA verbunden, nur eine Schätzung ([docs/grading-check.md](docs/grading-check.md))
- **Pack-Session:** ein ganzes Display zählen und am Ende die Auswertung sehen (Gesamtwert, beste Karten, neue Pokémon)
- **Binder-Ansicht** Seite für Seite wie ein echter Binder (9 / 12 / 16 Fächer), mit Hinweis "Seite 3, Platz 7" beim Einsortieren
- **Preisbewegung** seit der letzten Aktualisierung (rauf / runter, größte Gewinner und Verlierer, Wunschkarten, die billiger wurden)
- **76 Erfolge** in 8 Gruppen mit Fortschrittsbalken und Hinweisen, Pokémon des Tages, ein "Wer ist das Pokémon?"-Quiz, 7 Farbdesigns und optionale Retro-Töne
- **Sets-Ansicht:** alle Sets ab 2017 auf Deutsch, Englisch und Japanisch (japanische Sets mit englischen Namen und Ersatzbildern), komplette Kartenlisten, Hinzufügen per Klick

**Preise, Verkaufen und Tauschen**
- Preise von Cardmarket (über TCGdex), pro Karte sowie für Binder und gesamte Sammlung
- **Varianten:** Normal, Reverse Holo, Holo und Pokéball-, Superball-, Hyperball- und Meisterball-Muster, dazu optional ein eigener Preis
- **Nebenstapel-Export zum Verkaufen:** CSV mit Name, Wert und Cardmarket-Link (auf Wunsch mit weiteren Spalten)
- Wunschliste, Tauschliste (was du abgeben kannst / was du suchst) als fertiger Text, CSV-Export der Sammlung und der fehlenden Pokémon, Datenbank-Download

**Sonstiges**
- Handy-tauglich mit Burger-Menü, installierbar als App auf dem Home-Bildschirm (PWA)
- Mehrere Personen / Geräte können dieselbe Instanz gleichzeitig nutzen
- Docker-Image, Backup-Skript (lokal und optional auf eine Netzwerkfreigabe), Werkzeug zum Zusammenführen von Datenbanken
- Retro-Pokédex-Design (Pixelschrift, rotes Gerät, dunkles LCD-Display)

## Download: Desktop-App (Windows / macOS)

Der einfachste Weg, ohne Python und ohne Terminal. Lade die Datei für dein System aus dem [neuesten Release](https://github.com/askyonex/binderdex/releases/latest):

| System | Datei |
| ------ | ----- |
| Windows 10 / 11 (64 Bit) | `BinderDex-Setup-x.y.z.exe` |
| Mac mit Apple-Chip (M1 oder neuer) | `BinderDex-x.y.z-macOS-arm64.dmg` |
| Mac mit Intel-Prozessor | `BinderDex-x.y.z-macOS-x86_64.dmg` |

**Windows:** Installer starten (keine Administratorrechte nötig). Da die App nicht signiert ist, zeigt Windows eventuell *„Der Computer wurde durch Windows geschützt"*: **Weitere Informationen → Trotzdem ausführen**.
**macOS:** DMG öffnen und BinderDex auf *Applications* (Programme) ziehen. Beim ersten Start blockiert macOS die App, weil sie nicht von Apple beglaubigt ist: **Systemeinstellungen → Datenschutz & Sicherheit**, nach unten scrollen, **Dennoch öffnen** (nur einmal nötig).

Der Installer fragt, welche Sprachen die App haben soll (Deutsch, Englisch, Spanisch). Die Desktop-App ist dieselbe App in einem eigenen Fenster, der Kamera-Scan funktioniert mit der Webcam. Deine Sammlung liegt pro Benutzer (Windows: `%APPDATA%\BinderDex`, macOS: `~/Library/Application Support/BinderDex`) und bleibt bei Updates und (wenn du willst) auch beim Deinstallieren erhalten. Die App meldet sich, wenn es eine neue Version gibt. Details: [docs/desktop-app.de.md](docs/desktop-app.de.md)

## Schnellstart

Voraussetzungen: Python 3.10+ und ein aktueller Browser. Eine Internetverbindung ist nötig (Kartendaten, Bilder, Preise).

```bash
git clone https://github.com/askyonex/binderdex.git
cd binderdex
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Dann <http://localhost:5000> öffnen. Beim ersten Start lädt die App die Pokémon-Namen und Pokédex-Einträge nach (ein paar Minuten, oben in der Kopfleiste sichtbar).

**Docker:**

```bash
docker compose up -d --build     # danach http://localhost:5000 öffnen
```

### Konfiguration (Umgebungsvariablen)

| Variable  | Standard       | Bedeutung |
| --------- | -------------- | --------- |
| `DB_PATH` | `pokedex.db`   | Pfad der SQLite-Datenbank (das Docker-Image nutzt `/data/pokedex.db`) |
| `HOST`    | `127.0.0.1`    | Adresse, auf der gelauscht wird (`0.0.0.0` für andere Geräte, das Docker-Image macht das) |
| `PORT`    | `5000`         | Port |

**Der Kamerazugriff braucht HTTPS** (oder `localhost`). Willst du die Kamera am Handy nutzen, musst du die App über HTTPS ausliefern, siehe [docs/selbst-hosten.md](docs/selbst-hosten.md).

## Dokumentation

- [Benutzerhandbuch](docs/benutzerhandbuch.md) / [User guide](docs/user-guide.md)
- [Selbst hosten (Docker, Raspberry Pi, HTTPS, Handy-App, Backups)](docs/selbst-hosten.md) / [Self-hosting](docs/self-hosting.md)
- [Desktop-App (Download, Datenordner, Release bauen)](docs/desktop-app.de.md) / [Desktop app](docs/desktop-app.md)
- [Mitmachen](CONTRIBUTING.md)

## Datenquellen und Dank

| Was | Quelle |
| --- | --- |
| Kartendaten, Bilder, Cardmarket-Preise, Sets (de / en / ja) | [TCGdex](https://tcgdex.dev) |
| Pokémon-Namen, Pokédex-Einträge, Artwork für die Silhouetten | [PokeAPI](https://pokeapi.co) |
| Englische Namen japanischer Sets, Ersatz-Kartenbilder | [TCGplayer-Daten über tcgcsv.com](https://tcgcsv.com) |
| Texterkennung im Browser | [Tesseract.js](https://github.com/naptha/tesseract.js) (Apache-2.0) |
| Backend | [Flask](https://flask.palletsprojects.com) (BSD-3-Clause) |
| Schriften | Press Start 2P und VT323 (SIL Open Font License) über Google Fonts |
| Verweise | Links zu Cardmarket (es werden keine Daten direkt von Cardmarket geholt) |

Die App speichert zwischen, was geht, und fragt in kleinen Paketen ab. Bitte beachte die Nutzungsbedingungen dieser Dienste und halte die Anfragen niedrig, wenn du eine öffentliche Instanz betreibst.

## Datenschutz und Sicherheit

- Deine Sammlung liegt in einer SQLite-Datei auf deinem Rechner. Es geht nichts nach außen, außer den Abfragen an die oben genannten Dienste (Kartennummern, Set-Codes, Pokédex-Nummern).
- Die optionale KI-Hilfe schickt Kamerabilder an den Dienst, den du wählst: an deinen eigenen PC mit Ollama (bleibt im Netzwerk) oder an Google mit einem Gemini-Schlüssel (die kostenlose Stufe darf Google zur Verbesserung seiner Produkte nutzen). Sie ist aus, bis du sie einrichtest.
- Dein Browser lädt die Schriften von Google Fonts und Tesseract.js von jsDelivr. Wenn dir das wichtig ist (z. B. bei einer öffentlichen Instanz in der EU), lade diese Dateien herunter und liefere sie selbst aus.
- Es gibt **keinen Login**. Wer die Seite öffnen kann, kann die Daten ändern. Betreibe die App im Heimnetz oder hinter einer eigenen Anmeldung und **stelle sie nie direkt ins Internet**.
- Die App nutzt den eingebauten Server von Flask. Für ein paar Nutzer zu Hause reicht das, für eine öffentliche Seite nicht.

## Bekannte Einschränkungen

- Karten-, Set-Namen und Seltenheiten englischer und japanischer Karten erscheinen wie aufgedruckt (deutsche Seltenheiten werden übersetzt)
- Die Nummernerkennung per Kamera hängt von Licht, Abstand und Kamera ab. Die Nummer manuell einzutippen geht immer
- Preise sind Richtwerte: Cardmarket-Trend über TCGdex, nicht sprachspezifisch, teils fehlend (besonders bei japanischen Karten). Ball-Muster haben keinen eigenen Preis, trage ihn bei Bedarf selbst ein
- Pro Karte gilt eine Variante (besitzt du dieselbe Karte als Normal und Reverse Holo, nutze den eigenen Preis oder behandle sie getrennt)
- Die Kartendaten sind so vollständig wie die von TCGdex / TCGplayer, ganz neue Sets können Lücken haben

## Roadmap

- Weitere Sprachen (Französisch, Italienisch, ...): Beiträge willkommen, siehe [docs/translating.md](docs/translating.md)
- Mehrere Sammlungen (Profile) in einer Instanz
- Preisalarm für Wunschkarten, Upgrade-Vorschläge (bessere Karte zu einem Pokémon)
- Selbst gehostete Schriften und OCR-Dateien (offline nutzbar, ohne CDN)
- Englische Code-Kommentare

## Rechtliche Hinweise

Pokémon sowie alle zugehörigen Namen, Figuren, Logos und Kartenmotive sind Marken und/oder urheberrechtlich geschützte Werke von The Pokémon Company, Nintendo, Creatures Inc. und GAME FREAK Inc. Dieses Projekt ist ein inoffizielles, nichtkommerzielles Fan-Werkzeug zur Verwaltung einer privaten Sammlung. **Es enthält keine Kartenbilder oder offizielles Artwork**, Bilder werden zur Laufzeit von Diensten Dritter geladen. Cardmarket und TCGplayer sind Marken ihrer jeweiligen Inhaber. Die Software wird ohne Gewähr bereitgestellt (siehe [LICENSE](LICENSE)). Das ist keine Rechtsberatung. Veröffentlichst du eine veränderte Version oder betreibst eine öffentliche Instanz, prüfe die Bedingungen der Datenanbieter selbst.

## Lizenz

[MIT](LICENSE) für den Quellcode.
