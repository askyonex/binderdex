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
| `merge_db.py` | Merges two databases |
| `scripts/backup.sh` | Backup script (local and optional network share) |
| `docs/` | Documentation (English and German) |

## Guidelines

- Keep it simple: no build tools, no frontend framework, few dependencies.
- Please **do not add card images, logos or official artwork** to the repository or to pull requests.
- Code comments and UI texts are currently German. English comments are welcome, and a proper UI translation (i18n) is the biggest open topic (see README roadmap). If you want to work on it, open an issue first so we can agree on the approach.
- Test your change with a fresh database and with an existing one (the database is migrated automatically in `init()`).
- Mention the data source and terms if you add a new external service.

## Reporting bugs

Please include what you did, what you expected, what happened, your browser and how you run the app (local, Docker, Raspberry Pi). For price or image problems the diagnostic endpoints help: `/api/pricecheck?lang=de&id=<card id>`, `/api/imgcheck?lang=ja&set=<set id>`, `/api/seriesdebug?lang=ja`.
