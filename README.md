# Binderdex

**Self-hosted web app to digitize, price and manage your Pokémon card collection.**
Built around one idea: **one card per Pokémon in your binder** (a Pokédex of cards), everything else goes to a side pile you can sell or trade.

> **Unofficial fan project.** Not affiliated with, endorsed or sponsored by The Pokémon Company, Nintendo, Creatures or Game Freak. See the [legal notice](#legal-notice).
>
> **Languages:** the app is available in **English, German and Spanish**: interface, Pokémon names and Pokédex entries. You choose the languages on the first start (or in the Windows installer) and can switch anytime in the settings. Deutsche Version: [README.de.md](README.de.md)

No account, no cloud, no API key. It runs as a desktop app on Windows and macOS, or as a web app on your PC, a Raspberry Pi or a small server, and your data stays in a single SQLite file.

## Features

**Pokédex and binder**
- **English, German and Spanish** (interface, Pokémon names, Pokédex entries, exports), switchable per device; more languages can be added with a dictionary file and a few lines of code ([docs/translating.md](docs/translating.md))
- All Pokémon in national Pokédex order with progress bar; missing ones show as silhouettes
- One card per Pokémon in the binder; a second card shows both side by side: *replace* or *send to side pile*
- Pokédex entry (text from the games) and category for every Pokémon, favorites (star), filters (caught, missing, favorites, generation, fullart / no fullart) and sorting (number, price, number of cards)
- Statistics: progress per generation, fullart share, languages, rarities, most valuable cards, value history chart, achievements, "random missing Pokémon"

**Adding cards**
- Type `147/196`: the **set and language (German, English, Japanese) are detected automatically**
- **Camera scan** that reads the card number with OCR **in your browser** (Tesseract.js), scans continuously, picks the sharpest frame and confirms after two identical reads. Works with a PC webcam or the rear camera of a phone
- **Two guided modes** after adding a card: *next card in the set* or *next Pokémon in the Pokédex with all its cards* (full database, three languages)
- **+1 / -1 counters** on every card (Sets view, side pile, Pokémon window): count a whole display in seconds
- **Sales list with card images:** Excel file with embedded thumbnails (and a condition column), a printable sales page (save as PDF) and a CSV with image links
- **Optional AI help for the camera:** a free vision model (Ollama on your own PC, or a free Gemini key) reads the card from the camera image, far more reliable than OCR alone; you still confirm every card ([docs/ai-scan.md](docs/ai-scan.md))
- **Sell on Cardmarket:** pick cards from the side pile with quantity, condition and a price suggestion (trend with percentage adjustment and rounding), then a listing assistant walks you through each card with a direct Cardmarket link and copy buttons; listed and sold cards are tracked (sold copies are removed from the collection), plus a CSV for bulk-listing tools. Cardmarket's API is currently not available to private sellers, so nothing is published automatically ([docs/selling.md](docs/selling.md))
- **Grading check:** a pre-grade estimate (PSA scale) from photos: you measure the **centering** with lines and a magnifier against the published PSA limits, the AI judges corners, edges and surface, and the app shows a grade **range**, what limits it most and whether **sending it in is worth it** (you enter costs and market prices). Not affiliated with PSA, an estimate only ([docs/grading.md](docs/grading.md))
- **Pack session:** count a whole display and get an evaluation at the end (total value, best cards, new Pokémon)
- **Binder view:** page by page like a real binder (9 / 12 / 16 pockets), with a "page 3, slot 7" hint when you file a card
- **Price movement** since the last update (up / down, biggest winners and losers, wishlist cards that got cheaper)
- **76 achievements** in 8 groups with progress bars and pop-ups, Pokémon of the day, a "Who's that Pokémon?" quiz, 7 colour themes and optional retro sounds
- **Sets view:** all sets since 2017 in German, English and Japanese (Japanese sets with English names and fallback images), full card lists, add with one click

**Prices, selling and trading**
- Prices from Cardmarket (via TCGdex), per card and for binder / whole collection
- **Variants:** normal, reverse holo, holo and Poké / Great / Ultra / Master Ball patterns, plus an optional own price
- **Side pile export for selling:** CSV with name, value and Cardmarket link (optionally more columns)
- Wishlist, trade list (what you can offer / what you look for) as copy-ready text, CSV export of the collection and missing Pokémon, database download

**Everything else**
- Mobile friendly with burger menu, installable as a home-screen app (PWA)
- Several people / devices can use the same instance at the same time
- Docker image, backup script (local + optional network share), database merge tool
- Retro Pokédex-style design (pixel fonts, red device, dark LCD display)

## Download: desktop app (Windows / macOS)

The easiest way: no Python, no terminal. Download the file for your system from the [latest release](https://github.com/askyonex/binderdex/releases/latest):

| System | File |
| ------ | ---- |
| Windows 10 / 11 (64-bit) | `BinderDex-Setup-x.y.z.exe` |
| Mac with Apple Silicon (M1 or newer) | `BinderDex-x.y.z-macOS-arm64.dmg` |
| Mac with Intel processor | `BinderDex-x.y.z-macOS-x86_64.dmg` |

**Windows:** run the installer (no admin rights needed). Because the app is not code-signed, Windows may show *"Windows protected your PC"*: click **More info → Run anyway**.
**macOS:** open the DMG and drag BinderDex onto *Applications*. On the first start macOS blocks the app because it is not notarized by Apple: open **System Settings → Privacy & Security**, scroll down and click **Open Anyway** (only needed once).

The installer asks which app languages you want (English, German, Spanish). The desktop app runs the same app in its own window, the camera scan works with your webcam. Your collection is stored per user (Windows: `%APPDATA%\BinderDex`, macOS: `~/Library/Application Support/BinderDex`) and stays there on updates and (if you choose so) uninstalls. The app tells you when a new version is available. Details: [docs/desktop-app.md](docs/desktop-app.md)

## Quick start

Requirements: Python 3.10+ and a modern browser. Internet access is needed (card data, images, prices).

```bash
git clone https://github.com/askyonex/binderdex.git
cd binderdex
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open <http://localhost:5000>. On the first start the app downloads the Pokémon names and Pokédex entries (a few minutes, shown in the header).

**Docker:**

```bash
docker compose up -d --build     # then open http://localhost:5000
```

### Configuration (environment variables)

| Variable  | Default        | Meaning |
| --------- | -------------- | ------- |
| `DB_PATH` | `pokedex.db`   | Path of the SQLite database (the Docker image uses `/data/pokedex.db`) |
| `HOST`    | `127.0.0.1`    | Address to listen on (`0.0.0.0` to allow other devices, the Docker image does this) |
| `PORT`    | `5000`         | Port |

**Camera access needs HTTPS** (or `localhost`). If you want to use the camera from a phone, serve the app over HTTPS, see [docs/self-hosting.md](docs/self-hosting.md).

## Documentation

- [User guide](docs/user-guide.md) / [Benutzerhandbuch](docs/benutzerhandbuch.md)
- [Self-hosting (Docker, Raspberry Pi, HTTPS, phone app, backups)](docs/self-hosting.md) / [Selbst hosten](docs/selbst-hosten.md)
- [Desktop app (download, data folder, building a release)](docs/desktop-app.md) / [Desktop-App](docs/desktop-app.de.md)
- [Contributing](CONTRIBUTING.md)

## Data sources and credits

| What | Source |
| --- | --- |
| Card data, images, Cardmarket prices, sets (de / en / ja) | [TCGdex](https://tcgdex.dev) |
| Pokémon names, Pokédex entries, artwork for silhouettes | [PokeAPI](https://pokeapi.co) |
| English names of Japanese sets, fallback card images (for German cards first the English version of the same card from TCGdex) | [TCGplayer data via tcgcsv.com](https://tcgcsv.com) |
| Text recognition in the browser | [Tesseract.js](https://github.com/naptha/tesseract.js) (Apache-2.0) |
| Backend | [Flask](https://flask.palletsprojects.com) (BSD-3-Clause) |
| Fonts | Press Start 2P and VT323 (SIL Open Font License) via Google Fonts |
| Exchange / links | Cardmarket links (no data is taken from Cardmarket directly) |

The app caches what it can and requests data in small batches. Please respect the terms of these services and keep request volume low if you run a public instance.

## Privacy and security

- Your collection lives in one SQLite file on your machine. Nothing is sent anywhere except the lookups to the services above (card numbers, set codes, Pokédex numbers).
- The optional AI help sends camera frames to the service you choose: to your own PC with Ollama (stays in your network) or to Google with a Gemini key (the free tier may be used by Google to improve its products). It is off until you set it up.
- Your browser loads the fonts from Google Fonts and Tesseract.js from jsDelivr. If that matters to you (for example for a public instance in the EU), download and serve these files yourself.
- There is **no login**. Anyone who can open the page can change the data. Run it in your home network or behind your own authentication, **never expose it directly to the internet**.
- The app uses Flask's built-in server, which is fine for a few users at home but not for a public site.

## Known limitations

- Card names, set names and rarities of English and Japanese cards are shown as printed (German rarities are translated)
- Card number OCR depends on light, distance and camera. Typing the number always works
- Prices are indicative: Cardmarket trend via TCGdex, not language specific, sometimes missing (especially Japanese cards). Ball pattern variants have no price of their own, enter one manually
- One variant per card (if you own the same card as normal and reverse holo, set an own price or treat them separately)
- Card data is only as complete as TCGdex / TCGplayer data; very new sets can have gaps

## Roadmap

- More UI languages (French, Italian, ...): contributions welcome, see [docs/translating.md](docs/translating.md)
- Several collections (profiles) in one instance
- Price alerts for wishlist cards, upgrade suggestions (better card for a Pokémon)
- Self-hosted fonts and OCR files (offline use, no CDN)
- English code comments

## Legal notice

Pokémon and all related names, characters, logos and card artwork are trademarks and/or copyrighted works of The Pokémon Company, Nintendo, Creatures Inc. and GAME FREAK Inc. This project is an unofficial, non-commercial fan tool for managing a personal collection. **It contains no card images or official artwork**; images are loaded at runtime from third-party services. Cardmarket and TCGplayer are trademarks of their owners. The software is provided "as is" without warranty (see [LICENSE](LICENSE)). This is not legal advice; if you publish a modified version or run a public instance, check the terms of the data providers yourself.

## License

[MIT](LICENSE) for the source code.
