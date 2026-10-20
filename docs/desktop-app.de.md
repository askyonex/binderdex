# Desktop-App (Windows / macOS)

English: [desktop-app.md](desktop-app.md)

Die Desktop-App ist die normale Binderdex-Web-App in einem eigenen Fenster. Das Flask-Backend läuft unsichtbar im Hintergrund und lauscht nur auf `127.0.0.1`, niemand sonst im Netzwerk kommt also daran. Unter Windows zeigt die Microsoft-Edge-WebView2 die Oberfläche an, unter macOS WebKit (die Technik von Safari).

## Installieren

Download aus dem [neuesten Release](https://github.com/askyonex/binderdex/releases/latest), siehe Tabelle in der [README](../README.de.md#download-desktop-app-windows--macos).

- **Windows 10 / 11:** `BinderDex-Setup-x.y.z.exe` starten (Installer auf Deutsch, Englisch oder Spanisch). Standardmäßig wird nur für den eigenen Benutzer installiert (keine Administratorrechte). Der Installer fragt, in welchen **Sprachen** die App verfügbar sein soll (Deutsch, Englisch, Spanisch, mehrere möglich) und mit welcher sie startet, bietet eine Desktop-Verknüpfung an und startet die App am Ende. Bei einem Update schlägt er die bisherige Auswahl vor.
  - *„Der Computer wurde durch Windows geschützt"* (SmartScreen) erscheint, weil die App nicht signiert ist: **Weitere Informationen → Trotzdem ausführen**.
  - WebView2 ist in Windows 11 und aktuellem Windows 10 enthalten. Fehlt es, bietet der Installer die Download-Seite von Microsoft an.
- **macOS 11 oder neuer:** DMG öffnen und BinderDex auf *Applications* (Programme) ziehen.
  - Erster Start: macOS meldet, die App könne *nicht auf Malware überprüft werden*. **Systemeinstellungen → Datenschutz & Sicherheit** öffnen, nach unten zur Meldung über BinderDex scrollen, **Dennoch öffnen** klicken und bestätigen. Nur einmal pro Version nötig.
  - Alternativ im Terminal: `xattr -dr com.apple.quarantine /Applications/BinderDex.app`
  - Macs mit Apple-Chip (M1 und neuer) nehmen das `arm64`-DMG, Intel-Macs das `x86_64`-DMG.

## Wo deine Daten liegen

| System | Ordner |
| ------ | ------ |
| Windows | `%APPDATA%\BinderDex` (in die Adressleiste des Explorers einfügen) |
| macOS | `~/Library/Application Support/BinderDex` (Finder: *Gehe zu → Gehe zum Ordner …*) |

Darin liegen `pokedex.db` (deine komplette Sammlung), `binderdex.log` (Protokoll, hilfreich bei Fehlermeldungen) und `webview/` (Einstellungen der Oberfläche wie Design und Töne).

- **Updates** lassen den Ordner unangetastet. Neue Version einfach über die alte installieren.
- **Deinstallieren unter Windows** fragt, ob der Ordner bleiben soll (Standard: behalten).
- **Sicherung:** Der Backup-Knopf in der App lädt eine Kopie der Datenbank herunter, oder `pokedex.db` bei geschlossener App kopieren.
- **Umzug von der Web-Version:** App schließen, `pokedex.db` im Ordner durch deine bestehende Datenbank ersetzen, App wieder starten.
- Eigener Ordner (z. B. auf einem NAS oder in einem synchronisierten Ordner): Umgebungsvariable `BINDERDEX_DATA_DIR` setzen.

## Gut zu wissen

- **Sprache:** wechseln unter *Einstellungen → Sprache*, Sprachen hinzufügen oder entfernen mit dem **…**-Knopf daneben. Unter macOS fragt die App beim ersten Start nach den Sprachen. Details: [translating.md](translating.md)
- Der **Kamera-Scan** funktioniert mit der Webcam. Windows und macOS fragen beim ersten Mal nach der Erlaubnis.
- **Links** (Cardmarket, Release-Seite) und die druckbare **Verkaufsseite** öffnen sich im normalen Browser. Die Verkaufsseite funktioniert dort, solange die App läuft.
- **Downloads** (Backup, Excel, CSV) öffnen einen Speichern-Dialog.
- Ein zweiter Start holt nur das offene Fenster nach vorn.
- Die App schaut bei jedem Start einmal bei GitHub nach einer neueren Version und zeigt dann einen kleinen Hinweis. Sonst wird nichts gesendet. Abschalten mit `BINDERDEX_NO_UPDATE_CHECK=1`.
- Die App nutzt den festen lokalen Port `47821` (damit Einstellungen der Oberfläche einen Neustart überleben). Belegt ein anderes Programm den Port, nimmt sie für diese Sitzung einen freien.
- **Zugriff vom Handy** gehört nicht zur Desktop-App. Dafür Binderdex auf einem Server oder Raspberry Pi betreiben ([selbst-hosten.md](selbst-hosten.md)).
- Die **KI-Hilfe für die Kamera** (Ollama) wird weiterhin separat installiert, siehe [ki-scan.md](ki-scan.md).

## Für Entwickler: starten, bauen, veröffentlichen

Aus dem Quellcode starten (im Repo-Ordner):

```bash
pip install -r requirements.txt -r desktop/requirements-desktop.txt
python desktop/binderdex_desktop.py          # BINDERDEX_DEBUG=1 schaltet die Entwicklerwerkzeuge ein
```

| Datei | Aufgabe |
| ----- | ------- |
| `desktop/binderdex_desktop.py` | Starter: Datenordner, Backend-Thread, Fenster, Einzelinstanz, Update-Hinweis |
| `desktop/binderdex.spec` | PyInstaller-Bauplan (Windows-Programmordner / macOS-`.app` mit Kamera-Erlaubnistext) |
| `desktop/make_icons.py` | Erzeugt `icon.ico` / `icon.icns` aus `static/icon-512.png` |
| `desktop/installer/binderdex.iss` | Inno-Setup-Skript für den Windows-Installer |
| `desktop/make_dmg.sh` | Signiert die `.app` ad hoc und packt das DMG |
| `desktop/build_windows.bat` | Lokaler Windows-Build zum Testen |
| `.github/workflows/desktop-release.yml` | Baut alles bei GitHub und hängt es ans Release |

**Release:** Version in `VERSION` eintragen, committen, dann Tag setzen und pushen:

```bash
git tag v1.0.1
git push origin v1.0.1
```

GitHub Actions baut den Windows-Installer und beide macOS-DMGs (etwa 10 bis 15 Minuten) und veröffentlicht sie mit einer `SHA256SUMS.txt` im Release *v1.0.1*. Die Versionsnummer in den Builds kommt aus dem Tag. Testlauf ohne Release: *Actions → Desktop release → Run workflow*, die Dateien liegen dann unter *Artifacts* dieses Laufs.

**Signieren** (optional, entfernt die Warnungen): Windows z. B. über Azure Trusted Signing oder ein Code-Signing-Zertifikat, macOS braucht ein Apple-Entwicklerkonto (99 USD pro Jahr) für Signatur und Beglaubigung. Beides lässt sich später in den Workflow einbauen.
