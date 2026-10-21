# Selbst hosten

Ninedex braucht sehr wenig: einen Raspberry Pi 4 (2 GB reichen), einen Mini-PC, ein NAS mit Docker oder irgendeinen Rechner, der dauerhaft läuft. Die Texterkennung läuft im Browser, der Server hat nur wenig zu tun.

## 1. Lokal starten (ohne Docker)

```bash
pip install -r requirements.txt
python app.py                # http://localhost:5000
```

Umgebungsvariablen: `DB_PATH` (Datenbankdatei), `HOST` (`127.0.0.1` oder `0.0.0.0`), `PORT`. Mit `HOST=0.0.0.0 python app.py` ist die App von anderen Geräten im Netzwerk erreichbar.

## 2. Docker

```bash
docker compose up -d --build        # http://localhost:5000, Daten in ./data
```

Die Compose-Datei veröffentlicht den Port nur auf `127.0.0.1`. Für den Zugriff von anderen Geräten änderst du `"127.0.0.1:5000:5000"` in `"5000:5000"`. **Es gibt keinen Login, stelle den Port nie ins Internet.**

## 3. Raspberry Pi

1. Ein 64-Bit-Raspberry-Pi-OS installieren, danach Docker: `curl -fsSL https://get.docker.com | sh` und `sudo usermod -aG docker $USER` (neu anmelden).
2. `git clone https://github.com/askyonex/ninedex.git && cd ninedex`
3. `docker compose up -d --build`

Der Container startet nach einem Neustart von selbst (`restart: unless-stopped`).

Hinweis: Das Docker-Image installiert `openpyxl` und `pillow` (aus `requirements.txt`) für den Excel-Export. Ohne sie läuft alles andere, nur der Knopf *Excel mit Bildern* meldet die fehlenden Pakete.

## 4. HTTPS (nötig für die Kamera am Handy und an anderen Rechnern)

Browser erlauben den Kamerazugriff nur auf `https://`-Seiten oder auf `localhost`. Zu Hause geht das einfach mit Caddy und einer eigenen kleinen Zertifizierungsstelle.

1. **DNS-Name:** lege einen lokalen DNS-Eintrag an, der einen Namen wie `ninedex.home.arpa` auf die IP deines Servers zeigen lässt (Router, Pi-hole, AdGuard Home ...). Nutze nicht `.local`.
2. **Caddy:** kopiere `docs/examples/docker-compose.https.yml` und `docs/examples/Caddyfile.example` neben die Dockerfile (die zweite Datei in `Caddyfile` umbenennen, Namen anpassen) und starte `docker compose -f docker-compose.https.yml up -d --build`.
3. **Zertifikat auf jedem Gerät vertrauen.** Root-Zertifikat exportieren:
   ```bash
   docker compose -f docker-compose.https.yml exec caddy cat /data/caddy/pki/authorities/local/root.crt > caddy-root.crt
   ```
   Gib **nur `root.crt` weiter, niemals `root.key`.**
   - **iPhone / iPad:** Datei in *Safari* öffnen (z. B. per AirDrop oder einem kurzen `python3 -m http.server` im Ordner), Profil zulassen, in den *Einstellungen* installieren und unter *Einstellungen > Allgemein > Info > Zertifikatsvertrauenseinstellungen* aktivieren.
   - **Android:** *Einstellungen > Sicherheit > Verschlüsselung & Anmeldedaten > Zertifikat installieren > CA-Zertifikat*.
   - **macOS:** Doppelklick, zum Schlüsselbund hinzufügen, auf *Immer vertrauen* stellen.
   - **Windows:** Doppelklick, *Zertifikat installieren*, in *Vertrauenswürdige Stammzertifizierungsstellen* (lokaler Computer) speichern, Browser neu starten.
4. `https://ninedex.home.arpa` öffnen. Es darf keine Warnung erscheinen.

Nimm das Volume `caddy_data` in deine Backups auf. Geht es verloren, erzeugt Caddy eine neue Zertifizierungsstelle und das Zertifikat muss auf allen Geräten neu installiert werden.

**iPhone und "Website nicht erreichbar":** verteilt der Router einen eigenen IPv6-DNS, fragt iOS womöglich ihn statt deines lokalen DNS und kann den Namen nicht auflösen. In *Einstellungen > WLAN > (i) > DNS konfigurieren > Manuell* trägst du nur deinen lokalen DNS-Server ein.

## 5. Als App auf den Home-Bildschirm

Öffne die HTTPS-Adresse am iPhone in **Safari**, tippe auf *Teilen > Zum Home-Bildschirm*. Die App öffnet im Vollbild mit eigenem Symbol. (Android: Browser-Menü > *App installieren* / *Zum Startbildschirm hinzufügen*.) Die Kameraabfrage kann bei jedem Start erneut kommen, das ist iOS-Verhalten. Außerhalb deines Netzwerks funktioniert es nur mit einem VPN.

## 6. Backups

Deine ganze Sammlung ist eine SQLite-Datei (`data/pokedex.db`). Drei Wege zur Sicherung:

- **In der App:** *Statistik > Datenbank sichern* lädt eine konsistente Kopie herunter.
- **Skript:** `scripts/backup.sh` erstellt täglich eine Sicherung (auch bei laufender App) und kopiert sie optional auf eine eingebundene Netzwerkfreigabe. Beispiel für einen Cronjob (täglich 3:15 Uhr):
  ```
  15 3 * * * DB_FILE=/home/pi/ninedex/data/pokedex.db BACKUP_DIR=/home/pi/ninedex/backups /home/pi/ninedex/scripts/backup.sh
  ```
  Für eine NAS-Freigabe ergänzt du `NAS_MOUNT=/mnt/nas` (und bindest sie ein, z. B. mit einem `/etc/fstab`-Eintrag mit `cifs` und `credentials=`). Ist die Freigabe von root eingebunden, lass den Cronjob als root laufen.
- **Wiederherstellen:** App beenden, ein Backup über `data/pokedex.db` kopieren, App starten.

## 7. Aktualisieren

```bash
git pull
docker compose up -d --build
```

Datenbank-Änderungen werden beim Start automatisch eingespielt. Beim ersten Start nach einem Update füllt die App eventuell im Hintergrund neue Daten nach (Preise, Bilder, Kategorien), der Fortschritt steht in der Kopfleiste.

## 8. Zwei Datenbanken zusammenführen

Sind zwei Kopien der Datenbank auseinandergelaufen (z. B. eine Testkopie am PC), führst du sie in einer Kopie der Haupt-Datenbank zusammen:

```bash
python merge_db.py quelle.db ziel.db            # Vorschau
python merge_db.py quelle.db ziel.db --apply    # schreibt in ziel.db, vorher wird ein Backup angelegt
```

## 9. Fehlersuche

| Problem | Lösung |
| --- | --- |
| Kamera startet nicht | Braucht HTTPS oder `localhost` (Abschnitt 4). Kamera-Berechtigung des Browsers prüfen |
| Browser meldet "Website nicht erreichbar" | Der DNS-Name wird auf diesem Gerät nicht aufgelöst (Abschnitt 4, iPhone-Hinweis) |
| Zertifikatswarnung | Root-Zertifikat ist auf diesem Gerät nicht installiert oder nicht vertraut |
| Preise zeigen "–" | *Preise aktualisieren* klicken. Einzelne Karte prüfen: `/api/pricecheck?lang=de&id=<Karten-ID>` |
| Karten ohne Bild | `/api/imgcheck?lang=ja&set=<Set-ID>` zeigt, ob die Ersatzquelle das Set kennt |
| Ein Set fehlt in der Sets-Ansicht | `/api/seriesdebug?lang=ja` listet die Serien und ob sie aufgenommen wurden |
| "database is locked" | Selten bei mehreren Nutzern, die App wartet bis zu 30 Sekunden. Stelle sicher, dass nur eine App-Instanz die Datei nutzt |
| Nach einem Update alte Version | Mit Strg+F5 neu laden, die Home-Bildschirm-App entfernen und neu hinzufügen |

## 10. Sicherheits-Checkliste

- Kein Login: im Heimnetz lassen oder hinter eine eigene Anmeldung stellen.
- Veröffentliche weder deine `pokedex.db` noch Caddys `root.key`.
- Der Server kontaktiert TCGdex, PokeAPI und tcgcsv.com, dein Browser lädt Schriften von Google Fonts und Tesseract.js von jsDelivr.
