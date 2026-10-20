# Languages and translations

Binderdex is available in **German, English and Spanish**: the interface, the Pokémon names and the Pokédex entries (category and text from the games) follow the selected language. Exports (CSV, Excel, sales page) and the AI's free-text answers in the grading check do too.

## For users

- **Windows installer:** the setup asks which languages should be available (several possible) and, if you pick more than one, which one the app starts in.
- **macOS app, Raspberry Pi, Docker, `python app.py`:** on the first start the app shows a short dialog with the same choice.
- **Switching:** *Settings → Language* (yellow lamp on the PC, menu on the phone). The choice is saved **per device**, so you can use English on your phone and German on the PC with the same collection.
- **Adding or removing languages later:** the **…** button next to the language selection. The first language in that list is the default for new devices.
- **Docker / server:** `BINDERDEX_LANGS: "de,en,es"` in `docker-compose.yml` sets the languages from outside (first = default). The app takes it over whenever the value changes.

Pokémon names and Pokédex entries come from PokeAPI. After the update the app downloads them once for all three languages (a few minutes, shown in the header). If a Pokédex entry is missing in a language, the English one is shown, then the German one.

What stays as printed: card names, set names and rarities of English and Japanese cards (German rarities are translated).

## How it works

The interface is written in German. `static/i18n.js` translates it in the browser:

- It loads the dictionary of the selected language (`static/i18n/<lang>.json`, served as `/i18n/<lang>.js`).
- It translates every text that appears on the page (also later, through a `MutationObserver`), the `title`, `placeholder` and `aria-label` attributes, and `alert`/`confirm`/`prompt`.
- **Keys are the German texts** (whitespace collapsed). Inserted values become placeholders:
  ```json
  "{0} Karten": "{0} cards",
  "{0} liegt im Nebenstapel.": "{0} is in the side pile."
  ```
  Parts that fall into a placeholder are looked up again (so `"Selten"` inside `"{0} · {1}"` is translated as well). Entries whose value equals the key (for example `"{0} · {1}"`) exist only for that reason.
- Missing keys simply stay German, nothing breaks.
- Elements with `class="notranslate"` are left alone (language names, for example).
- The server uses the same dictionaries for exports (`tr()` in `app.py`) and reads the language from the `ui_lang` cookie.

## Adding or changing texts

1. Change the German text in `static/index.html` or `app.py` as usual.
2. Run `python tools/i18n_extract.py --check`. It lists every text that is missing in a dictionary.
3. Add the translations to `static/i18n/en.json` and `static/i18n/es.json`. Keep the placeholders `{0}`, `{1}` (their order may change).
4. Raise `I18N_VERSION` in `app.py` so browsers load the new dictionary.

Texts that should never be translated (CSS selectors, addresses, proper names) go into `tools/i18n_ignore.txt`.

## Adding a language

1. Copy `static/i18n/en.json` to `static/i18n/<code>.json` (for example `fr.json`) and translate the values.
2. Add the code to `DEX_LANGS` in `app.py`, plus game names in a `GAMES_<CODE>` table (the Pokédex texts come from PokeAPI, which has French, Italian, Korean and more).
3. Add it to `NAMES` and `LOCALES` in `static/i18n.js`.
4. For the Windows installer: one more line in `LangCode`/`LangName` in `desktop/installer/binderdex.iss` (and `NLANG`), plus the language in `installer_langs()` in `desktop/binderdex_desktop.py`.
