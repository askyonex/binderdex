# KI-Hilfe für die Kamera (optional)

Ein Bildmodell liest die Karte direkt aus dem Kamerabild (Name, Sammlernummer, Set-Größe) und ist bei Hüllen, Glanz und schrägem Winkel deutlich zuverlässiger als die reine Texterkennung. Die App sucht die Karte danach in der Kartendatenbank und zeigt sie mit Bild. **Du bestätigst jede Karte selbst.** Die schnelle Texterkennung im Browser bleibt die Grundfunktion.

## Modi (Kamerafenster, "KI-Hilfe")

| Modus | Verhalten |
| --- | --- |
| *Aus* | nur Texterkennung |
| *Bei "Jetzt scannen"* | Texterkennung läuft wie gewohnt, der Knopf *Jetzt scannen* (oder Tipp aufs Video, Leertaste) fragt **zuerst die KI**, bei Misserfolg die Texterkennung |
| *Automatisch bei Stillstand* | fragt die KI zusätzlich von selbst, wenn das Bild etwa 2,5 Sekunden ruhig liegt und die Texterkennung nichts fand (einmal pro ruhiger Phase, erst nach einer Bewegung wieder) |

## Weg A: Ollama auf deinem PC (kostenlos, privat)

1. Ollama installieren (ollama.com/download).
2. Ein Bildmodell laden, z. B. `ollama pull qwen3-vl:8b` (ca. 6 GB, passt in 12 GB Grafikspeicher; `qwen3-vl:4b` braucht weniger).
3. Ollama im Netzwerk erreichbar machen: Umgebungsvariable `OLLAMA_HOST=0.0.0.0:11434` setzen (Windows: `setx OLLAMA_HOST "0.0.0.0:11434"`, danach Ollama neu starten) und TCP-Port 11434 in der Firewall für das private Netz freigeben. **Ollama hat keine Anmeldung, nur im vertrauenswürdigen Heimnetz nutzen.**
4. In der App: Kamerafenster > *KI einrichten* > Anbieter *Ollama*, Adresse `http://<PC-IP>:11434`, Modell `qwen3-vl:8b` > *Verbindung testen* > *Speichern*.

Der erste Scan nach einer Pause dauert länger, weil das Modell erst in die Grafikkarte geladen wird.

## Weg B: Google Gemini (kostenloser API-Schlüssel)

In Google AI Studio einen Schlüssel erstellen, Anbieter *Google Gemini* wählen, Schlüssel einfügen und das Modell `gemini-flash-latest` lassen (ein Alias auf das aktuelle Flash-Modell, Modellnamen ändern sich). *Verbindung testen* listet die verfügbaren Flash-Modelle. Die kostenlose Stufe hat Limits pro Minute und Tag, die vom Modell abhängen und sich ändern, und **Google kann über die kostenlose Stufe gesendete Bilder zur Verbesserung seiner Produkte nutzen**. Fotografiere nur Karten.

## Einstellungen per Umgebungsvariable (optional)

`AI_PROVIDER` (`ollama` oder `gemini`), `OLLAMA_URL`, `OLLAMA_MODEL`, `GEMINI_API_KEY`, `GEMINI_MODEL`. In der App gespeicherte Werte (liegen in der Datenbank, der Schlüssel im Klartext) haben Vorrang.

## Fehlersuche

| Meldung | Lösung |
| --- | --- |
| "KI-Dienst nicht erreichbar" | Ollama läuft nicht, Adresse falsch, `OLLAMA_HOST` nicht gesetzt oder Ollama nicht neu gestartet, Firewall-Regel fehlt |
| "Modell nicht gefunden" | Auf dem PC `ollama pull <Modell>` ausführen oder den Namen korrigieren |
| "Kontingent aufgebraucht" | Gemini-Limit erreicht, warten oder auf Ollama wechseln |
| "... keine passende Karte gefunden" | Karte nicht in der Datenbank oder Nummer falsch gelesen: Nummer eintippen oder Set manuell wählen |

Keine Methode ist zu 100 % perfekt (Glanz, winzige Schrift, seltene Sondernummern). Deshalb zeigt die App den Treffer immer zur Bestätigung, und die manuelle Eingabe bleibt möglich.
