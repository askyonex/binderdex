# User guide

The app's interface is German; this guide explains it in English. Menu names are given in German with the English meaning in brackets.

## 1. The main screen

- **Pokédex grid:** every Pokémon in national Pokédex order. Caught Pokémon show their binder card (green check = the card is in the binder), missing ones are silhouettes. The header shows progress (caught / total), the value of the binder and of all cards.
- **Blue lens (top left):** switches the camera scan on and off.
- **Title "Mein Pokédex":** on phones it opens the menu (see section 8).
- **Search, filter, generation, sort:** *Alle / Gefangen / Fehlen / Favoriten / Fullart im Binder / Kein Fullart im Binder* (all / caught / missing / favorites / fullart in binder / no fullart in binder), generation (Kanto to Paldea) and sorting by number, price or number of cards. Pokémon without a price or without cards always come last. The star on a tile marks a favorite.
- **Click a Pokémon:** opens its window with the Pokédex entry (text from the games), a star for favorites and all your cards of that Pokémon. There you can move a card into the binder, delete it, change its variant or enter an own price.

## 2. Adding cards

**By number.** Type the number as printed on the card, for example `147/196` (the part behind the slash is the size of the set). The app finds the set and the language (German, English, Japanese) itself. If several cards match (for example the same card in German and English), pick the right one. If you select a set and a language first, the number alone (`147`) is enough.

**By camera.** Click the blue lens, allow camera access and hold the card so that the number is inside the yellow frame (the slider changes its height).
- The app reads continuously. After **two identical reads in a row** the card is recognized, the result dialog appears and the device vibrates (Android).
- Confirm, then take the card out of the picture for a moment and show the next one. The same card is not recognized twice while it stays in view.
- *Jetzt scannen* (scan now), the space bar or a tap on the video image reads immediately and more thoroughly.
- Tips: about 15-20 cm distance, light from the side, tilt the card against glare. Letters before the number (for example the **F** regulation mark) are ignored. The app only accepts a number if the number behind the slash matches a known set size.
- **AI help:** for the most reliable result set up the optional AI help (button *KI einrichten* in the camera window), see [ai-scan.md](ai-scan.md).
- If a card is not recognized, tick **Diagnose anzeigen** (show diagnostics) below the video: it shows the crop that is being read and the raw OCR text of the last attempts, which usually reveals what goes wrong (glare, wrong frame height, a misread digit).
- On phones the rear camera is used by default; zoom and torch appear where the device supports them.

**Result dialog.**
- Pokémon has no binder card yet: *In den Binder* (to the binder) or *In den Nebenstapel* (to the side pile).
- Pokémon already has a binder card: both cards are shown side by side. *In den Binder (ersetzen)* replaces it, *In den Nebenstapel* keeps the current one.
- If the card is already in your collection you see the quantity; *Noch ein Exemplar (+1)* adds a copy. *Auf die Wunschliste* puts a card you do not own on your wishlist.
- *Variante* lets you choose reverse holo, holo or a ball pattern for common cards (see section 5).

**Adding from the grid.** Click a **silhouette** (a Pokémon you have no card of) to open the list of **all cards of that Pokémon** (whole database, newest sets first, German / English / Japanese). Pick a card for *In den Binder*, *In den Nebenstapel* or *Auf die Wunschliste*; you stay on the same Pokémon so you can add several cards, and *Schließen* returns to the grid. For Pokémon you already have cards of, the same list opens via the button *Alle Karten dieses Pokémon* in the Pokémon window.

## 3. Guided modes after adding a card

Header row "Nach dem Hinzufügen vorschlagen" (suggest after adding), only one can be active:

- **Nächste Karte im Set** (next card in the set): after card 114 you get 115, 116 and so on. Optional: skip trainer and energy cards. Buttons: *In den Binder*, *In den Nebenstapel*, *Überspringen* (skip), *Beenden* (stop).
- **Nächstes Pokémon im Pokédex** (next Pokémon): after Pikachu (#25) a window shows Raichu (#26) with the Pokédex entry, your current binder card and **all cards of that Pokémon** from the whole database, newest sets first, switchable between German, English and Japanese. Pick a card and the next Pokémon follows. Adding a card to the **wishlist** does *not* advance (in the "next card in the set" mode the current card stays, too): you stay on the same Pokémon so you can mark several cards (marked cards show a "Wunschliste" label). Optional: skip Pokémon that already have a binder card. You can also start without scanning ("ab Nr." field and *Durchlauf starten*).
- **Nichts** (nothing) switches the suggestions off. Scanning cards in random order from a pack works best with this setting.

## 4. Sets view

Button **Sets**: all sets since 2017 (Sun & Moon, Sword & Shield, Scarlet & Violet, Mega Evolution and newer), newest first, in German, English or Japanese. Japanese sets show English names (matched via the set code) and, where the card database has no image, a fallback image. Under every Pokémon card you see **"Nr. 097 · Hypno"** (Pokédex number and German name), matched from the card name in German, English or Japanese; trainer and energy cards have none, and the search also finds by German name or Pokédex number. In the card dialog the number is part of the Pokédex entry. The matching is a name lookup, so unusual card names can be missed or occasionally wrong; on the first start after an update the app downloads the English and Japanese Pokémon names (a few minutes). Click a set for the full card list with markers (check = in binder, "Nebenstapel" = in collection but not in the binder), filter and search. Click a card for the result dialog.

**Counting copies (+1 / -1), for example when opening a whole display.** In the Sets view every card has **-**, the quantity and **+** underneath. A tap on **+** adds a copy, **-** removes one, without any dialog (for cards you already have it is a tiny database change, so it is instant). A card you do not own yet is added by the first **+**: into the binder if the Pokémon's slot is free, otherwise into the side pile, without asking. Tapping **-** on the last copy asks before removing the card. The same **-** / **+** buttons exist in the side pile and in the Pokémon window, and the result dialog offers *Noch ein Exemplar (+1)* and *Ein Exemplar weniger (-1)* for cards you already own.

**Classic Collection cards** carry the original number (for example Charizard 4/102). Entering or scanning that number offers the Classic Collection card next to the original one; pick the right one, or count them in the Sets view. Missing images of such sets are matched by card name.

## 5. Prices and variants

- The price is the **Cardmarket trend in euro** (via TCGdex): per card and in total. Click *Preise aktualisieren* (update prices) to refresh; new cards get their price automatically. Prices are indicative, not language specific, and missing for some cards (especially Japanese ones).
- **Variants:** *Normal*, *Reverse Holo*, *Holo*, and the *Pokéball / Superball / Hyperball / Meisterball pattern* of newer sets. Normal uses the normal Cardmarket trend, all others the **foil trend**. Below the price it says where the price comes from.
- **Own price:** the field "Eigener Preis" overrides everything. Use it especially for ball patterns, because the card database has no own price for them (the foil price is usually too low).
- One variant applies to a card (all copies). If you own the same card as normal and reverse holo, use the own price or handle them separately.

## 6. Side pile, selling and trading

- **Nebenstapel** (side pile): all cards that are not in the binder **plus the spare copies of binder cards** (a second copy of a binder card counts as side pile; the binder card itself stays in the binder), with filter *Alle / Pokémon / Trainer / Energie* and the total value of the selection.
- **Selling list:** *Verkaufsliste als CSV* downloads the side pile for Excel. Column A: card name (with the variant), column B: value in euro, column C: Cardmarket link. Every copy is its own row so that the sum of column B is the total. Options: *mit Zusatzspalten* (extra columns: quantity, sum, set, number, rarity, language, variant) and *Doppelte der Binder-Karten mitnehmen* (include spare copies of binder cards, on by default). Links go to the product page of the card (foil filter for foil variants); for ball patterns and cards without a product ID they go to a Cardmarket search.
- **Tauschen** (trade): your wishlist (with prices, "Hab ich jetzt" = I have it now, Cardmarket search) and everything you can offer (side pile and duplicates), plus a ready-made text "Ich biete ... Ich suche ..." to copy into a chat or forum.

## 7. Statistics, export and backup

Button **Statistik**: caught Pokémon, number of cards, values, progress per generation, fullart share (rarities containing illustration, ultra, hyper, full art, secret, gold, rainbow, adjustable in `FULLART_KEYS` in `app.py`), languages, most common rarities, value history (one data point per day), top 10 cards, achievements and the button *Zufälliges fehlendes Pokémon* (random missing Pokémon). Export: collection CSV, missing Pokémon CSV, and **Datenbank sichern** (download of the database).

**Menus on desktop:** on wider screens the three small lights next to the camera lens are buttons. **Red** opens *Extras* (Statistik, Binder, Quiz, Grading-Check, Upgrade-Vorschläge, Platzhalter drucken, Preise aktualisieren), **yellow** the settings (design, binder page size, sounds, language), **green** filter, generation and sort. One panel is open at a time; click the light again or press Esc to close it. While a filter or a non-default sort is active the green light shows a dark dot. On phones everything stays in the burger menu.

## 8. On a phone

On narrow screens the header is reduced to lens, title with progress, set field, language / number / add row and search. A tap on **Mein Pokédex** opens the menu with *Ansichten* (Sets, Nebenstapel, Tauschen, Statistik), *Aktionen* (update prices), *Anzeige* (filter, generation, sort) and the guided-mode settings. The menu closes automatically after choosing a view. Install it as a home-screen app, see [self-hosting](self-hosting.md).

## 9. Several people at once

Several devices can use one instance at the same time. They share one collection. A second person adding a card for the same Pokémon sees the normal comparison dialog. Other devices see changes after a reload.

## 10. Diagnostics

| URL | Shows |
| --- | --- |
| `/api/pricecheck?lang=de&id=<card id>` | the raw price data of a card |
| `/api/imgcheck?lang=ja&set=<set id>` | whether fallback images were found for a set |
| `/api/seriesdebug?lang=ja` | which series the Sets view found and why |
| `/api/dexcards?dex_id=25&lang=en` | all cards of a Pokémon |

## 11. Extras

- **Sales list with images** (side pile window): *Excel mit Bildern* creates an `.xlsx` with embedded thumbnails, name, value, quantity, sum (formula), condition, set, number, rarity, language, variant and a Cardmarket link, sorted by value with a total. It needs `openpyxl` and `pillow` (installed by `requirements.txt` and the Docker image) and takes a few seconds because the images are downloaded and shrunk. *Verkaufsseite (Drucken/PDF)* opens a clean page with images that you can print or save as PDF from the browser. The CSV with extra columns now contains *Zustand* (condition) and *Bild-Link*.
- **Condition:** in card lists (side pile, Pokémon window) choose NM, MT, EX, GD, LP, PL or PO (Cardmarket abbreviations) next to the variant. It appears in the exports.
- **Pack session** (menu): *Pack-Session starten* counts everything you add (including +1). The header shows the running total; *Pack-Session beenden* shows the evaluation: cards, total value, average per card, new cards, **new Pokémon**, best cards with images and value per set.
- **Binder view** (menu): your binder page by page (9, 12 or 16 pockets, set in the menu), empty pockets as silhouettes, jump by page or Pokémon number. When a card goes into the binder the app tells you the position ("page 3, slot 7").
- **Price movement:** every price update remembers the previous price. Card lists show up / down arrows with the difference, wishlist cards show *billiger* / *teurer*, and the statistics list the biggest winners and losers.
- **Achievements:** 76 in 8 groups with progress bars; new ones pop up when you unlock them. **Statistics** also show the Pokémon of the day, your current streak (days in a row with new cards), sets owned / completed and the most valuable sets.
- **Grading check** (menu, or the *Grading* button of a card): pre-grade estimate with centering measurement, AI condition review and a "worth sending in?" calculation, see [grading.md](grading.md).
- **Upgrade suggestions** (red light / menu): for every Pokémon in the binder whose card is not a full art the app looks up the cheapest full art card you don't own yet (Cardmarket trend) and shows a shopping list with the total, e.g. "For €25.30 you get 9 new full arts". Choose the card language (German or English), the scope (binder Pokémon only, or all Pokémon without a full art) and optionally a budget: the list then keeps the cheapest cards that fit. Each suggestion has a Cardmarket link and a wishlist button, plus *Add all to the wishlist* and *Copy shopping list*. The first search loads all full art cards and their prices and takes a few minutes; prices are cached for 7 days, *Find full arts* refreshes them. Which rarities count as full art is set in `FULLART_KEYS` in `app.py`.
- **Printable binder placeholders** (red light / menu, or *Platzhalter drucken* in the binder view for the current page): a print page with card-size placeholders (63 × 88 mm, 9 per A4 sheet, dashed cut lines) showing number, name, silhouette and binder position. Options: missing Pokémon / without full art / all, generation, number range, *compact* or *like the binder* (one sheet per binder page, occupied pockets stay blank) and a light silhouette (saves ink), dark silhouette or colour artwork. Print at 100 % / "actual size" so the cards fit the pockets.
- **Quiz** (menu): "Wer ist das Pokémon?", silhouette guessing with a hint, streak, points and record, optionally per generation.
- **Design and sounds** (menu): seven colour themes and optional retro sounds (scan recognized, new Pokémon, achievement). Stored per device.
