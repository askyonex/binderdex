# Selling on Cardmarket

The side pile has a selling assistant that removes most of the typing when you list cards on Cardmarket and keeps track of what is listed and sold.

## Why not publish with one click?

Cardmarket has an API that can create offers, but according to several developers **access for private sellers is currently closed** (no new API apps are granted; Cardmarket pointed to a future API 3.0). You can check your own account's API section. Until then the app offers two ways that need no API.

## Listing assistant

1. Side pile > *Auf Cardmarket verkaufen*.
2. Pick cards (everything in the side pile that is not listed yet, spare copies of binder cards included, the binder card never) and set **quantity**, **condition** (MT, NM, EX, GD, LP, PL, PO) and **price** (suggestion from the Cardmarket trend, at least 0.02 €). A global **price adjustment** (for example −10 % below trend) and **rounding** (0.05 €, x.x9 or none) recalculate all suggestions.
3. *Listing-Assistent starten* walks through the cards one by one: picture, set, number, variant, language, foil, condition, quantity and price with copy buttons, and *Auf Cardmarket öffnen* opens the card's product page (foil filter for reverse holo and holo; ball patterns open a search). List the card on Cardmarket, then press *Eingestellt, weiter*.

**Search and sort:** above the card list there is a search box (card name, Pokémon, set, number, variant or language; several words work, for example "obsidian charizard") and a sort order: price high or low, name, set and number, Pokédex number, most copies or selected cards first. *Alle auswählen* (select all) and *Keine* (none) apply to the cards currently found.

## Managing listings

*Gelistet* shows all offers with the total offer value. *Verkauft* removes the sold copies from your collection (asks how many if more than one; a binder card is never removed), *Zurückgezogen* marks an offer you deleted on Cardmarket. Listed cards carry a yellow "n× auf Cardmarket" label in the side pile, and the assistant only offers copies that are not listed yet.

*Gelistet* (listed) has search and sorting too (newest or oldest first, price, name, set and number); the search also filters the list of sold cards.

## CSV for bulk-listing tools

*CSV für Massenlistung* exports the selection (name, English expansion name, expansion as stored, collector number, language, condition, foil, reverse holo, quantity, price, Cardmarket product ID, comment). Tools such as the open-source browser extension "Cardmarket Bulk Import" fill Cardmarket's bulk listing form from a CSV. Cardmarket accepts at most 100 items per expansion at a time; column names expected by such tools may differ, so check the mapping and **always review the filled form before submitting**.
