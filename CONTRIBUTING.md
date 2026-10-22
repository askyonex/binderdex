# Contributing

Thanks for your interest! Bug reports, ideas and pull requests are welcome.

## Run it for development

```bash
python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
DB_PATH=test.db python app.py                       # Windows PowerShell: $env:DB_PATH="test.db"; python app.py
```

Open <http://localhost:5000>. Use a separate `test.db` so you do not touch your real collection. Static files are served from `static/` on every request (reload with Ctrl+F5); changes in `app.py` need a restart.

## Project layout

| Path | Purpose |
| --- | --- |
| `app.py` | Flask backend, SQLite, calls to TCGdex / PokeAPI / tcgcsv.com |
| `static/index.html` | The whole frontend (HTML, CSS, JavaScript in one file, no build step) |
| `static/i18n.js`, `static/i18n/*.json` | Translations (see [docs/translating.md](docs/translating.md)) |
| `tools/` | Translation helpers (extract texts, build the dictionaries) |
| `desktop/` | Desktop app: launcher, PyInstaller build, Windows installer, macOS DMG |
| `merge_db.py` | Merges two databases |
| `scripts/backup.sh` | Backup script (local and optional network share) |
| `docs/` | Documentation (English and German) |

## Guidelines

- Keep it simple: no build tools, no frontend framework, few dependencies.
- Please **do not add card images, logos or official artwork** to the repository or to pull requests.
- Code comments and the source UI texts are German; English comments are welcome. The UI is translated at runtime: when you add or change a text, run `python tools/i18n_extract.py --check` and add the missing translations (see [docs/translating.md](docs/translating.md)).
- Test your change with a fresh database and with an existing one (the database is migrated automatically in `init()`).
- Mention the data source and terms if you add a new external service.

## Intro tour

The intro tour is the `TOUR` list in `static/index.html` (max. 7 steps per view, desktop steps `desk: true`, phone steps `mob: true`). For an important new feature add a step with a **new** `id` and `new: true`: devices that already saw the tour then show only that step, prefixed with "Neu:". Add the texts to `static/i18n/*.json`.

## Reporting bugs

Please include what you did, what you expected, what happened, your browser and how you run the app (local, Docker, Raspberry Pi). For price or image problems the diagnostic endpoints help: `/api/pricecheck?lang=de&id=<card id>`, `/api/imgcheck?lang=ja&set=<set id>`, `/api/seriesdebug?lang=ja`.
