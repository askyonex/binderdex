# AI help for the camera (optional)

A vision model reads the card straight from the camera image (name, collector number, set size) and is much more reliable than plain OCR with sleeves, glare and tilted cards. The app then looks the card up in the card database and shows it with its picture. **You still confirm every card yourself.** The fast in-browser OCR stays as the default.

## Modes (camera window, "KI-Hilfe")

| Mode | Behavior |
| --- | --- |
| *Aus* (off) | OCR only |
| *Bei "Jetzt scannen"* | continuous OCR as usual; the *Jetzt scannen* button (or tapping the video, space bar) asks the AI **first**, OCR as fallback |
| *Automatisch bei Stillstand* | additionally asks the AI automatically when the picture has been still for about 2.5 s and OCR found nothing (once per still phase, again only after movement) |

## Option A: Ollama on your own PC (free, private)

1. Install Ollama (ollama.com/download).
2. Pull a vision model, e.g. `ollama pull qwen3-vl:8b` (about 6 GB, fits into 12 GB of VRAM; `qwen3-vl:4b` for less memory).
3. Make Ollama reachable in your network: set the environment variable `OLLAMA_HOST=0.0.0.0:11434` (Windows: `setx OLLAMA_HOST "0.0.0.0:11434"`, then restart Ollama) and allow TCP port 11434 in the firewall for the private network. **Ollama has no authentication, use it in a trusted home network only.**
4. In the app: camera window > *KI einrichten* > provider *Ollama*, address `http://<PC-IP>:11434`, model `qwen3-vl:8b` > *Verbindung testen* > *Speichern*.

The first scan after a pause is slower because the model is loaded into GPU memory.

## Option B: Google Gemini (free API key)

Create a key in Google AI Studio, choose provider *Google Gemini*, paste the key and keep the model `gemini-flash-latest` (an alias for the current Flash model; model names change). *Verbindung testen* lists the available Flash models. The free tier has per-minute and per-day limits that depend on the model and change over time, and **Google may use images sent through the free tier to improve its products**. Only photograph cards.

## Settings via environment variables (optional)

`AI_PROVIDER` (`ollama` or `gemini`), `OLLAMA_URL`, `OLLAMA_MODEL`, `GEMINI_API_KEY`, `GEMINI_MODEL`. Values saved in the app (stored in the database, the key in plain text) take precedence.

## Troubleshooting

| Message | Solution |
| --- | --- |
| "KI-Dienst nicht erreichbar" | Ollama not running, wrong address, `OLLAMA_HOST` not set or Ollama not restarted, firewall rule missing |
| "Modell nicht gefunden" | `ollama pull <model>` on the PC, or fix the model name |
| "Kontingent aufgebraucht" | Gemini free-tier limit reached, wait or switch to Ollama |
| "... keine passende Karte gefunden" | the card is not in the database or the number was misread: type the number or choose the set manually |

No method is 100 % perfect (glare, tiny print, rare special numbers). That is why the app always shows the match for confirmation and manual entry stays available.
