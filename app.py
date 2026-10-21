"""Eigener Pokedex - Backend (Flask + SQLite).
Datenquellen: PokeAPI (Pokemon-Namen) und TCGdex (Karten de/en/ja inkl. Cardmarket-Preise)."""
import csv
import datetime
import difflib
import io
import json
import math
import os
import re
import sqlite3
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, Response, has_request_context, jsonify, request, send_from_directory

DB = os.environ.get("DB_PATH", "pokedex.db")  # fuer Docker: /data/pokedex.db
TCG = "https://api.tcgdex.net/v2"
POKE = "https://pokeapi.co/api/v2"
LANGS = ["de", "en", "ja"]
I18N_VERSION = "4"  # bei geaenderten Uebersetzungen erhoehen, damit Browser das neue Woerterbuch laden

app = Flask(__name__, static_folder="static")
progress = {"done": 0, "total": 0, "running": False}
price_prog = {"done": 0, "total": 0, "running": False, "missing": 0, "errors": 0, "last_error": ""}
_sets = {}
_series = {}
# Sets-Ansicht: alle Serien der Kartendatenbank, deren Sets ab MIN_DATE erschienen sind (ausser den hier genannten)
MIN_DATE = "2017-01-01"
SERIES_SKIP = {"tcgp", "misc"}  # TCG Pocket (App) und Sonstiges
SERIES_DE = {"me": "Mega-Entwicklung", "m": "Mega-Entwicklung", "sv": "Karmesin & Purpur",
             "swsh": "Schwert & Schild", "s": "Schwert & Schild", "sm": "Sonne & Mond"}
_series_dbg = {}
_dexcache = {}
_tpg = {}  # TCGplayer-Kategorie -> (Zeit, {Set-Code: (groupId, Titel)})
_eni = {}  # Set-ID -> (Zeit, {Nummer: Bild-Basis-URL}) der englischen TCGdex-Version
_tpp = {}
_tpl = {}  # Kategorie -> {groupId: Titel} aller TCGplayer-Gruppen
_enc = {}  # Set-ID -> (Zeit, [(Nummer, Name, Bild)]) der englischen TCGdex-Karten  # (Kategorie, groupId) -> (Zeit, {Kartennummer: Bild-URL})
# Generationen (Pokedex-Nummern) fuer Statistik und Filter
GENS = [("I", "Kanto", 1, 151), ("II", "Johto", 152, 251), ("III", "Hoenn", 252, 386), ("IV", "Sinnoh", 387, 493),
        ("V", "Einall", 494, 649), ("VI", "Kalos", 650, 721), ("VII", "Alola", 722, 809), ("VIII", "Galar", 810, 905),
        ("IX", "Paldea", 906, 1025)]
# Woran eine Seltenheit als "Fullart" erkannt wird (Teile des Namens, Gross-/Kleinschreibung egal). Bei Bedarf anpassen.
FULLART_KEYS = ("illustration", "ultra", "hyper", "full art", "vollbild", "secret", "geheim", "gold", "rainbow", "regenbogen")
# Kartenvarianten (Normal, Reverse Holo, Holo und die Ball-Muster neuerer Sets) und Preislogik
VARIANT_LABELS = {"normal": "Normal", "reverse": "Reverse Holo", "holo": "Holo", "pokeball": "Pokéball-Muster",
                  "greatball": "Superball-Muster", "ultraball": "Hyperball-Muster", "masterball": "Meisterball-Muster"}
PATTERN_VARIANTS = ("pokeball", "greatball", "ultraball", "masterball")
FOIL_VARIANTS = ("reverse", "holo") + PATTERN_VARIANTS
PATTERN_SEARCH = {"pokeball": "Poke Ball", "greatball": "Great Ball", "ultraball": "Ultra Ball", "masterball": "Master Ball"}
FOIL_SQL = ", ".join(f"'{v}'" for v in FOIL_VARIANTS)
_ja = {"names": {}, "t": 0.0}  # englische Namen japanischer Sets (Cache)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ninedex (self-hosted Pokemon card collection app)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def q(sql, args=()):
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(sql, args).fetchall()]
    con.close()
    for r in rows:  # Wert je nach Variante und eigenem Preis (siehe eff_price)
        if "price_holo" in r and "price" in r:
            r["price_base"] = r["price"]
            r["price"], r["price_src"] = eff_price(r)
    return rows


def eff_price(r):
    """Wert einer Karte: eigener Preis, sonst Foil-Preis bei Reverse/Holo/Muster, sonst Normalpreis. Zweiter Wert: Quelle."""
    if r.get("price_own") is not None:
        return r["price_own"], "own"
    if (r.get("variant") or "") in FOIL_VARIANTS:
        if r.get("price_holo") is not None:
            return r["price_holo"], "foil"
        return r.get("price"), "normal_fallback"
    return r.get("price"), "normal"


def psql(a=""):
    """Dieselbe Wertlogik als SQL-Ausdruck (a = Tabellenalias mit Punkt, z. B. 'c.')."""
    return (f"COALESCE({a}price_own, CASE WHEN {a}variant IN ({FOIL_SQL}) AND {a}price_holo IS NOT NULL "
            f"THEN {a}price_holo ELSE {a}price END)")


def run(sql, args=()):
    con = sqlite3.connect(DB, timeout=30)
    con.execute(sql, args)
    con.commit()
    con.close()


def init():
    con = sqlite3.connect(DB, timeout=30)
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS pokemon(id INTEGER PRIMARY KEY, name TEXT, name_en TEXT, name_ja TEXT);
        CREATE TABLE IF NOT EXISTS cards(
            id TEXT PRIMARY KEY, name TEXT, set_name TEXT, local_id TEXT,
            rarity TEXT, image TEXT, dex_id INTEGER, qty INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS binder(dex_id INTEGER PRIMARY KEY, card_id TEXT);
        CREATE TABLE IF NOT EXISTS dex_info(id INTEGER PRIMARY KEY, genus TEXT, text TEXT, game TEXT);
        CREATE TABLE IF NOT EXISTS dex_text(id INTEGER, lang TEXT, genus TEXT, text TEXT, game TEXT, PRIMARY KEY(id, lang));
        CREATE TABLE IF NOT EXISTS favorites(dex_id INTEGER PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS wishlist(card_id TEXT PRIMARY KEY, name TEXT, set_name TEXT, set_id TEXT, local_id TEXT,
            rarity TEXT, image TEXT, dex_id INTEGER, lang TEXT, price REAL, added TEXT);
        CREATE TABLE IF NOT EXISTS value_history(day TEXT PRIMARY KEY, binder REAL, total REAL, cards INTEGER, caught INTEGER);
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, val TEXT);
        CREATE TABLE IF NOT EXISTS listings(id INTEGER PRIMARY KEY AUTOINCREMENT, card_id TEXT, qty INTEGER, price REAL, cond TEXT,
            status TEXT DEFAULT 'listed', ts TEXT, done_ts TEXT);
        CREATE TABLE IF NOT EXISTS grades(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, card_id TEXT, name TEXT, set_name TEXT, image TEXT,
            best INTEGER, low INTEGER, high INTEGER, limiting TEXT, conf TEXT, cen_f REAL, cen_b REAL, subs TEXT, notes TEXT, raw_price REAL);
        CREATE TABLE IF NOT EXISTS session_log(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, card_id TEXT, name TEXT, set_name TEXT,
            image TEXT, price REAL, delta INTEGER, newc INTEGER, newp INTEGER);
        """
    )
    for col in ("name_en TEXT", "name_ja TEXT", "name_es TEXT"):  # Namen in Englisch, Japanisch, Spanisch (Migration)
        try:
            con.execute(f"ALTER TABLE pokemon ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass
    for col in ("lang TEXT DEFAULT 'de'", "price REAL", "price_at TEXT", "category TEXT",
                "price_holo REAL", "price_own REAL", "variant TEXT", "cm_id INTEGER", "px_at TEXT", "cond TEXT", "added TEXT", "price_old REAL"):  # Migrationen
        try:
            con.execute(f"ALTER TABLE cards ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass
    try:
        con.execute("ALTER TABLE wishlist ADD COLUMN price_old REAL")
    except sqlite3.OperationalError:
        pass
    con.commit()
    con.close()


GAMES_DE = {
    "red": "Rot", "blue": "Blau", "yellow": "Gelb", "gold": "Gold", "silver": "Silber", "crystal": "Kristall",
    "ruby": "Rubin", "sapphire": "Saphir", "emerald": "Smaragd", "firered": "Feuerrot", "leafgreen": "Blattgrün",
    "diamond": "Diamant", "pearl": "Perl", "platinum": "Platin", "heartgold": "HeartGold", "soulsilver": "SoulSilver",
    "black": "Schwarz", "white": "Weiß", "black-2": "Schwarz 2", "white-2": "Weiß 2", "x": "X", "y": "Y",
    "omega-ruby": "Omega Rubin", "alpha-sapphire": "Alpha Saphir", "sun": "Sonne", "moon": "Mond",
    "ultra-sun": "Ultrasonne", "ultra-moon": "Ultramond", "lets-go-pikachu": "Let's Go, Pikachu!",
    "lets-go-eevee": "Let's Go, Evoli!", "sword": "Schwert", "shield": "Schild",
    "brilliant-diamond": "Strahlender Diamant", "shining-pearl": "Leuchtende Perle",
    "legends-arceus": "Legenden: Arceus", "scarlet": "Karmesin", "violet": "Purpur", "legends-za": "Legenden: Z-A",
}


GAMES_EN = {
    "red": "Red", "blue": "Blue", "yellow": "Yellow", "gold": "Gold", "silver": "Silver", "crystal": "Crystal",
    "ruby": "Ruby", "sapphire": "Sapphire", "emerald": "Emerald", "firered": "FireRed", "leafgreen": "LeafGreen",
    "diamond": "Diamond", "pearl": "Pearl", "platinum": "Platinum", "heartgold": "HeartGold", "soulsilver": "SoulSilver",
    "black": "Black", "white": "White", "black-2": "Black 2", "white-2": "White 2", "x": "X", "y": "Y",
    "omega-ruby": "Omega Ruby", "alpha-sapphire": "Alpha Sapphire", "sun": "Sun", "moon": "Moon",
    "ultra-sun": "Ultra Sun", "ultra-moon": "Ultra Moon", "lets-go-pikachu": "Let's Go, Pikachu!",
    "lets-go-eevee": "Let's Go, Eevee!", "sword": "Sword", "shield": "Shield",
    "brilliant-diamond": "Brilliant Diamond", "shining-pearl": "Shining Pearl",
    "legends-arceus": "Legends: Arceus", "scarlet": "Scarlet", "violet": "Violet", "legends-za": "Legends: Z-A",
}
GAMES_ES = {
    "red": "Rojo", "blue": "Azul", "yellow": "Amarillo", "gold": "Oro", "silver": "Plata", "crystal": "Cristal",
    "ruby": "Rubí", "sapphire": "Zafiro", "emerald": "Esmeralda", "firered": "Rojo Fuego", "leafgreen": "Verde Hoja",
    "diamond": "Diamante", "pearl": "Perla", "platinum": "Platino", "heartgold": "Oro HeartGold", "soulsilver": "Plata SoulSilver",
    "black": "Negro", "white": "Blanco", "black-2": "Negro 2", "white-2": "Blanco 2", "x": "X", "y": "Y",
    "omega-ruby": "Rubí Omega", "alpha-sapphire": "Zafiro Alfa", "sun": "Sol", "moon": "Luna",
    "ultra-sun": "Ultrasol", "ultra-moon": "Ultraluna", "lets-go-pikachu": "Let's Go, Pikachu!",
    "lets-go-eevee": "Let's Go, Eevee!", "sword": "Espada", "shield": "Escudo",
    "brilliant-diamond": "Diamante Brillante", "shining-pearl": "Perla Reluciente",
    "legends-arceus": "Leyendas Pokémon: Arceus", "scarlet": "Escarlata", "violet": "Púrpura", "legends-za": "Leyendas Pokémon: Z-A",
}
GAMES = {"de": GAMES_DE, "en": GAMES_EN, "es": GAMES_ES}
DEX_LANGS = ("de", "en", "es")  # Sprachen der Oberflaeche und des Pokedex (Namen, Kategorie, Eintrag)


def dex_entry(d, lang):
    """Kategorie, neuester Pokedex-Eintrag und Spiel in einer Sprache aus den PokeAPI-Daten."""
    genus = next((g["genus"] for g in d.get("genera", []) if g["language"]["name"] == lang), "")
    best, best_v = None, -1
    for e in d.get("flavor_text_entries", []):
        if e["language"]["name"] != lang:
            continue
        vid = int(e["version"]["url"].rstrip("/").rsplit("/", 1)[1])
        if vid > best_v:  # hoehere Versions-ID = neueres Spiel
            best, best_v = e, vid
    text, game = "", ""
    if best:
        raw = re.sub(r"-[\n\f]+(?=[a-zäöüßáéíóúñ])", "", best["flavor_text"].replace("\u00ad", ""))  # Silbentrennung am Zeilenende aufheben
        text = re.sub(r"\s+", " ", re.sub(r"-[\n\f]+", "-", raw)).strip()  # Bindestrich vor Grossbuchstaben bleibt erhalten
        slug = best["version"]["name"]
        game = GAMES.get(lang, GAMES_EN).get(slug, slug.replace("-", " ").title())
    return genus, text, game


def species_info(d):
    """Namen (de, en, ja, es) und Pokedex-Eintraege (de, en, es) aus den PokeAPI-Daten."""
    nm = lambda code: next((n["name"] for n in d["names"] if n["language"]["name"] == code), "")
    names = {"de": nm("de") or d["name"].capitalize(), "en": nm("en"), "ja": nm("ja-Hrkt") or nm("ja"), "es": nm("es") or nm("en")}
    return names, {lang: dex_entry(d, lang) for lang in DEX_LANGS}


def load_pokemon():
    """Holt Namen und Pokedex-Eintraege aller Pokemon von PokeAPI (fehlende werden nachgeladen)."""
    progress["running"] = True
    try:
        total = fetch(f"{POKE}/pokemon-species?limit=1")["count"]
        have = ({r["id"] for r in q("SELECT id FROM pokemon WHERE name_en IS NOT NULL AND name_es IS NOT NULL")}
                & {r["id"] for r in q("SELECT id FROM dex_info")} & {r["id"] for r in q("SELECT id FROM dex_text WHERE lang='es'")})
        todo = [i for i in range(1, total + 1) if i not in have]
        progress.update(done=total - len(todo), total=total)

        def one(i):
            for _ in range(3):
                try:
                    return (i,) + species_info(fetch(f"{POKE}/pokemon-species/{i}"))
                except Exception:
                    pass
            return i, None, None

        with ThreadPoolExecutor(8) as ex:
            for i, names, entries in ex.map(one, todo):
                if names:
                    run("INSERT OR REPLACE INTO pokemon(id, name, name_en, name_ja, name_es) VALUES(?,?,?,?,?)",
                        (i, names["de"], names["en"], names["ja"], names["es"]))
                    run("INSERT OR REPLACE INTO dex_info VALUES(?,?,?,?)", (i,) + entries["de"])
                    for lang in ("en", "es"):
                        run("INSERT OR REPLACE INTO dex_text VALUES(?,?,?,?,?)", (i, lang) + entries[lang])
                    progress["done"] += 1
    finally:
        progress["running"] = False


def best_price(card):
    """Cardmarket-Trend in EUR (Fallbacks: Durchschnitt, niedrigster Preis, Foil-Preise)."""
    cm = (card.get("pricing") or {}).get("cardmarket") or {}
    for k in ("trend", "avg", "low", "trend-holo", "avg-holo"):
        v = cm.get(k)
        if isinstance(v, (int, float)) and v > 0:
            return round(v, 2)
    return None


def holo_price(card):
    """Cardmarket-Foil-Preis (Reverse Holo/Holo) in EUR."""
    cm = (card.get("pricing") or {}).get("cardmarket") or {}
    for k in ("trend-holo", "avg-holo", "low-holo"):
        v = cm.get(k)
        if isinstance(v, (int, float)) and v > 0:
            return round(v, 2)
    return None


def cm_product(card):
    cm = (card.get("pricing") or {}).get("cardmarket") or {}
    v = str(cm.get("idProduct") or "")
    return int(v) if v.isdigit() else None


def card_prices(card, lang):
    """(Normalpreis, Foil-Preis, Cardmarket-ID). Fehlt etwas, wird die englische Version derselben Karte befragt."""
    p, h, cid = best_price(card), holo_price(card), cm_product(card)
    if (p is None or cid is None) and lang != "ja":
        try:
            en = fetch(f"{TCG}/en/cards/{card['id']}")
            p = p if p is not None else best_price(en)
            h = h if h is not None else holo_price(en)
            cid = cid or cm_product(en)
        except Exception:
            pass
    return p, h, cid


def card_price(card, lang):
    """Preis der Karte; fehlt er in der Kartensprache, wird die englische Version derselben Karte befragt."""
    p = best_price(card)
    if p is None and lang != "ja":
        try:
            p = best_price(fetch(f"{TCG}/en/cards/{card['id']}"))
        except Exception:
            pass
    return p


def split_cid(cid):
    return cid.split(":", 1) if ":" in cid else ("de", cid)


def refresh_prices(only_new=False):
    price_prog["running"] = True
    try:
        today = datetime.date.today().isoformat()
        where = (f" WHERE (price IS NULL AND (price_at IS NULL OR price_at < '{today}')) OR px_at IS NULL") if only_new else ""
        rows = q("SELECT id FROM cards" + where)
        if not only_new:
            rows += [{"id": r["card_id"]} for r in q("SELECT card_id FROM wishlist")]
        price_prog.update(done=0, total=len(rows), missing=0, errors=0, last_error="")

        def one(r):
            lang, tid = split_cid(r["id"])
            try:
                return r["id"], card_prices(fetch(f"{TCG}/{lang}/cards/{tid}"), lang), None
            except Exception as e:
                return r["id"], None, str(e)

        with ThreadPoolExecutor(8) as ex:
            for cid, pr, err in ex.map(one, rows):
                if err:
                    price_prog["errors"] += 1
                    price_prog["last_error"] = err
                else:
                    p, h, cmid = pr
                    run("UPDATE cards SET price_old=CASE WHEN price IS NOT NULL AND ? IS NOT NULL AND ABS(price - ?) > 0.004 THEN price ELSE price_old END, "
                        "price=?, price_holo=?, cm_id=COALESCE(?, cm_id), price_at=?, px_at=? WHERE id=?",
                        (p, p, p, h, cmid, today, today, cid))
                    if p is not None:
                        run("UPDATE wishlist SET price_old=CASE WHEN price IS NOT NULL AND ABS(price - ?) > 0.004 THEN price ELSE price_old END, price=? WHERE card_id=?",
                            (p, p, cid))
                    if p is None:
                        price_prog["missing"] += 1
                price_prog["done"] += 1
    finally:
        price_prog["running"] = False


def get_sets(lang):
    if lang not in _sets:
        _sets[lang] = list(reversed(fetch(f"{TCG}/{lang}/sets")))  # neueste zuerst
    return _sets[lang]


def find_card(lang, set_id, num):
    cands = [num, str(int(num)), num.zfill(3), num.zfill(2)] if num.isdigit() else [num]  # "008" findet auch "8" und umgekehrt
    for cand in dict.fromkeys(cands):
        try:
            return fetch(f"{TCG}/{lang}/cards/{set_id}-{cand}")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
    return None


COND_LABELS = {"MT": "Mint", "NM": "Near Mint", "EX": "Excellent", "GD": "Good", "LP": "Light Played", "PL": "Played", "PO": "Poor"}


def meta_get(k, default=None):
    r = q("SELECT val FROM meta WHERE key=?", (k,))
    return r[0]["val"] if r and r[0]["val"] is not None else default


def meta_set(k, v):
    run("INSERT OR REPLACE INTO meta VALUES(?,?)", (k, None if v is None else str(v)))


def meta_inc(k, n=1):
    meta_set(k, int(meta_get(k, 0) or 0) + n)


def log_session(cid, delta, newc=False, newp=False):
    """Haelt waehrend einer Pack-Session fest, was dazukommt (oder wegfaellt)."""
    if not meta_get("session_start"):
        return
    r = q("SELECT name, set_name, image, price, price_holo, price_own, variant FROM cards WHERE id=?", (cid,))
    if r:
        run("INSERT INTO session_log(ts, card_id, name, set_name, image, price, delta, newc, newp) VALUES(?,?,?,?,?,?,?,?,?)",
            (time.strftime("%H:%M:%S"), cid, r[0]["name"], r[0]["set_name"], r[0]["image"], r[0]["price"], delta, int(newc), int(newp)))


def session_summary():
    rows = q("SELECT * FROM session_log ORDER BY id")
    net = {}
    for r in rows:
        e = net.setdefault(r["card_id"], {"name": r["name"], "set_name": r["set_name"], "image": r["image"], "price": r["price"], "qty": 0})
        e["qty"] += r["delta"]
    sets = {}
    for e in net.values():
        if e["qty"] > 0:
            t = sets.setdefault(e["set_name"], {"set_name": e["set_name"], "cards": 0, "value": 0.0})
            t["cards"] += e["qty"]
            t["value"] += (e["price"] or 0) * e["qty"]
    top = sorted((e for e in net.values() if e["qty"] > 0), key=lambda e: -(e["price"] or 0))[:6]
    return {"active": bool(meta_get("session_start")), "started": meta_get("session_start"),
            "cards": sum(r["delta"] for r in rows), "value": round(sum((r["price"] or 0) * r["delta"] for r in rows), 2),
            "new_cards": sum(r["newc"] for r in rows), "new_pokemon": sum(r["newp"] for r in rows),
            "top": top, "sets": sorted(({**t, "value": round(t["value"], 2)} for t in sets.values()), key=lambda t: -t["value"])[:5]}


def category_of(card):
    """Pokemon / Trainer / Energy (sprachunabhaengig ueber typische Felder erkannt)."""
    if card.get("trainerType"):
        return "Trainer"
    if card.get("energyType"):
        return "Energy"
    if card.get("hp") or card.get("dexId") or card.get("stage") or card.get("attacks"):
        return "Pokemon"
    c = str(card.get("category", "")).lower()
    if c.startswith(("train", "トレー")):
        return "Trainer"
    if c.startswith(("energ", "エネル")):
        return "Energy"
    return "Pokemon" if c.startswith(("pok", "ポケ")) else "Sonstiges"


def backfill_categories():
    """Traegt die Kartenart bei bereits vorhandenen Karten nach."""
    run("UPDATE cards SET category='Pokemon' WHERE category IS NULL AND dex_id IS NOT NULL")
    rows = q("SELECT id FROM cards WHERE category IS NULL")

    def one(r):
        lang, tid = split_cid(r["id"])
        try:
            return r["id"], category_of(fetch(f"{TCG}/{lang}/cards/{tid}"))
        except Exception:
            return r["id"], None

    with ThreadPoolExecutor(8) as ex:
        for cid, cat in ex.map(one, rows):
            if cat:
                run("UPDATE cards SET category=? WHERE id=?", (cat, cid))


def card_row(card, lang):
    dex_id = (card.get("dexId") or [None])[0]
    prices = card_prices(card, lang)
    set_name = card["set"]["name"]
    if lang == "ja":
        set_name = ja_set_names().get(norm_code(card["set"]["id"])) or set_name
    cid = card["id"] if lang == "de" else f"{lang}:{card['id']}"
    return dict(
        id=cid, name=card["name"], set_name=set_name, set_id=card["set"]["id"],
        local_id=card["localId"], rarity=card.get("rarity", ""),
        image=(card["image"] + "/high.png") if card.get("image") else fallback_image(lang, card["set"]["id"], card["localId"]),
        dex_id=dex_id, lang=lang, price=prices[0], price_holo=prices[1], cm_id=prices[2], category=category_of(card),
    )


def is_fullart(rarity):
    r = (rarity or "").lower()
    return any(k in r for k in FULLART_KEYS)


def norm_code(code):
    return re.sub(r"[^a-z0-9+]", "", str(code).lower())


def tp_groups(cat):
    """Sets einer TCGplayer-Kategorie (85 = Pokemon Japan, 3 = Pokemon) von tcgcsv.com: {Code: (groupId, Titel)}, Gruppennamen wie 'SV3: Ruler of the Black Flame'."""
    hit = _tpg.get(cat)
    if hit and hit[1] and time.time() - hit[0] < 86400:
        return hit[1]
    if hit and not hit[1] and time.time() - hit[0] < 600:  # nach Fehlern fruehestens nach 10 Minuten erneut versuchen
        return hit[1]
    out = {}
    try:
        data = fetch(f"https://tcgcsv.com/tcgplayer/{cat}/groups")
        for g in data.get("results") or data.get("Results") or []:
            code, sep, title = (g.get("name") or g.get("Name") or "").partition(":")
            gid = g.get("groupId") or g.get("GroupId")
            if gid:
                _tpl.setdefault(cat, {})[gid] = (title.strip() if sep else code.strip())  # alle Gruppen fuer die Namenssuche
            if sep and title.strip() and gid:
                out[norm_code(code)] = (gid, title.strip())
    except Exception:
        pass
    _tpg[cat] = (time.time(), out)
    return out


def name_tokens(txt):
    return set(re.sub(r"[^a-z0-9 ]", " ", str(txt).lower().replace("&", " ")).split())


def card_key(name):
    """Kartenname vergleichbar machen: 'Metagross (Delta Species)' und 'Metagross δ' -> 'metagross', 'Genesect EX' und 'Genesect-EX' -> 'genesectex'."""
    n = re.sub(r"\(.*?\)", "", str(name).lower()).split(" - ")[0]
    return re.sub(r"[^a-z0-9]", "", n)


def set_info(lang, set_id):
    try:
        return next((x for x in get_sets(lang) if x["id"] == set_id), None)
    except Exception:
        return None


def tp_group_for(lang, set_id):
    """TCGplayer-Gruppe zu einem Set: zuerst ueber das Kuerzel (z. B. 'SV3'), sonst ueber den englischen Set-Namen
    (z. B. '30th Celebration' -> 'ME: 30th Celebration', '30th Classic Collection' -> 'ME: 30th Celebration Classic Collection')."""
    cat = 85 if lang == "ja" else 3
    g = tp_groups(cat).get(norm_code(set_id))
    if g:
        return cat, g
    if cat != 3:
        return cat, None
    info = set_info("en", set_id)
    if not info:
        return cat, None
    want = name_tokens(info.get("name", ""))
    best, second = (0.0, None), 0.0
    for gid, title in (_tpl.get(cat) or {}).items():
        have = name_tokens(title)
        if not want or not have:
            continue
        wt = lambda ts: sum(2 if re.search(r"\d", t) else 1 for t in ts)  # Zahlen wie "30th" sind besonders aussagekraeftig
        sc = wt(want & have) / wt(want | have)
        if sc > best[0]:
            best, second = (sc, (gid, title)), best[0]
        elif sc > second:
            second = sc
    if best[0] >= 0.6 and best[0] - second >= 0.15:
        return cat, best[1]
    return cat, None


def ja_set_names():
    """Englische Namen japanischer Sets (Zuordnung ueber den Set-Code, z. B. 'SV3')."""
    return {k: v[1] for k, v in tp_groups(85).items()}


def tp_products(cat, gid):
    """Karten einer TCGplayer-Gruppe: [(Nummer ohne fuehrende Nullen, Set-Groesse oder None, Name, Bild, Sonderdruck?)]"""
    hit = _tpp.get((cat, gid))
    if hit and time.time() - hit[0] < 86400:
        return hit[1]
    try:
        data = fetch(f"https://tcgcsv.com/tcgplayer/{cat}/{gid}/products")
    except Exception:
        return []
    out = []
    for p in data.get("results") or []:
        ext = {e.get("name"): e.get("value") for e in p.get("extendedData") or []}
        num, img = ext.get("Number"), p.get("imageUrl")
        if not num or not img:
            continue
        n, _, d = str(num).partition("/")
        name = p.get("name") or ""
        special = any(x in name.lower() for x in ("reverse", "pattern", "master ball", "poke ball"))
        out.append((n.strip().lstrip("0").lower(), int(d) if d.strip().isdigit() else None, name, img, special))
    _tpp[(cat, gid)] = (time.time(), out)
    return out


def tp_images(lang, set_id):
    """Ersatz-Kartenbilder von TCGplayer: {Kartennummer ohne fuehrende Nullen: Bild-URL} plus {'n:' + Kartenname: Bild-URL}.
    Nummern werden nur uebernommen, wenn die Set-Groesse passt (bei der Classic Collection stehen dort die Originalnummern, z. B. 4/102)."""
    cat, g = tp_group_for(lang, set_id)
    if not g:
        return {}
    info = set_info(lang, set_id) or {}
    official = (info.get("cardCount") or {}).get("official")
    best, names = {}, {}
    for n, den, name, img, special in tp_products(cat, g[0]):
        if den is None or not official or den == official:
            if n not in best or (best[n][1] and not special):  # normale Karte bevorzugen
                best[n] = (img, special)
        k = "n:" + card_key(name)
        if k not in names or (names[k][1] and not special):
            names[k] = (img, special)
    out = {k: v[0] for k, v in names.items()}
    out.update({n: v[0] for n, v in best.items()})
    return out


def en_cards(set_id):
    """Karten der englischen Version eines Sets bei TCGdex: [(Nummer ohne fuehrende Nullen klein, Name, Bild-Basis oder '', Nummer wie gespeichert)]."""
    hit = _enc.get(set_id)
    if hit and time.time() - hit[0] < (86400 if hit[1] else 3600):
        return hit[1]
    out = []
    try:
        for c in fetch(f"{TCG}/en/sets/{set_id}").get("cards", []):
            out.append((str(c["localId"]).lstrip("0").lower(), c.get("name", ""), c.get("image") or "", str(c["localId"])))
    except Exception:
        pass
    _enc[set_id] = (time.time(), out)
    return out


def en_images(set_id):
    """Bilder der englischen Version desselben Sets bei TCGdex: {Nummer: Basis-URL}."""
    return {c[0]: c[2] for c in en_cards(set_id) if c[2]}


def fallback_map(lang, set_id, low=False):
    """Ersatzbilder {Nummer: URL}: zuerst die englische Version desselben Sets (TCGdex), dann TCGplayer."""
    tp = tp_images(lang, set_id)
    out = {k: v for k, v in tp.items() if not k.startswith("n:")}
    if lang not in ("en", "ja"):
        out.update({n: b + ("/low.webp" if low else "/high.png") for n, b in en_images(set_id).items()})
    if lang != "ja" and any(k.startswith("n:") for k in tp):  # Karten ohne Treffer ueber die Nummer: ueber den englischen Namen zuordnen
        for n, name, *_ in en_cards(set_id):
            if n not in out and tp.get("n:" + card_key(name)):
                out[n] = tp["n:" + card_key(name)]
    return out


def fallback_image(lang, set_id, local_id, low=False):
    return fallback_map(lang, set_id, low).get(str(local_id).split("/")[0].lstrip("0").lower(), "")


def backfill_images():
    """Fuellt fehlende Kartenbilder bei vorhandenen Karten aus der Ersatzquelle nach."""
    for r in q("SELECT id, local_id FROM cards WHERE image IS NULL OR image = ''"):
        lang, tid = split_cid(r["id"])
        img = fallback_image(lang, tid.rsplit("-", 1)[0], r["local_id"])
        if img:
            run("UPDATE cards SET image=? WHERE id=?", (img, r["id"]))


def backfill_ja_names():
    """Ersetzt japanische Set-Namen bei vorhandenen japanischen Karten durch die englischen."""
    names = ja_set_names()
    if not names:
        return
    for r in q("SELECT id, set_name FROM cards WHERE lang='ja'"):
        en = names.get(norm_code(split_cid(r["id"])[1].rsplit("-", 1)[0]))
        if en and en != r["set_name"]:
            run("UPDATE cards SET set_name=? WHERE id=?", (en, r["id"]))


def dex_brief(lang, dex_id):
    """Alle Karten (Kurzform) eines Pokemon in einer Sprache. Zwischengespeichert fuer 1 Stunde."""
    hit = _dexcache.get((lang, dex_id))
    if hit and time.time() - hit[0] < 3600:
        return hit[1]
    cards = None
    for url, strict in ((f"{TCG}/{lang}/dex-ids/{dex_id}", False), (f"{TCG}/{lang}/cards?dexId=eq:{dex_id}", True),
                        (f"{TCG}/{lang}/cards?dexId={dex_id}", True)):
        try:
            d = fetch(url)
        except Exception:
            continue
        lst = d.get("cards") if isinstance(d, dict) else d
        if isinstance(lst, list) and not (strict and len(lst) > 2000):  # Filter wirkungslos -> verwerfen
            cards = lst
            break
    if cards is None:
        raise RuntimeError("Kartenliste nicht abrufbar")
    _dexcache[(lang, dex_id)] = (time.time(), cards)
    return cards


def natural_key(text):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(text))]


def dex_payload(dex_id, lang):
    """Alle Karten eines Pokemon (komplette Datenbank) mit Stand in der Sammlung, neueste Sets zuerst."""
    sets = get_sets(lang)
    names = {s["id"]: s["name"] for s in sets}
    if lang == "ja":
        en = ja_set_names()
        names = {k: en.get(norm_code(k)) or v for k, v in names.items()}
    order = {s["id"]: i for i, s in enumerate(sets)}
    qty = {r["id"]: r["qty"] for r in q("SELECT id, qty FROM cards")}
    binder = {r["card_id"] for r in q("SELECT card_id FROM binder")}
    wish = {r["card_id"] for r in q("SELECT card_id FROM wishlist")}
    cards = []
    for c in dex_brief(lang, dex_id):
        tid = c["id"]
        sid = tid.rsplit("-", 1)[0]
        cid = tid if lang == "de" else f"{lang}:{tid}"
        cards.append({"tid": tid, "local_id": c.get("localId", ""), "name": c.get("name", ""),
                      "image": c["image"] + "/low.webp" if c.get("image") else "", "set_id": sid,
                      "set_name": names.get(sid, sid), "owned": qty.get(cid, 0), "in_binder": cid in binder,
                      "wished": cid in wish, "_o": order.get(sid, 9999)})
    cards.sort(key=lambda x: (x["_o"], natural_key(x["local_id"])))
    missing = sorted({c["set_id"] for c in cards if not c["image"]})[:30]
    if missing:  # Bilder aus der Ersatzquelle (Sets parallel vorladen, danach kommt alles aus dem Zwischenspeicher)
        with ThreadPoolExecutor(6) as ex:
            list(ex.map(lambda sid: fallback_map(lang, sid, low=True), missing))
        for c in cards:
            if not c["image"]:
                c["image"] = fallback_image(lang, c["set_id"], c["local_id"], low=True)
    for c in cards:
        del c["_o"]
    genus, text, game = dex_text(dex_id)
    info = {"name": dex_name(dex_id), "genus": genus, "text": text, "game": game}
    cur = q("SELECT c.* FROM binder b JOIN cards c ON c.id = b.card_id WHERE b.dex_id=?", (dex_id,))
    return {"status": "ok", "dex_id": dex_id, "lang": lang, "name": info["name"], "genus": info["genus"] or "",
            "text": info["text"] or "", "game": info["game"] or "", "binder_card": cur[0] if cur else None, "cards": cards}


_nidx = {"key": None}


def name_index():
    """Namen aller Pokemon (de, en, ja) fuer die Zuordnung von Kartennamen."""
    rows = q("SELECT id, name, name_en, name_ja FROM pokemon")
    key = (len(rows), sum(1 for r in rows if r["name_en"]))
    if _nidx["key"] != key:
        latin, ja, de = {}, {}, {}
        for r in rows:
            de[r["id"]] = r["name"]
            for nm in (r["name"], r["name_en"]):
                k = (nm or "").strip().lower()
                if len(k) >= 3:
                    latin.setdefault(k, r["id"])
            if r["name_ja"] and len(r["name_ja"]) >= 2:
                ja.setdefault(r["name_ja"], r["id"])
        rx = re.compile("|".join(re.escape(x) for x in sorted(ja, key=len, reverse=True))) if ja else None
        _nidx.update(key=key, latin=latin, ja=ja, rx=rx, de=de)
    return _nidx


def guess_dex(card_name):
    """Pokedex-Nummer aus einem Kartennamen (deutsch, englisch oder japanisch), z. B. 'Team Rockets Hypno' oder 'メガガグソクムシャex'."""
    idx = name_index()
    best = (0, None)
    if idx["rx"]:
        for m in idx["rx"].finditer(card_name):  # laengster Treffer gewinnt
            if len(m.group()) > best[0]:
                best = (len(m.group()), idx["ja"][m.group()])
    toks = [t.strip(".,:;!?()[]{}\"") for t in card_name.lower().split()]
    cands = set()
    for i, t in enumerate(toks):
        cands.add(t)
        if "-" in t:
            cands.update(t.split("-"))
        if i + 1 < len(toks):
            cands.add(t + " " + toks[i + 1])
        if i + 2 < len(toks):
            cands.add(t + " " + toks[i + 1] + " " + toks[i + 2])
    for c in cands:
        did = idx["latin"].get(c)
        if did and len(c) > best[0]:
            best = (len(c), did)
    return best[1]


def inc_local(local_id):
    """Naechste Kartennummer, z. B. 114 -> 115, 099 -> 100, TG05 -> TG06."""
    m = re.match(r"^(\D*)(\d+)(\D*)$", str(local_id))
    if not m:
        return None
    return f"{m.group(1)}{int(m.group(2)) + 1:0{len(m.group(2))}d}{m.group(3)}"


def slot_info(row):
    """Ergaenzt eine Karte um ihren Stand in der Sammlung (Anzahl, im Binder?, aktuelle Binder-Karte)."""
    owned = q("SELECT qty FROM cards WHERE id=?", (row["id"],))
    row["owned_qty"] = owned[0]["qty"] if owned else 0
    row["wished"] = bool(q("SELECT 1 FROM wishlist WHERE card_id=?", (row["id"],)))
    cur = q("SELECT c.* FROM binder b JOIN cards c ON c.id=b.card_id WHERE b.dex_id=?", (row["dex_id"],)) if row["dex_id"] else []
    row["in_binder"] = bool(cur) and cur[0]["id"] == row["id"]
    row["binder_card"] = cur[0] if cur and cur[0]["id"] != row["id"] else None
    row["dex_name"] = dex_name(row["dex_id"]) if row["dex_id"] else ""
    row["dex_genus"], row["dex_text"], row["dex_game"] = dex_text(row["dex_id"]) if row["dex_id"] else ("", "", "")
    return row


def get_series(lang):
    cached = _series.get(lang)
    if cached and time.time() - cached[0] < 86400:
        return cached[1]
    lst = fetch(f"{TCG}/{lang}/series")

    def date_of(set_id):
        try:
            return fetch(f"{TCG}/{lang}/sets/{set_id}").get("releaseDate") or ""
        except Exception:
            return ""

    def detail(sr):
        sid = sr["id"]
        info = {"id": sid, "name": sr.get("name", sid), "date": "", "included": False}
        if sid in SERIES_SKIP:
            return info, None
        try:
            ser = fetch(f"{TCG}/{lang}/series/{sid}")
        except Exception:
            return info, None
        sets = ser.get("sets", [])
        if sets:
            info["date"] = max(date_of(sets[0]["id"]), date_of(sets[-1]["id"]))
        if not sets or info["date"] < MIN_DATE:
            return info, None
        info["included"] = True
        return info, {"id": sid, "name": ser.get("name", sid), "date": info["date"], "sets": list(reversed(sets))}  # neueste Sets zuerst

    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(detail, lst))
    out = sorted((r[1] for r in res if r[1]), key=lambda r: r["date"], reverse=True)  # neueste Serie zuerst
    _series_dbg[lang] = [r[0] for r in res]
    if out:
        _series[lang] = (time.time(), out)
    return out


# ================= Sprachen der Oberflaeche (de, en, es)
# Die Oberflaeche ist auf Deutsch geschrieben, static/i18n.js uebersetzt sie im Browser mit static/i18n/<lang>.json.
# Welche Sprachen zur Auswahl stehen, steht in meta (ui_langs, ui_default). NINEDEX_LANGS (z. B. "de,en",
# die erste ist die Standardsprache) setzt sie von aussen, etwa der Windows-Installer oder docker-compose.
UI_LANGS = DEX_LANGS
_dicts = {}


def ui_config():
    env = ",".join(l for l in (x.strip().lower() for x in (os.environ.get("NINEDEX_LANGS") or os.environ.get("BINDERDEX_LANGS") or "").split(",")) if l in UI_LANGS)
    if env and env != meta_get("ui_env", ""):  # neue Auswahl von aussen (Installer, Umgebungsvariable) uebernehmen
        meta_set("ui_langs", env)
        meta_set("ui_default", env.split(",")[0])
        meta_set("ui_env", env)
    langs = [l for l in (meta_get("ui_langs", "") or "").split(",") if l in UI_LANGS]
    default = meta_get("ui_default", "") or ""
    if not langs:
        return {"langs": list(UI_LANGS), "default": "", "configured": False}
    return {"langs": langs, "default": default if default in langs else langs[0], "configured": True}


def ui_lang():
    """Sprache der aktuellen Anfrage: Cookie bzw. ?ui= vom Browser, sonst die Standardsprache."""
    if has_request_context():
        l = (request.args.get("ui") or request.headers.get("X-UI-Lang") or request.cookies.get("ui_lang") or "").lower()
        if l in UI_LANGS:
            return l
    c = ui_config()
    return c["default"] or "de"


def ui_dict(lang):
    if lang not in _dicts:
        try:
            with open(os.path.join(app.root_path, "static", "i18n", f"{lang}.json"), encoding="utf-8") as f:
                _dicts[lang] = json.load(f)
        except (OSError, ValueError):
            _dicts[lang] = {}
    return _dicts[lang]


def tr(text, lang=None):
    """Deutschen Text fuer Exporte uebersetzen (gleiches Woerterbuch wie im Browser, nur exakte Treffer)."""
    lang = lang or ui_lang()
    return text if lang == "de" else ui_dict(lang).get(text, text)


def pname(alias="p"):
    """SQL-Ausdruck fuer den Pokemon-Namen in der Sprache der Anfrage (Rueckfall: deutsch)."""
    l = ui_lang()
    return f"COALESCE(NULLIF({alias}.name_{l}, ''), {alias}.name)" if l in ("en", "es") else f"{alias}.name"


def dex_text(dex_id, lang=None):
    """(Kategorie, Pokedex-Eintrag, Spiel) in der Sprache der Anfrage; fehlt der Eintrag, zuerst Englisch, dann Deutsch."""
    lang = lang or ui_lang()
    de = q("SELECT genus, text, game FROM dex_info WHERE id=?", (dex_id,))
    rows = {r["lang"]: r for r in q("SELECT lang, genus, text, game FROM dex_text WHERE id=?", (dex_id,))}
    rows["de"] = de[0] if de else None
    for l in (lang, "en", "de"):
        r = rows.get(l)
        if r and r["text"]:
            genus = (rows.get(lang) or {}).get("genus") or r["genus"] or ""
            return genus, r["text"], r["game"] or ""
    r = rows.get(lang) or rows.get("de")
    return ((r["genus"] or ""), "", "") if r else ("", "", "")


def dex_name(dex_id):
    r = q(f"SELECT {pname()} AS name FROM pokemon p WHERE id=?", (dex_id,))
    return r[0]["name"] if r else f"#{dex_id}"


@app.get("/favicon.ico")
def favicon():
    """Symbol fuer den Browser-Tab (Browser fragen es automatisch unter dieser Adresse ab)."""
    return send_from_directory("static", "favicon.ico", mimetype="image/vnd.microsoft.icon", max_age=86400)


def i18n_head():
    """Sprach-Konfiguration und Uebersetzer fuer den Kopf jeder HTML-Seite."""
    cfg = dict(ui_config(), v=I18N_VERSION)
    return (f'<script>window.BDX_CFG={json.dumps(cfg)};</script>'
            f'<script src="/static/i18n.js?v={I18N_VERSION}"></script>')


@app.get("/")
def index():
    with open(os.path.join(app.root_path, "static", "index.html"), encoding="utf-8") as f:
        page = f.read()
    resp = Response(page.replace("<!--I18N-->", i18n_head(), 1), mimetype="text/html")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.get("/i18n/<lang>.js")
def i18n_dict(lang):
    """Woerterbuch einer Sprache als Skript (Deutsch ist die Ausgangssprache und braucht keins)."""
    d = ui_dict(lang) if lang in UI_LANGS and lang != "de" else {}
    return Response("window.BDX_DICT=" + json.dumps(d, ensure_ascii=False) + ";", mimetype="text/javascript",
                    headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/i18n")
def i18n_get():
    return jsonify(dict(ui_config(), all=list(UI_LANGS)))


@app.post("/api/i18n")
def i18n_set():
    """Sprachen, die in der App zur Auswahl stehen (erste = Standard fuer neue Geraete)."""
    d = request.json or {}
    langs = [l for l in d.get("langs", []) if l in UI_LANGS]
    langs = list(dict.fromkeys(langs))
    if not langs:
        return jsonify(ok=False, msg="Mindestens eine Sprache auswählen."), 400
    default = d.get("default") if d.get("default") in langs else langs[0]
    meta_set("ui_langs", ",".join([default] + [l for l in langs if l != default]))
    meta_set("ui_default", default)
    return jsonify(ok=True, **ui_config())


@app.get("/api/dex")
def dex():
    rows = q(
        f"""SELECT p.id, {pname()} AS name, c.id AS cid, c.name AS cname, c.set_name, c.rarity, c.image, c.lang, c.price, c.price_holo, c.price_own, c.variant,
                  (SELECT COUNT(*) FROM cards x WHERE x.dex_id = p.id) AS n,
                  (SELECT COALESCE(SUM(x.qty), 0) FROM cards x WHERE x.dex_id = p.id) AS total,
                  (SELECT COUNT(*) FROM favorites f WHERE f.dex_id = p.id) AS fav
           FROM pokemon p
           LEFT JOIN binder b ON b.dex_id = p.id
           LEFT JOIN cards c ON c.id = b.card_id
           ORDER BY p.id"""
    )
    for r in rows:
        r["fa"] = 1 if r["cid"] and is_fullart(r["rarity"]) else 0
    side = q("SELECT COALESCE(SUM(CASE WHEN id IN (SELECT card_id FROM binder) THEN qty - 1 ELSE qty END), 0) AS n FROM cards")[0]["n"]
    v = q(f"""SELECT COALESCE(SUM({psql()} * qty), 0) AS a,
             (SELECT COALESCE(SUM({psql('c.')}), 0) FROM binder b JOIN cards c ON c.id = b.card_id) AS b FROM cards""")[0]
    snapshot(v["b"], v["a"], sum(1 for r in rows if r["cid"]))
    sess = session_summary()
    return jsonify(rows=rows, progress=progress, prices=price_prog, side=side, session={"active": sess["active"], "cards": sess["cards"], "value": sess["value"]},
                   value_all=round(v["a"], 2), value_binder=round(v["b"], 2))


def snapshot(binder_value, total_value, caught):
    """Speichert einmal pro Tag (und bei Aenderungen) den Sammlungswert fuer den Verlauf."""
    n = q("SELECT COUNT(*) AS n FROM cards")[0]["n"]
    if not n:
        return
    today = datetime.date.today().isoformat()
    new = (round(binder_value, 2), round(total_value, 2), caught)
    cur = q("SELECT binder, total, caught FROM value_history WHERE day=?", (today,))
    if not cur or (cur[0]["binder"], cur[0]["total"], cur[0]["caught"]) != new:
        run("INSERT OR REPLACE INTO value_history VALUES(?,?,?,?,?)", (today, new[0], new[1], n, caught))


def streaks(days):
    """(laengste Serie, aktuelle Serie) aufeinanderfolgender Tage, an denen Karten hinzugekommen sind."""
    ds = sorted({datetime.date.fromisoformat(d) for d in days if d})
    best = cur = 0
    prev = None
    for d in ds:
        cur = cur + 1 if prev and (d - prev).days == 1 else 1
        best, prev = max(best, cur), d
    today = datetime.date.today()
    now_streak = cur if prev and (today - prev).days <= 1 else 0
    return best, now_streak


def set_progress():
    """(Anzahl verschiedener Sets mit Karten, Namen komplett gesammelter Sets). Komplett = alle Nummern 1..Setgroesse vorhanden."""
    per = {}
    for r in q("SELECT id, local_id, set_name FROM cards"):
        lang, tid = split_cid(r["id"])
        e = per.setdefault((lang, tid.rsplit("-", 1)[0]), {"name": r["set_name"], "nums": set()})
        m = re.match(r"^\d+$", str(r["local_id"]).strip())
        if m:
            e["nums"].add(int(r["local_id"]))
    complete = []
    for lang in {k[0] for k in per}:
        try:
            official = {x["id"]: (x.get("cardCount") or {}).get("official") for x in get_sets(lang)}
        except Exception:
            continue
        for (l, sid), e in per.items():
            size = official.get(sid)
            if l == lang and size and all(n in e["nums"] for n in range(1, size + 1)):
                complete.append(e["name"])
    return len(per), sorted(complete)


@app.get("/api/stats")
def stats():
    top_id = q("SELECT MAX(id) AS m FROM pokemon")[0]["m"] or 1025
    binder = q("SELECT b.dex_id, c.rarity, c.price, c.price_holo, c.price_own, c.variant FROM binder b JOIN cards c ON c.id = b.card_id")
    gens = []
    for roman, region, lo, hi in GENS:
        gens.append({"gen": roman, "region": region, "lo": lo, "hi": hi, "total": max(0, min(hi, top_id) - lo + 1),
                     "caught": sum(1 for b in binder if lo <= b["dex_id"] <= hi)})
    tot = q(f"SELECT COALESCE(SUM(qty), 0) AS cards, COUNT(*) AS distinct_cards, COALESCE(SUM({psql()} * qty), 0) AS value FROM cards")[0]
    top = q(f"""SELECT c.id, c.name, c.set_name, c.local_id, c.rarity, c.image, c.lang, c.price, c.price_holo, c.price_own, c.variant, c.qty,
                      {pname()} AS dex_name, (b.card_id IS NOT NULL) AS in_binder
               FROM cards c LEFT JOIN pokemon p ON p.id = c.dex_id LEFT JOIN binder b ON b.card_id = c.id
               WHERE ({psql('c.')}) IS NOT NULL ORDER BY ({psql('c.')}) DESC LIMIT 10""")
    hist = q("SELECT day, binder, total, cards, caught FROM value_history ORDER BY day DESC LIMIT 120")[::-1]
    streak_best, streak_now = streaks([r["added"] for r in q("SELECT DISTINCT added FROM cards WHERE added IS NOT NULL")])
    sets_owned, sets_complete = set_progress()
    movers = {
        "up": q("""SELECT name, set_name, local_id, image, lang, price, price_old, (price - price_old) AS diff FROM cards
                   WHERE price_old IS NOT NULL AND price IS NOT NULL AND price > price_old ORDER BY diff DESC LIMIT 5"""),
        "down": q("""SELECT name, set_name, local_id, image, lang, price, price_old, (price - price_old) AS diff FROM cards
                     WHERE price_old IS NOT NULL AND price IS NOT NULL AND price < price_old ORDER BY diff ASC LIMIT 5"""),
    }
    value_sets = q(f"""SELECT set_name, SUM(({psql()}) * qty) AS value, SUM(qty) AS cards FROM cards
                       GROUP BY set_name HAVING value IS NOT NULL ORDER BY value DESC LIMIT 5""")
    return jsonify(
        streak_best=streak_best, streak_now=streak_now, sets_owned=sets_owned, sets_complete=sets_complete, movers=movers, value_sets=value_sets,
        fav_count=q("SELECT COUNT(*) AS n FROM favorites")[0]["n"], wish_count=q("SELECT COUNT(*) AS n FROM wishlist")[0]["n"],
        spare_total=q("SELECT COALESCE(SUM(CASE WHEN id IN (SELECT card_id FROM binder) THEN qty - 1 ELSE qty END), 0) AS n FROM cards")[0]["n"],
        counters={k: int(meta_get(k, 0) or 0) for k in ("scans", "exports", "sessions", "big_sessions", "grade_checks", "grades_saved", "listings", "sold")},
        caught=len(binder), species=top_id, cards=tot["cards"], distinct=tot["distinct_cards"],
        value_all=round(tot["value"], 2), value_binder=round(sum(b["price"] or 0 for b in binder), 2),
        fullart=sum(1 for b in binder if is_fullart(b["rarity"])), gens=gens, top=top, history=hist,
        langs=q("SELECT COALESCE(lang, 'de') AS lang, SUM(qty) AS n FROM cards GROUP BY COALESCE(lang, 'de')"),
        rarities=q("SELECT rarity, SUM(qty) AS n FROM cards WHERE rarity IS NOT NULL AND rarity != '' GROUP BY rarity ORDER BY n DESC LIMIT 8"),
        max_price=max([c["price"] for c in top] or [0]))


@app.get("/api/randommissing")
def randommissing():
    r = q("SELECT id FROM pokemon WHERE id NOT IN (SELECT dex_id FROM binder) ORDER BY RANDOM() LIMIT 1")
    return jsonify(dex_id=r[0]["id"] if r else None)


@app.post("/api/wish")
def wish():
    d = request.json
    if d.get("action") == "remove":
        run("DELETE FROM wishlist WHERE card_id=?", (d["card_id"],))
        return jsonify(ok=True)
    c = d["card"]
    run("INSERT OR REPLACE INTO wishlist(card_id, name, set_name, set_id, local_id, rarity, image, dex_id, lang, price, added) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (c["id"], c["name"], c["set_name"], c.get("set_id", ""), c["local_id"], c.get("rarity", ""), c.get("image", ""),
         c.get("dex_id"), c.get("lang", "de"), c.get("price"), datetime.date.today().isoformat()))
    return jsonify(ok=True)


@app.get("/api/trade")
def trade():
    """Tauschliste: was du abgeben kannst (Nebenstapel + doppelte Exemplare) und was du suchst (Wunschliste)."""
    offer = q(f"""SELECT * FROM (
                   SELECT c.id, c.name, c.set_name, c.local_id, c.rarity, c.image, c.lang, c.price, c.price_holo, c.price_own, c.variant, {pname()} AS dex_name,
                          CASE WHEN b.card_id IS NULL THEN c.qty ELSE c.qty - 1 END AS spare
                   FROM cards c LEFT JOIN pokemon p ON p.id = c.dex_id LEFT JOIN binder b ON b.card_id = c.id)
                 WHERE spare > 0""")
    offer.sort(key=lambda o: (o["price"] is None, -(o["price"] or 0)))
    wishes = q(f"""SELECT w.*, {pname()} AS dex_name FROM wishlist w LEFT JOIN pokemon p ON p.id = w.dex_id ORDER BY w.added DESC""")
    return jsonify(offer=offer, wishes=wishes)


@app.get("/api/export.csv")
def export_csv():
    kind = request.args.get("kind", "cards")
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    if kind == "missing":
        w.writerow([tr("Pokédex-Nr."), "Pokémon"])
        for r in q(f"SELECT id, {pname()} AS name FROM pokemon p WHERE id NOT IN (SELECT dex_id FROM binder) ORDER BY id"):
            w.writerow([r["id"], r["name"]])
        fname = "fehlende-pokemon"
    else:
        w.writerow([tr(x) for x in ["Pokédex-Nr.", "Pokémon", "Karte", "Set", "Nummer", "Seltenheit", "Sprache", "Anzahl", "Preis (EUR)", "Im Binder"]])
        for r in q(f"""SELECT c.dex_id, {pname()} AS dex_name, c.name, c.set_name, c.local_id, c.rarity, c.lang, c.qty, c.price, c.price_holo, c.price_own, c.variant,
                             (b.card_id IS NOT NULL) AS in_binder
                      FROM cards c LEFT JOIN pokemon p ON p.id = c.dex_id LEFT JOIN binder b ON b.card_id = c.id
                      ORDER BY (c.dex_id IS NULL), c.dex_id, c.name"""):
            price = dec(r["price"])
            w.writerow([r["dex_id"] or "", r["dex_name"] or "", r["name"], r["set_name"], r["local_id"], tr(r["rarity"] or ""),
                        (r["lang"] or "de").upper(), r["qty"], price, tr("ja") if r["in_binder"] else tr("nein")])
        fname = "sammlung"
    data = ("\ufeff" + buf.getvalue()).encode("utf-8")  # BOM, damit Excel Umlaute richtig anzeigt
    return Response(data, mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={fname}-{datetime.date.today():%Y%m%d}.csv"})


def cm_link(r):
    """Cardmarket-Link: direkte Produktseite (bei Ball-Mustern Suche mit Musternamen, weil dort eigene Produkte moeglich sind)."""
    v = r.get("variant") or ""
    if r.get("cm_id") and v not in PATTERN_VARIANTS:
        return f"https://www.cardmarket.com/{ui_lang()}/Pokemon/Products?idProduct={r['cm_id']}" + ("&isFoil=Y" if v in FOIL_VARIANTS else "")
    words = f"{r['name']} {r['local_id']}" + (f" {PATTERN_SEARCH[v]}" if v in PATTERN_VARIANTS else "")
    return f"https://www.cardmarket.com/{ui_lang()}/Pokemon/Products/Search?searchString=" + urllib.parse.quote_plus(words)


def variant_suffix(v):
    if v in PATTERN_VARIANTS:
        return f" ({tr(VARIANT_LABELS[v])} Reverse Holo)"
    return f" ({tr(VARIANT_LABELS[v])})" if v in ("reverse", "holo") else ""


def dec(x):
    """Betrag fuer CSV-Dateien: Dezimalkomma (de, es) bzw. Dezimalpunkt (en)."""
    if x is None:
        return ""
    v = "%.2f" % x
    return v if ui_lang() == "en" else v.replace(".", ",")


@app.post("/api/variant")
def set_variant():
    d = request.json
    v = d.get("variant") or ""
    if v and v not in VARIANT_LABELS:
        return jsonify(ok=False, msg="Unbekannte Variante"), 400
    own = d.get("price_own")
    if own in ("", None):
        own = None
    else:
        try:
            own = round(float(str(own).replace(",", ".")), 2)
        except ValueError:
            return jsonify(ok=False, msg="Preis ungültig"), 400
    cond = d.get("cond") if "cond" in d else (q("SELECT cond FROM cards WHERE id=?", (d["card_id"],)) or [{"cond": None}])[0]["cond"]
    if cond and cond not in COND_LABELS:
        return jsonify(ok=False, msg="Unbekannter Zustand"), 400
    run("UPDATE cards SET variant=?, price_own=?, cond=? WHERE id=?", (v or None, own, cond or None, d["card_id"]))
    r = q("SELECT price, price_holo, price_own, variant FROM cards WHERE id=?", (d["card_id"],))
    return jsonify(ok=True, price=r[0]["price"] if r else None, src=r[0]["price_src"] if r else None)


def side_rows(spare=True):
    """Nebenstapel (inkl. ueberzaehliger Exemplare der Binder-Karten), teuerste zuerst."""
    rows = q(f"""SELECT * FROM (
                   SELECT c.id, c.name, c.set_name, c.local_id, c.rarity, c.lang, c.qty, c.image, c.price, c.price_holo, c.price_own,
                          c.variant, c.cond, c.cm_id, CASE WHEN b.card_id IS NULL THEN c.qty ELSE c.qty - 1 END AS spare
                   FROM cards c LEFT JOIN binder b ON b.card_id = c.id {"" if spare else "WHERE b.card_id IS NULL"})
                 WHERE spare > 0""")
    rows.sort(key=lambda r: (r["price"] is None, -(r["price"] or 0), r["name"]))
    return rows


# ================= Verkaufen auf Cardmarket (Assistent, Listen-Verwaltung, CSV fuer Massen-Werkzeuge)
LANG_EN = {"de": "German", "en": "English", "ja": "Japanese"}


def listed_qty(card_id):
    return q("SELECT COALESCE(SUM(qty), 0) AS n FROM listings WHERE card_id=? AND status='listed'", (card_id,))[0]["n"]


def available(card_id):
    """Wie viele Exemplare einer Karte noch verkauft werden koennen (Nebenstapel minus bereits gelistet)."""
    r = q("SELECT c.qty, (b.card_id IS NOT NULL) AS inb FROM cards c LEFT JOIN binder b ON b.card_id = c.id WHERE c.id=?", (card_id,))
    if not r:
        return 0
    return max(0, r[0]["qty"] - (1 if r[0]["inb"] else 0) - listed_qty(card_id))


@app.get("/api/listings")
def listings_get():
    status = request.args.get("status", "listed")
    rows = q("""SELECT l.*, c.name, c.set_name, c.local_id, c.image, c.lang, c.variant, c.cm_id, c.price AS price_now, c.price_holo, c.price_own
                FROM listings l LEFT JOIN cards c ON c.id = l.card_id WHERE l.status=? ORDER BY l.id DESC LIMIT 500""", (status,))
    for r in rows:
        r["name"] = r["name"] or r["card_id"]
        r["cm_url"] = cm_link({**r, "local_id": r["local_id"] or ""}) if r["local_id"] is not None else ""
    return jsonify(rows)


@app.post("/api/listings")
def listings_add():
    """Eingestellte Karten merken: items = [{card_id, qty, price, cond}]"""
    added, errors = 0, []
    for it in (request.json or {}).get("items", []):
        cid = it.get("card_id")
        try:
            n, price = int(it.get("qty", 1)), round(float(it.get("price")), 2)
        except (TypeError, ValueError):
            errors.append(f"{cid}: ungueltige Anzahl oder Preis")
            continue
        cond = it.get("cond") if it.get("cond") in COND_LABELS else "NM"
        if n < 1 or price < 0.02:
            errors.append(f"{cid}: Anzahl mindestens 1, Preis mindestens 0,02 €")
            continue
        if n > available(cid):
            errors.append(f"{cid}: nur noch {available(cid)} Exemplar(e) verfuegbar")
            continue
        run("INSERT INTO listings(card_id, qty, price, cond, status, ts) VALUES(?,?,?,?, 'listed', ?)",
            (cid, n, price, cond, datetime.datetime.now().strftime("%d.%m.%Y %H:%M")))
        meta_inc("listings")
        added += 1
    return jsonify(ok=not errors, added=added, errors=errors)


@app.post("/api/listings/act")
def listings_act():
    """action: sold (verkauft, Anzahl in der Sammlung sinkt) oder removed (auf Cardmarket zurueckgezogen)."""
    d = request.json or {}
    r = q("SELECT * FROM listings WHERE id=? AND status='listed'", (d.get("id"),))
    if not r:
        return jsonify(ok=False, msg="Eintrag nicht gefunden oder schon erledigt."), 404
    l, now = r[0], datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    if d.get("action") == "removed":
        run("UPDATE listings SET status='removed', done_ts=? WHERE id=?", (now, l["id"]))
        return jsonify(ok=True)
    if d.get("action") != "sold":
        return jsonify(ok=False, msg="Unbekannte Aktion."), 400
    n = l["qty"]
    try:
        if d.get("qty") not in (None, ""):
            n = max(1, min(l["qty"], int(d["qty"])))
    except (TypeError, ValueError):
        pass
    c = q("SELECT c.qty, (b.card_id IS NOT NULL) AS inb FROM cards c LEFT JOIN binder b ON b.card_id = c.id WHERE c.id=?", (l["card_id"],))
    if c:
        left = c[0]["qty"] - n
        if c[0]["inb"]:
            left = max(1, left)  # die Binder-Karte selbst wird nie verkauft
        if left <= 0:
            run("DELETE FROM cards WHERE id=?", (l["card_id"],))
        else:
            run("UPDATE cards SET qty=? WHERE id=?", (left, l["card_id"]))
    if n < l["qty"]:  # teilweise verkauft: Rest bleibt gelistet
        run("UPDATE listings SET qty=? WHERE id=?", (l["qty"] - n, l["id"]))
        run("INSERT INTO listings(card_id, qty, price, cond, status, ts, done_ts) VALUES(?,?,?,?, 'sold', ?, ?)", (l["card_id"], n, l["price"], l["cond"], l["ts"], now))
    else:
        run("UPDATE listings SET status='sold', done_ts=? WHERE id=?", (now, l["id"]))
    meta_inc("sold", n)
    meta_set("sold_total", round(float(meta_get("sold_total", 0) or 0) + n * l["price"], 2))
    return jsonify(ok=True, sold=n)


@app.post("/api/cm-export.csv")
def cm_export():
    """CSV fuer Massen-Werkzeuge (z. B. Cardmarket-Bulk-Listing per Browser-Erweiterung): items = [{card_id, qty, price, cond}]"""
    items = (request.json or {}).get("items", [])
    en_names = {}
    try:
        en_names = {x["id"]: x["name"] for x in get_sets("en")}
    except Exception:
        pass
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Name", "Expansion", "Expansion (Sammlung)", "Collector Number", "Language", "Condition", "Foil", "Reverse Holo", "Quantity", "Price", "Cardmarket ID", "Comment"])
    for it in items:
        r = q("SELECT * FROM cards WHERE id=?", (it.get("card_id"),))
        if not r:
            continue
        r = r[0]
        lang, tid = split_cid(r["id"])
        sid = tid.rsplit("-", 1)[0]
        v = r["variant"] or ""
        w.writerow([r["name"], en_names.get(sid, r["set_name"]) if lang != "ja" else r["set_name"], r["set_name"], r["local_id"], LANG_EN.get(lang, lang),
                    it.get("cond") or r.get("cond") or "NM", "true" if v in FOIL_VARIANTS else "false", "true" if v == "reverse" or v in PATTERN_VARIANTS else "false",
                    it.get("qty", 1), "%.2f" % float(it.get("price") or 0), r["cm_id"] or "", VARIANT_LABELS.get(v, "") if v in PATTERN_VARIANTS else ""])
    data = ("\ufeff" + buf.getvalue()).encode("utf-8")
    return Response(data, mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename=cardmarket-listing-{datetime.date.today():%Y%m%d}.csv"})


@app.get("/api/export-side.csv")
def export_side():
    """Nebenstapel als CSV zum Verkaufen: Spalte A Name, B Wert, C Cardmarket-Link (details=1 mit Zusatzspalten, spare=1 inkl. Doppelte der Binder-Karten)."""
    details, spare = request.args.get("details") == "1", request.args.get("spare", "1") == "1"
    rows = side_rows(spare)
    meta_inc("exports")
    fmt = dec
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow([tr(x) for x in ["Name", "Wert (EUR)", "Cardmarket-Link"] + (["Anzahl", "Summe (EUR)", "Set", "Nummer", "Seltenheit", "Sprache", "Variante", "Zustand", "Bild-Link"] if details else [])])
    for r in rows:
        v = r["variant"] or ""
        name = r["name"] + variant_suffix(v)
        if details:
            w.writerow([name, fmt(r["price"]), cm_link(r), r["spare"], fmt(r["price"] * r["spare"]) if r["price"] is not None else "",
                        r["set_name"], r["local_id"], tr(r["rarity"] or ""), (r["lang"] or "de").upper(), tr(VARIANT_LABELS.get(v, "Normal")),
                        r["cond"] or "NM", r["image"] or ""])
        else:
            for _ in range(r["spare"]):  # jedes Exemplar eine Zeile, damit die Summe der Spalte B stimmt
                w.writerow([name, fmt(r["price"]), cm_link(r)])
    data = ("\ufeff" + buf.getvalue()).encode("utf-8")
    return Response(data, mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename=nebenstapel-{datetime.date.today():%Y%m%d}.csv"})


_imgcache = {}


def fetch_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ninedex (self-hosted Pokemon card collection app)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def thumb_bytes(url, width=110):
    """Kleines JPEG-Vorschaubild einer Karte (fuer die Excel-Datei); None, wenn das Bild nicht ladbar ist."""
    if not url:
        return None
    u = re.sub(r"/(high|low)\.(png|webp)$", "/low.webp", url) if "assets.tcgdex.net" in url else url
    if u in _imgcache:
        return _imgcache[u]
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(fetch_bytes(u))).convert("RGB")
        im.thumbnail((width, int(width * 1.45)))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=82)
        _imgcache[u] = (buf.getvalue(), im.size)
    except Exception:
        _imgcache[u] = None
    return _imgcache[u]


@app.get("/api/export-side.xlsx")
def export_side_xlsx():
    """Nebenstapel als Excel-Datei MIT Kartenbildern (Verkaufsliste)."""
    try:
        from openpyxl import Workbook
        from openpyxl.drawing.image import Image as XLImage
        from openpyxl.styles import Alignment, Font, PatternFill
        import PIL  # noqa: F401
    except ImportError:
        return jsonify(ok=False, msg="Für die Excel-Datei fehlen die Pakete openpyxl und pillow. Dockerfile aktualisieren und neu bauen (siehe Anleitung)."), 501
    rows = side_rows(request.args.get("spare", "1") == "1")
    meta_inc("exports")
    urls = sorted({r["image"] for r in rows if r["image"]})
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(thumb_bytes, urls))
    wb = Workbook()
    ws = wb.active
    ws.title = tr("Verkaufsliste")[:31]
    head = [tr(x) for x in ["Bild", "Name", "Wert (EUR)", "Anzahl", "Summe (EUR)", "Zustand", "Set", "Nummer", "Seltenheit", "Sprache", "Variante", "Cardmarket"]]
    ws.append(head)
    for c in ws[1]:
        c.font, c.fill, c.alignment = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F6F85"), Alignment(vertical="center", horizontal="center")
    for i, w_ in enumerate([16, 38, 12, 9, 13, 10, 24, 9, 22, 9, 24, 14], start=1):
        ws.column_dimensions[chr(64 + i)].width = w_
    ws.row_dimensions[1].height = 24
    for n, r in enumerate(rows, start=2):
        v = r["variant"] or ""
        ws.append(["", r["name"] + variant_suffix(v), r["price"], r["spare"], f"=IF(C{n}=\"\",\"\",C{n}*D{n})", r["cond"] or "NM", r["set_name"],
                   r["local_id"], tr(r["rarity"] or ""), (r["lang"] or "de").upper(), tr(VARIANT_LABELS.get(v, "Normal")), "Cardmarket"])
        ws.row_dimensions[n].height = 100
        ws.cell(n, 12).hyperlink = cm_link(r)
        ws.cell(n, 12).font = Font(color="0563C1", underline="single")
        for col in (3, 5):
            ws.cell(n, col).number_format = '#,##0.00 "€"'
        for col in range(1, 13):
            ws.cell(n, col).alignment = Alignment(vertical="center", wrap_text=(col in (2, 7, 9)))
        t = thumb_bytes(r["image"])
        if t:
            img = XLImage(io.BytesIO(t[0]))
            img.width, img.height = t[1]
            ws.add_image(img, f"A{n}")
    last = len(rows) + 1
    ws.cell(last + 2, 2, "Summe").font = Font(bold=True)
    ws.cell(last + 2, 4, f"=SUM(D2:D{last})").font = Font(bold=True)
    ws.cell(last + 2, 5, f"=SUM(E2:E{last})").font = Font(bold=True)
    ws.cell(last + 2, 5).number_format = '#,##0.00 "€"'
    ws.freeze_panes = "A2"
    out = io.BytesIO()
    wb.save(out)
    return Response(out.getvalue(), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename=verkaufsliste-{datetime.date.today():%Y%m%d}.xlsx"})


@app.get("/verkauf")
def sell_page():
    """Verkaufsseite mit Kartenbildern zum Ansehen, Drucken oder Speichern als PDF (Browser: Drucken > Als PDF speichern)."""
    import html
    rows = side_rows(request.args.get("spare", "1") == "1")
    meta_inc("exports")
    total = sum((r["price"] or 0) * r["spare"] for r in rows)
    fmt = lambda x: ("–" if x is None else ("€%.2f" % x) if ui_lang() == "en" else ("%.2f €" % x).replace(".", ","))
    body = "".join(
        f"<tr><td class='im'>{'<img src=\"' + html.escape(r['image']) + '\" alt=\"\">' if r['image'] else ''}</td>"
        f"<td><b>{html.escape(r['name'] + variant_suffix(r['variant'] or ''))}</b><br><small>{html.escape(r['set_name'] or '')} {html.escape(str(r['local_id']))}"
        f" · {html.escape(r['rarity'] or '–')} · {(r['lang'] or 'de').upper()}</small></td>"
        f"<td>{r['cond'] or 'NM'}</td><td class='n'>{r['spare']}×</td><td class='n'>{fmt(r['price'])}</td>"
        f"<td class='n'>{fmt(r['price'] * r['spare'] if r['price'] is not None else None)}</td>"
        f"<td class='no'><a href='{html.escape(cm_link(r))}' target='_blank' rel='noopener'>Cardmarket</a></td></tr>" for r in rows)
    page = f"""<!doctype html><html lang="de"><head><meta charset="utf-8">{i18n_head()}<title>Verkaufsliste</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{{font:15px/1.35 system-ui,sans-serif;margin:24px;color:#1f2433}}h1{{margin:0 0 4px}}
table{{border-collapse:collapse;width:100%;margin-top:14px}}th,td{{border-bottom:1px solid #d8dde6;padding:6px 8px;text-align:left;vertical-align:middle}}
th{{background:#1f6f85;color:#fff}}td.im{{width:74px}}td.im img{{width:64px;border-radius:4px;display:block}}td.n{{text-align:right;white-space:nowrap}}
small{{color:#5b6477}}tfoot td{{font-weight:700;border-top:2px solid #1f2433}}button{{padding:8px 14px;font-size:15px;cursor:pointer}}
@media print{{.no,button{{display:none}}body{{margin:8mm}}tr{{break-inside:avoid}}}}</style></head><body>
<h1>Verkaufsliste</h1><div>Stand {datetime.date.today():%d.%m.%Y} · {sum(r['spare'] for r in rows)} Karten · Wert ca. <b>{fmt(total)}</b>
 <button onclick="window.print()">Drucken / Als PDF speichern</button></div>
<table><thead><tr><th></th><th>Karte</th><th>Zustand</th><th>Anzahl</th><th>Einzelpreis</th><th>Summe</th><th class="no"></th></tr></thead>
<tbody>{body or '<tr><td colspan=7>Der Nebenstapel ist leer.</td></tr>'}</tbody>
<tfoot><tr><td></td><td>Summe</td><td></td><td class="n">{sum(r['spare'] for r in rows)}×</td><td></td><td class="n">{fmt(total)}</td><td class="no"></td></tr></tfoot></table>
<p><small>Preise: Cardmarket-Trend (Richtwerte). Erstellt mit Ninedex.</small></p></body></html>"""
    return Response(page, mimetype="text/html")


@app.get("/api/session")
def session_get():
    return jsonify(session_summary())


@app.post("/api/session")
def session_post():
    """Pack-Session: start = neue Session (Protokoll wird geleert), stop = beenden und Auswertung zurueckgeben."""
    action = (request.json or {}).get("action")
    if action == "start":
        run("DELETE FROM session_log")
        meta_set("session_start", datetime.datetime.now().strftime("%d.%m.%Y %H:%M"))
        return jsonify(session_summary())
    if action == "stop":
        summ = session_summary()
        if summ["active"]:
            if summ["cards"] >= 1:
                meta_inc("sessions")
            if summ["cards"] >= 36:
                meta_inc("big_sessions")
            meta_set("session_start", None)
            summ["active"] = False
        return jsonify(summ)
    return jsonify(ok=False), 400


@app.get("/api/backup")
def backup_download():
    """Konsistente Kopie der Datenbank zum Herunterladen."""
    fd, tmp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        src, dst = sqlite3.connect(DB), sqlite3.connect(tmp)
        src.backup(dst)
        dst.close()
        src.close()
        with open(tmp, "rb") as f:
            data = f.read()
    finally:
        os.remove(tmp)
    return Response(data, mimetype="application/octet-stream",
                    headers={"Content-Disposition": f"attachment; filename=pokedex-backup-{datetime.date.today():%Y%m%d}.db"})


@app.get("/api/dexinfo")
def dexinfo():
    dex_id = int(request.args["id"])
    r = q(f"""SELECT p.id, {pname()} AS name, (SELECT COUNT(*) FROM favorites f WHERE f.dex_id = p.id) AS fav
              FROM pokemon p WHERE p.id=?""", (dex_id,))
    if not r:
        return jsonify({})
    r[0]["genus"], r[0]["text"], r[0]["game"] = dex_text(dex_id)
    return jsonify(r[0])


@app.post("/api/favorite")
def favorite():
    d = request.json
    if d.get("on"):
        run("INSERT OR IGNORE INTO favorites VALUES(?)", (d["dex_id"],))
    else:
        run("DELETE FROM favorites WHERE dex_id=?", (d["dex_id"],))
    return jsonify(ok=True)


@app.get("/api/cards")
def cards():
    base = f"""SELECT c.*, {pname()} AS dex_name, (b.card_id IS NOT NULL) AS in_binder,
                     CASE WHEN b.card_id IS NULL THEN c.qty ELSE c.qty - 1 END AS spare
              FROM cards c LEFT JOIN pokemon p ON p.id = c.dex_id
              LEFT JOIN binder b ON b.card_id = c.id """
    if request.args.get("side"):  # Nebenstapel = Karten ausserhalb des Binders plus ueberzaehlige Exemplare der Binder-Karten
        rows = q(base.replace("AS spare", "AS spare, (SELECT COALESCE(SUM(l.qty), 0) FROM listings l WHERE l.card_id = c.id AND l.status = 'listed') AS listed")
                 + "WHERE (b.card_id IS NULL OR c.qty > 1) ORDER BY c.dex_id, c.name")
        for r in rows:
            r["cm_url"] = cm_link(r)
        return jsonify(rows)
    return jsonify(q(base + "WHERE c.dex_id=? ORDER BY in_binder DESC, c.name", (request.args["dex_id"],)))


@app.get("/api/sets")
def sets():
    lang = request.args.get("lang", "de")
    lang = lang if lang in LANGS else "de"
    names = ja_set_names() if lang == "ja" else {}
    out = []
    try:
        sl = get_sets(lang)
    except Exception:  # Kartendatenbank nicht erreichbar: leere Liste statt Fehlerseite
        return jsonify([])
    for s in sl:
        c = s.get("cardCount") or {}
        out.append({"id": s["id"], "name": s["name"], "name_en": names.get(norm_code(s["id"])),
                    "official": c.get("official"), "total": c.get("total")})
    return jsonify(out)


@app.get("/api/dens")
def dens():
    """Alle vorkommenden Set-Groessen (Zahl hinter dem '/'), fuer die Nummernerkennung."""
    out = set()
    for lang in LANGS:
        try:
            sl = get_sets(lang)
        except Exception:  # Kartendatenbank nicht erreichbar: diese Sprache auslassen
            continue
        for s in sl:
            o = (s.get("cardCount") or {}).get("official")
            if o and o >= 20:
                out.add(o)
    return jsonify(sorted(out, reverse=True))


def detect_cards(num, den, set_id="", lang="auto", pref=""):
    """Findet Karte(n) zu Nummer + Nenner (Set-Groesse) in allen Sprachen. Mit set_id nur in diesem Set."""
    langs = [lang] if lang in LANGS else list(LANGS)
    langs.sort(key=lambda l: l != pref)  # erkannte Sprache zuerst
    cands = []
    for l in langs:
        for st in get_sets(l):
            official = (st.get("cardCount") or {}).get("official")
            if (set_id and st["id"] == set_id) or (not set_id and den and official == den):
                cands.append((l, st["id"]))
    cands = cands[:18]
    if den:
        cands += classic_cands(num, den, langs, set_id)
    return slot_cards(cands, num)


def classic_cands(num, den, langs, set_id=""):
    """Classic-Collection-Karten tragen die Originalnummer (z. B. Glurak 4/102). Passende Karten aus solchen Sets mit anbieten."""
    out = []
    try:
        classic = [x["id"] for x in get_sets("en") if "classic collection" in x.get("name", "").lower()]
    except Exception:
        return out
    n = str(num).split("/")[0].strip().lstrip("0").lower()
    for sid in classic:
        if set_id and sid != set_id:
            continue
        cat, g = tp_group_for("en", sid)
        if not g:
            continue
        names = {card_key(nm) for pn, pd, nm, _, _ in tp_products(cat, g[0]) if pn == n and pd == den}
        if not names:
            continue
        locals_ = [c[3] for c in en_cards(sid) if card_key(c[1]) in names]
        for l in langs:
            if l == "ja" or not set_info(l, sid):
                continue
            out += [(l, sid, ln) for ln in locals_]
    return out[:6]


def slot_cards(cands, num):
    def one(c):
        try:
            card = find_card(c[0], c[1], c[2] if len(c) > 2 else num)
        except Exception:
            return None
        if not card:
            return None
        return slot_info(card_row(card, c[0]))

    with ThreadPoolExecutor(8) as ex:
        return [r for r in ex.map(one, cands) if r]


@app.get("/api/detect")
def detect():
    """Findet Karte(n) zu Nummer + Nenner (Set-Groesse) in allen Sprachen. Mit set=... nur in diesem Set."""
    num = request.args["num"].split("/")[0].strip()
    try:
        den = int(request.args.get("den") or 0)
    except ValueError:
        den = 0
    return jsonify(detect_cards(num, den, request.args.get("set", "").strip(), request.args.get("lang", "auto"), request.args.get("pref", "")))


# ================= KI-Hilfe fuer die Kamera (Ollama lokal oder Google Gemini)
AI_PROMPT = """You are an expert for the Pokemon Trading Card Game. The image shows one Pokemon card (it may be in a sleeve, tilted, or with glare). Read the printed text as exactly as possible and answer ONLY with one JSON object, no other text:
{"is_card": true or false, "name": "card name as printed, without HP and without the evolution stage", "number": "collector number as printed, only the part before the slash, e.g. 057", "total": "the number after the slash, digits only, or null", "set_code": "short set code printed near the number (e.g. PAL, SVI, M3) or null", "language": "de" or "en" or "ja" or "other", "hp": integer or null, "regulation_mark": "single letter or null"}
The collector number is printed small at the bottom left or bottom right of the card in the form 057/193. Never guess: use null for anything you cannot read."""


class AIError(Exception):
    pass


def ai_config():
    env = os.environ.get
    return {"provider": meta_get("ai_provider", env("AI_PROVIDER", "")), "url": meta_get("ai_url", env("OLLAMA_URL", "http://localhost:11434")),
            "ollama_model": meta_get("ai_model_ollama", env("OLLAMA_MODEL", "qwen3-vl:8b")),
            "gemini_model": meta_get("ai_model_gemini", env("GEMINI_MODEL", "gemini-flash-latest")), "key": meta_get("ai_key", env("GEMINI_API_KEY", ""))}


def ai_ok(c):
    return (c["provider"] == "ollama" and bool(c["url"])) or (c["provider"] == "gemini" and bool(c["key"]))


def ai_request(url, payload=None, headers=None, timeout=60, provider=""):
    """HTTP-Aufruf an den KI-Dienst; Fehler werden in verstaendliche Meldungen uebersetzt."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET",
                                 headers={"Content-Type": "application/json", "User-Agent": "ninedex", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise AIError("Das kostenlose Kontingent ist gerade aufgebraucht (Anfragen pro Minute oder Tag). Kurz warten oder die Nummer eintippen.")
        if provider == "gemini" and e.code in (400, 401, 403):
            raise AIError("Der API-Schluessel wurde abgelehnt oder ist ungueltig. Pruefe ihn in den KI-Einstellungen.")
        if e.code == 404:
            raise AIError("Modell nicht gefunden. Pruefe den Modellnamen in den KI-Einstellungen" + (" (mit 'ollama pull' installieren)." if provider == "ollama" else "."))
        raise AIError(f"Der KI-Dienst meldet Fehler {e.code}.")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise AIError("KI-Dienst nicht erreichbar. " + ("Laeuft Ollama auf dem PC, ist die Adresse richtig und der Port 11434 im Netzwerk freigegeben?" if provider == "ollama"
                                                          else "Internetverbindung des Servers pruefen.") + f" ({getattr(e, 'reason', e)})")
    except ValueError:
        raise AIError("Die Antwort des KI-Dienstes war nicht lesbar.")


def parse_ai_json(text):
    m = re.search(r"\{.*\}", (text or "").strip(), re.S)
    if not m:
        raise AIError("Die KI-Antwort war nicht lesbar.")
    try:
        d = json.loads(m.group(0))
    except ValueError:
        raise AIError("Die KI-Antwort war nicht lesbar.")
    g = lambda k: str(d.get(k)).strip() if d.get(k) not in (None, "", "null") else ""
    raw_num, tot = g("number"), re.sub(r"\D", "", g("total"))
    if "/" in raw_num and not tot:
        tot = re.sub(r"\D", "", raw_num.split("/", 1)[1])
    num = re.sub(r"[^0-9A-Za-z-]", "", raw_num.split("/")[0])
    lang = g("language").lower()[:2]
    return {"is_card": d.get("is_card", True) not in (False, "false", 0), "name": g("name"), "number": num, "total": int(tot) if tot else 0,
            "set_code": g("set_code"), "language": lang if lang in LANGS else "", "regulation_mark": g("regulation_mark")}


def ai_vision(prompt, images, ollama_timeout=180):
    """Fragt das eingestellte Bildmodell (Ollama oder Gemini) mit einem Text und einem oder mehreren Bildern (base64-JPEG); Rueckgabe: Antworttext."""
    c = ai_config()
    if c["provider"] == "ollama":
        r = ai_request(c["url"].rstrip("/") + "/api/chat", {"model": c["ollama_model"], "stream": False, "format": "json", "options": {"temperature": 0},
                       "messages": [{"role": "user", "content": prompt, "images": images}]}, timeout=ollama_timeout, provider="ollama")
        return (r.get("message") or {}).get("content", "")
    if c["provider"] == "gemini" and c["key"]:
        parts = [{"text": prompt}] + [{"inline_data": {"mime_type": "image/jpeg", "data": im}} for im in images]
        r = ai_request(f"https://generativelanguage.googleapis.com/v1beta/models/{c['gemini_model']}:generateContent",
                       {"contents": [{"parts": parts}], "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}},
                       headers={"x-goog-api-key": c["key"]}, timeout=120, provider="gemini")
        ps = ((r.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        return "".join(p.get("text", "") for p in ps)
    raise AIError("Die KI-Erkennung ist nicht eingerichtet.")


def ai_read_card(b64):
    return parse_ai_json(ai_vision(AI_PROMPT, [b64]))


def detect_by_name(name, num, pref=""):
    """Karten ueber den Namen suchen und nach der Nummer filtern (wenn die Set-Groesse nicht lesbar war)."""
    langs = list(LANGS)
    langs.sort(key=lambda l: l != pref)
    cands = []
    for l in langs:
        try:
            res = fetch(f"{TCG}/{l}/cards?name={urllib.parse.quote(name)}")
        except Exception:
            continue
        for c in res if isinstance(res, list) else []:
            if str(c.get("localId", "")).lstrip("0").lower() == num.lstrip("0").lower():
                cands.append((l, c["id"].rsplit("-", 1)[0]))
    return slot_cards(cands[:12], num)


def ai_resolve(info, lang="auto"):
    num, den, name = info["number"], info["total"], info["name"]
    cards = detect_cards(num, den, "", lang, info["language"]) if num and den else []
    if not cards and num and name:
        cards = detect_by_name(name, num, info["language"])
    if name and cards:  # passende Namen zuerst, unpassende nur behalten, wenn nichts passt
        sim = lambda c: difflib.SequenceMatcher(None, name.lower(), (c.get("name") or "").lower()).ratio()
        cards.sort(key=lambda c: -sim(c))
        cards = [c for c in cards if sim(c) >= 0.5] or cards
    return cards


@app.post("/api/ai-scan")
def ai_scan():
    d = request.json or {}
    img = d.get("image", "")
    if "," in img:
        img = img.split(",", 1)[1]
    if not img or len(img) > 8_000_000:
        return jsonify(ok=False, msg="Kein brauchbares Bild erhalten."), 400
    try:
        info = ai_read_card(img)
        cards = ai_resolve(info, d.get("lang", "auto")) if info["is_card"] and info["number"] else []
    except AIError as e:
        return jsonify(ok=False, msg=str(e)), 502
    meta_inc("ai_scans")
    return jsonify(ok=True, info=info, cards=cards)


def ai_public():
    c = ai_config()
    return {"provider": c["provider"], "url": c["url"], "ollama_model": c["ollama_model"], "gemini_model": c["gemini_model"],
            "has_key": bool(c["key"]), "configured": ai_ok(c)}


# ================= Grading-Check (Vorab-Einschaetzung, PSA-Massstab)
PSA_NAMES = {10: "Gem Mint", 9: "Mint", 8: "NM-MT", 7: "NM", 6: "EX-MT", 5: "EX", 4: "VG-EX", 3: "VG", 2: "Good", 1: "Poor"}
# hoechste moegliche Note je schlechtestem Zentrierwert (in Prozent der breiteren Seite), nach den veroeffentlichten PSA-Grenzen
FRONT_CAPS = [(55, 10), (60, 9), (65, 8), (70, 7), (80, 6), (85, 5), (90, 3)]
BACK_CAPS = [(75, 10), (90, 9)]
GRADE_PROMPT = """You are a strict, experienced trading card grader (PSA style) and you examine photos of one Pokemon trading card. The images are given in this order: {labels}. "front" and "back" are full views; "fTL, fTR, fBL, fBR" are close-ups of the front corners (top-left, top-right, bottom-left, bottom-right), "bTL, bTR, bBL, bBR" the same for the back.
Judge ONLY what is visible. Rate each category from 1 to 10 in half-point steps:
- corners: whitening, fraying, dents or rounding on all corners
- edges: whitening or chipping along the edges (visible at the borders in the close-ups)
- surface: scratches, scuffs, dents, creases, stains, holo scratches, indentations, on front and back
- print: print defects such as print lines, ink spots, misregistration or rough cut (if visible)
Scale: 10 flawless; 9 only microscopic flaws; 8 minor flaws (slight whitening on one or two corners or edges, a faint scratch); 7 light wear; 6 clearly visible wear; 5 or lower obvious damage.
Be conservative. If glare, blur, sleeves, toploaders or low resolution prevent a reliable judgment, say so under "photo" and never give a score above 9.
Answer ONLY with this JSON object:
{"photo": {"usable": true or false, "sharp": true or false, "glare": "none" or "some" or "heavy", "in_sleeve": true or false, "notes": "short"},
 "corners": {"score": number, "defects": ["short descriptions"]}, "edges": {"score": number, "defects": []}, "surface": {"score": number, "defects": []}, "print": {"score": number, "defects": []},
 "summary": "one or two sentences"}"""


def center_worst(l, r, t, b):
    """Schlechtester Zentrierwert in Prozent der breiteren Randseite (50 = perfekt)."""
    pct = lambda a, c: (max(a, c) / (a + c) * 100) if (a + c) > 0 else 50.0
    return round(max(pct(l, r), pct(t, b)), 1)


def cap_from(worst, table, floor):
    for limit, grade in table:
        if worst <= limit:
            return grade
    return floor


def grade_estimate(center, sub, photo=None):
    """Schaetzt die PSA-Note. center: {"front": Prozentwert|None, "back": ...}, sub: Teilnoten 1-10 (corners, edges, surface, print) oder leer."""
    photo = photo or {}
    cf = cap_from(center["front"], FRONT_CAPS, 1) if center.get("front") else 10
    cb = cap_from(center["back"], BACK_CAPS, 5) if center.get("back") else 10
    vals, labels = [], {}
    surf = sub.get("surface")
    if surf is not None and sub.get("print") is not None:
        surf = min(surf, sub["print"] + 0.5)
    for key, v, name in (("corners", sub.get("corners"), "Ecken"), ("edges", sub.get("edges"), "Kanten"), ("surface", surf, "Oberfläche")):
        if v is not None:
            vals.append(v)
            labels[name] = v
    if vals:
        core_min, core_mean = min(vals), sum(vals) / len(vals)
        g = int(math.floor(core_min + 0.35 * (core_mean - core_min) + 0.5))
        if core_min < 9.5:
            g = min(g, 9)
        g = max(1, min(10, g))
    else:
        g = 10
    base = g
    g = min(g, cf, cb)
    top = min(cf, cb, 10)
    if not vals:  # nur Zentrierung bekannt: keine Note behaupten, nur die Obergrenze nennen
        return {"best": None, "low": None, "high": top, "name": "", "limiting": "nur Zentrierung ausgewertet", "conf": "niedrig", "cap_front": cf, "cap_back": cb,
                "centering_borderline": False, "subs": {}, "measured": False}
    if g < base:
        limiting = "Zentrierung vorne" if cf <= cb else "Zentrierung hinten"
    elif labels:
        limiting = min(labels, key=labels.get) if min(labels.values()) < 9.5 else "kein klarer Schwachpunkt"
    else:
        limiting = "nur Zentrierung ausgewertet"
    clean = bool(photo.get("usable", True)) and bool(photo.get("sharp", True)) and photo.get("glare", "none") == "none" and not photo.get("in_sleeve")
    conf = "hoch" if clean else ("mittel" if photo.get("usable", True) else "niedrig")
    if conf != "hoch":
        g = min(g, 9)  # eine 10 trauen wir uns nur bei sauberen, scharfen Fotos ohne Huelle und Spiegelung zu
    down = 1 if conf == "hoch" else 2 if conf == "mittel" else 3
    near = False  # Messung knapp ueber einer Grenze: kleine Messfehler koennen die Note aendern
    for key, table in (("front", FRONT_CAPS), ("back", BACK_CAPS)):
        w = center.get(key)
        if w and any(0 < w - lim <= 1.5 for lim, _ in table):
            near = True
    return {"best": g, "low": max(1, g - down), "high": min(g + 1, top) if g < top else g, "name": PSA_NAMES[g], "limiting": limiting, "conf": conf,
            "cap_front": cf, "cap_back": cb, "centering_borderline": near, "subs": {k: v for k, v in labels.items()}, "measured": bool(vals)}


def parse_grade_json(text):
    m = re.search(r"\{.*\}", (text or "").strip(), re.S)
    if not m:
        raise AIError("Die KI-Antwort war nicht lesbar.")
    try:
        d = json.loads(m.group(0))
    except ValueError:
        raise AIError("Die KI-Antwort war nicht lesbar.")

    def part(k):
        v = d.get(k) if isinstance(d.get(k), dict) else {}
        try:
            sc = float(v.get("score"))
            sc = max(1.0, min(10.0, round(sc * 2) / 2))
        except (TypeError, ValueError):
            sc = None
        return {"score": sc, "defects": [str(x)[:140] for x in (v.get("defects") or []) if x][:6]}

    ph = d.get("photo") if isinstance(d.get("photo"), dict) else {}
    photo = {"usable": ph.get("usable", True) not in (False, "false"), "sharp": ph.get("sharp", True) not in (False, "false"),
             "glare": ph.get("glare") if ph.get("glare") in ("none", "some", "heavy") else "none", "in_sleeve": ph.get("in_sleeve") in (True, "true"), "notes": str(ph.get("notes") or "")[:200]}
    if photo["glare"] == "heavy":
        photo["usable"] = False
    return {"photo": photo, "corners": part("corners"), "edges": part("edges"), "surface": part("surface"), "print": part("print"), "summary": str(d.get("summary") or "")[:400]}


def centering_info(c):
    """Aus den normierten Randbreiten (l, r, t, b) Verhaeltnisse berechnen."""
    if not c:
        return None
    try:
        l, r, t, b = (max(0.0, float(c[k])) for k in ("l", "r", "t", "b"))
    except (KeyError, TypeError, ValueError):
        return None
    if l + r <= 0 or t + b <= 0:
        return None
    return {"lr": [round(l / (l + r) * 100, 1), round(r / (l + r) * 100, 1)], "tb": [round(t / (t + b) * 100, 1), round(b / (t + b) * 100, 1)], "worst": center_worst(l, r, t, b)}


@app.post("/api/grade-ai")
def grade_ai():
    d = request.json or {}
    imgs = [i for i in d.get("images", []) if isinstance(i, dict) and i.get("data")][:12]
    if sum(len(i["data"]) for i in imgs) > 30_000_000:
        return jsonify(ok=False, msg="Die Bilder sind zu gross."), 400
    cen = {k: centering_info((d.get("centering") or {}).get(k)) for k in ("front", "back")}
    center = {k: (v["worst"] if v else None) for k, v in cen.items()}
    ai, msg = None, ""
    if imgs and ai_ok(ai_config()):
        try:
            prompt = GRADE_PROMPT.replace("{labels}", ", ".join(i.get("label", f"image{n + 1}") for n, i in enumerate(imgs)))
            prompt += "\nWrite all free-text values (notes, defects, summary) in " + {"de": "German", "en": "English", "es": "Spanish"}[ui_lang()] + "."
            ai = parse_grade_json(ai_vision(prompt, [i["data"].split(",", 1)[-1] for i in imgs], ollama_timeout=420))
        except AIError as e:
            msg = str(e)
    elif imgs:
        msg = "Die KI-Hilfe ist nicht eingerichtet, deshalb wurde nur die Zentrierung ausgewertet."
    sub = {k: ai[k]["score"] for k in ("corners", "edges", "surface", "print")} if ai else {}
    est = grade_estimate(center, sub, ai["photo"] if ai else None)
    if ai:
        meta_inc("grade_checks")
    return jsonify(ok=True, ai=ai, centering=cen, estimate=est, msg=msg)


@app.post("/api/grade-calc")
def grade_calc():
    """Note neu berechnen, wenn du die Teilnoten selbst anpasst (ohne KI-Aufruf)."""
    d = request.json or {}
    cen = {k: centering_info((d.get("centering") or {}).get(k)) for k in ("front", "back")}
    sub = {}
    for k in ("corners", "edges", "surface", "print"):
        try:
            v = (d.get("subs") or {}).get(k)
            if v not in (None, ""):
                sub[k] = max(1.0, min(10.0, float(v)))
        except (TypeError, ValueError):
            pass
    est = grade_estimate({k: (v["worst"] if v else None) for k, v in cen.items()}, sub, d.get("photo"))
    return jsonify(ok=True, centering=cen, estimate=est)


@app.post("/api/grades")
def grades_save():
    d = request.json or {}
    e = d.get("estimate") or {}
    run("INSERT INTO grades(ts, card_id, name, set_name, image, best, low, high, limiting, conf, cen_f, cen_b, subs, notes, raw_price) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (datetime.datetime.now().strftime("%d.%m.%Y %H:%M"), d.get("card_id"), d.get("name") or "Unbekannte Karte", d.get("set_name"), d.get("image"),
         e.get("best"), e.get("low"), e.get("high"), e.get("limiting"), e.get("conf"), d.get("cen_f"), d.get("cen_b"), json.dumps(e.get("subs") or {}), (d.get("notes") or "")[:400], d.get("raw_price")))
    meta_inc("grades_saved")
    return jsonify(ok=True)


@app.get("/api/grades")
def grades_list():
    rows = q("SELECT * FROM grades ORDER BY best DESC, id DESC")
    for r in rows:
        r["subs"] = json.loads(r["subs"] or "{}")
    return jsonify(rows)


@app.post("/api/grades/delete")
def grades_delete():
    run("DELETE FROM grades WHERE id=?", ((request.json or {}).get("id"),))
    return jsonify(ok=True)


@app.get("/api/ai/config")
def ai_config_get():
    return jsonify(ai_public())


@app.post("/api/ai/config")
def ai_config_save():
    d = request.json or {}
    if d.get("provider") in ("", "ollama", "gemini"):
        meta_set("ai_provider", d["provider"])
    for k, mk in (("url", "ai_url"), ("ollama_model", "ai_model_ollama"), ("gemini_model", "ai_model_gemini")):
        if str(d.get(k, "")).strip():
            meta_set(mk, str(d[k]).strip())
    if d.get("clear_key"):
        meta_set("ai_key", None)
    elif str(d.get("key", "")).strip():
        meta_set("ai_key", str(d["key"]).strip())
    return jsonify(ai_public())


@app.post("/api/ai/test")
def ai_test():
    """Verbindung pruefen (mit den im Formular stehenden, noch nicht gespeicherten Werten)."""
    d = request.json or {}
    c = ai_config()
    c.update({k: str(d[k]).strip() for k in ("provider", "url", "ollama_model", "gemini_model", "key") if str(d.get(k, "")).strip()})
    try:
        if c["provider"] == "ollama":
            names = [m["name"] for m in ai_request(c["url"].rstrip("/") + "/api/tags", timeout=10, provider="ollama").get("models", [])]
            have = c["ollama_model"] in names or c["ollama_model"] + ":latest" in names
            return jsonify(ok=have, models=names, msg="Verbunden, das Modell ist installiert." if have else
                           f"Verbunden, aber das Modell fehlt. Auf dem PC ausfuehren: ollama pull {c['ollama_model']}")
        if c["provider"] == "gemini":
            if not c["key"]:
                return jsonify(ok=False, msg="Bitte den API-Schluessel eintragen.")
            ms = ai_request("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200", headers={"x-goog-api-key": c["key"]}, timeout=15, provider="gemini").get("models", [])
            names = [m["name"].split("/", 1)[-1] for m in ms if "generateContent" in m.get("supportedGenerationMethods", [])]
            have = c["gemini_model"] in names
            flash = [n for n in names if "flash" in n][:8]
            return jsonify(ok=have, models=flash, msg="Verbunden, das Modell ist verfuegbar." if have else
                           "Verbunden, aber dieses Modell gibt es nicht. Moegliche Flash-Modelle: " + ", ".join(flash))
        return jsonify(ok=False, msg="Bitte einen Anbieter waehlen.")
    except AIError as e:
        return jsonify(ok=False, msg=str(e))


@app.post("/api/add")
def add():
    d = request.json
    lang = d.get("lang", "de")
    lang = lang if lang in LANGS else "de"
    try:
        card = find_card(lang, d["set"].strip(), d["number"].split("/")[0].strip())
    except Exception as e:
        return jsonify(status="error", msg=f"Kartendatenbank nicht erreichbar: {e}"), 502
    if not card:
        return jsonify(status="notfound"), 404

    row = card_row(card, lang)
    dex_id = row["dex_id"]
    had_dex = bool(dex_id) and bool(q("SELECT 1 FROM cards WHERE dex_id=? LIMIT 1", (dex_id,)))
    existed = bool(q("SELECT 1 FROM cards WHERE id=?", (row["id"],)))
    if existed:
        run("UPDATE cards SET qty = qty + 1, price = COALESCE(?, price), price_holo = COALESCE(?, price_holo), cm_id = COALESCE(?, cm_id) WHERE id=?",
            (row["price"], row["price_holo"], row["cm_id"], row["id"]))
    else:
        run(
            "INSERT INTO cards(id,name,set_name,local_id,rarity,image,dex_id,lang,price,price_at,category,price_holo,cm_id,px_at,variant,added) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (row["id"], row["name"], row["set_name"], row["local_id"], row["rarity"], row["image"],
             dex_id, lang, row["price"], datetime.date.today().isoformat(), row["category"], row["price_holo"], row["cm_id"],
             datetime.date.today().isoformat(), d.get("variant") if d.get("variant") in VARIANT_LABELS else None,
             datetime.date.today().isoformat()),
        )
    mode = d.get("mode", "auto")
    run("DELETE FROM wishlist WHERE card_id=?", (row["id"],))  # Karte ist jetzt da, also nicht mehr gesucht
    log_session(row["id"], 1, newc=not existed, newp=(not existed) and dex_id is not None and not had_dex)
    if d.get("src") == "scan":
        meta_inc("scans")
    if dex_id is None:
        return jsonify(status="nodex", card=row)
    if mode == "quick":  # Schnell-Eintrag (+1): neue Karte kommt in den Binder, wenn der Platz frei ist, sonst in den Nebenstapel, ohne Rueckfrage
        if not existed and not q("SELECT 1 FROM binder WHERE dex_id=?", (dex_id,)):
            run("INSERT OR IGNORE INTO binder VALUES(?,?)", (dex_id, row["id"]))
            return jsonify(status="placed", card=row, dex_name=dex_name(dex_id))
        return jsonify(status="side", card=row)
    if mode == "side":  # nur in die Sammlung, Binder bleibt unveraendert
        return jsonify(status="side", card=row)
    if mode == "binder":  # immer in den Binder, ersetzt eine vorhandene Karte
        run("INSERT OR REPLACE INTO binder VALUES(?,?)", (dex_id, row["id"]))
        return jsonify(status="placed", card=row, dex_name=dex_name(dex_id))

    name = dex_name(dex_id)
    cur = q("SELECT c.* FROM binder b JOIN cards c ON c.id=b.card_id WHERE b.dex_id=?", (dex_id,))
    if not cur:
        run("INSERT OR IGNORE INTO binder VALUES(?,?)", (dex_id, row["id"]))  # falls jemand gleichzeitig denselben Platz belegt
        cur = q("SELECT c.* FROM binder b JOIN cards c ON c.id=b.card_id WHERE b.dex_id=?", (dex_id,))
        if cur and cur[0]["id"] == row["id"]:
            return jsonify(status="placed", card=row, dex_name=name)
    if cur[0]["id"] == row["id"]:
        return jsonify(status="same", card=row, dex_name=name, qty=q("SELECT qty FROM cards WHERE id=?", (row["id"],))[0]["qty"])
    return jsonify(status="conflict", card=row, current=cur[0], dex_id=dex_id, dex_name=name)


@app.get("/api/next")
def next_card():
    """Naechste Karte im selben Set (fuer den Set-Durchlauf). skip=1 ueberspringt Trainer und Energie."""
    set_id, lang, cur = request.args["set"], request.args.get("lang", "de"), request.args["after"]
    skip, skipped = request.args.get("skip") == "1", 0
    for _ in range(60):
        cur = inc_local(cur)
        if cur is None:
            break
        try:
            card = find_card(lang, set_id, cur)
        except Exception as e:
            return jsonify(status="error", msg=f"Kartendatenbank nicht erreichbar: {e}"), 502
        if not card:
            break
        row = card_row(card, lang)
        if skip and row["category"] != "Pokemon":
            skipped += 1
            cur = str(card["localId"])
            continue
        return jsonify(status="ok", card=slot_info(row), skipped=skipped)
    return jsonify(status="end", skipped=skipped)


@app.get("/api/dexcards")
def dexcards():
    lang = request.args.get("lang", "de")
    lang = lang if lang in LANGS else "de"
    try:
        return jsonify(dex_payload(int(request.args["dex_id"]), lang))
    except Exception as e:
        return jsonify(status="error", msg=f"Kartenliste nicht abrufbar: {e}"), 502


@app.get("/api/nextdex")
def nextdex():
    """Naechstes Pokemon im Pokedex (nach 'after') samt allen Karten. skip=1 ueberspringt Pokemon mit Binder-Karte."""
    after, skip = int(request.args.get("after", 0)), request.args.get("skip") == "1"
    lang = request.args.get("lang", "de")
    lang = lang if lang in LANGS else "de"
    top = q("SELECT MAX(id) AS m FROM pokemon")[0]["m"] or 0
    in_binder = {r["dex_id"] for r in q("SELECT dex_id FROM binder")}
    skipped = calls = 0
    for dex_id in range(after + 1, top + 1):
        if skip and dex_id in in_binder:
            skipped += 1
            continue
        if calls >= 40:  # nicht zu lange am Stueck suchen, der Browser fragt weiter
            return jsonify(status="continue", after=dex_id - 1, skipped=skipped)
        calls += 1
        try:
            if not dex_brief("en", dex_id):  # Pokemon ohne Karte ueberspringen
                skipped += 1
                continue
            payload = dex_payload(dex_id, lang)
        except Exception as e:
            return jsonify(status="error", msg=f"Kartenliste nicht abrufbar: {e}"), 502
        payload["skipped"] = skipped
        return jsonify(payload)
    return jsonify(status="end", skipped=skipped)


@app.get("/api/cardinfo")
def cardinfo():
    lang, tid = request.args.get("lang", "de"), request.args["id"]
    try:
        card = fetch(f"{TCG}/{lang}/cards/{tid}")
    except Exception as e:
        return jsonify(status="error", msg=f"Kartendatenbank nicht erreichbar: {e}"), 502
    return jsonify(status="ok", card=slot_info(card_row(card, lang)))


@app.get("/api/setlist")
def setlist():
    lang = request.args.get("lang", "de")
    lang = lang if lang in LANGS else "de"
    owned = {}
    for r in q("SELECT id FROM cards"):
        l, tid = split_cid(r["id"])
        key = (l, tid.rsplit("-", 1)[0])
        owned[key] = owned.get(key, 0) + 1
    names = ja_set_names() if lang == "ja" else {}
    out = []
    for ser in get_series(lang):
        sets = []
        for s in ser["sets"]:
            c = s.get("cardCount") or {}
            sets.append({"id": s["id"], "name": s["name"], "name_en": names.get(norm_code(s["id"])), "logo": s.get("logo"),
                         "symbol": s.get("symbol"), "official": c.get("official"), "total": c.get("total"),
                         "owned": owned.get((lang, s["id"]), 0)})
        ser_name = f"{SERIES_DE.get(ser['id'].lower(), ser['name'])} (Japan)" if lang == "ja" else ser["name"]
        out.append({"id": ser["id"], "name": ser_name, "sets": sets})
    return jsonify(out)


@app.get("/api/seriesdebug")
def seriesdebug():
    """Diagnose: welche Serien die Kartendatenbank kennt und welche in der Sets-Ansicht erscheinen."""
    lang = request.args.get("lang", "de")
    lang = lang if lang in LANGS else "de"
    get_series(lang)
    return jsonify(_series_dbg.get(lang, []))


@app.get("/api/imgcheck")
def imgcheck():
    """Diagnose der Bild-Ersatzquelle, z. B. ?lang=ja&set=M6"""
    lang, set_id = request.args.get("lang", "ja"), request.args["set"]
    cat, g = tp_group_for(lang, set_id)
    m = {k: v for k, v in tp_images(lang, set_id).items() if not k.startswith("n:")} if g else {}
    e = en_images(set_id) if lang not in ("en", "ja") else {}
    return jsonify(kategorie=cat, gruppen_gefunden=len(tp_groups(cat)), gruppe=g, bilder_tcgplayer=len(m), bilder_tcgdex_englisch=len(e), bilder_gesamt=len(fallback_map(lang, set_id)),
                   beispiel=dict(list(m.items())[:2]) or dict(list(e.items())[:2]))


@app.get("/api/setcards")
def setcards():
    lang, set_id = request.args.get("lang", "de"), request.args["set"]
    try:
        s = fetch(f"{TCG}/{lang}/sets/{set_id}")
    except Exception as e:
        return jsonify(status="error", msg=f"Kartendatenbank nicht erreichbar: {e}"), 502
    qty = {r["id"]: r["qty"] for r in q("SELECT id, qty FROM cards")}
    binder = {r["card_id"] for r in q("SELECT card_id FROM binder")}
    wish = {r["card_id"] for r in q("SELECT card_id FROM wishlist")}
    cards = []
    fb = fallback_map(lang, set_id, low=True) if lang == "ja" or any(not c.get("image") for c in s.get("cards", [])) else {}
    for c in s.get("cards", []):
        cid = c["id"] if lang == "de" else f"{lang}:{c['id']}"
        img = c["image"] + "/low.webp" if c.get("image") else fb.get(str(c["localId"]).lstrip("0").lower(), "")
        did = guess_dex(c.get("name", ""))
        cards.append({"tid": c["id"], "local_id": c["localId"], "name": c.get("name", ""), "image": img,
                      "dex_id": did, "dex_name": name_index()["de"].get(did) if did else "",
                      "owned": qty.get(cid, 0), "in_binder": cid in binder, "wished": cid in wish})
    cc = s.get("cardCount") or {}
    return jsonify(status="ok", name=s.get("name"), name_en=ja_set_names().get(norm_code(set_id)) if lang == "ja" else None,
                   total=cc.get("total"), official=cc.get("official"), cards=cards, fb=fb)


@app.post("/api/replace")
def replace():
    d = request.json
    run("INSERT OR REPLACE INTO binder VALUES(?,?)", (d["dex_id"], d["card_id"]))
    return jsonify(ok=True)


@app.post("/api/qty")
def qty_change():
    """Anzahl einer vorhandenen Karte um delta aendern. Das letzte Exemplar wird nicht entfernt (last=true), das Loeschen bestaetigt der Browser."""
    d = request.json
    r = q("SELECT qty FROM cards WHERE id=?", (d["card_id"],))
    if not r:
        return jsonify(ok=False, msg="Karte nicht gefunden"), 404
    new = r[0]["qty"] + int(d.get("delta", 1))
    if new < 1:
        return jsonify(ok=False, qty=r[0]["qty"], last=True)
    run("UPDATE cards SET qty=? WHERE id=?", (new, d["card_id"]))
    log_session(d["card_id"], 1 if int(d.get("delta", 1)) > 0 else -1)
    return jsonify(ok=True, qty=new)


@app.post("/api/delete")
def delete():
    cid = request.json["card_id"]
    card = q("SELECT dex_id FROM cards WHERE id=?", (cid,))
    run("DELETE FROM cards WHERE id=?", (cid,))
    run("DELETE FROM binder WHERE card_id=?", (cid,))
    dex_id = card[0]["dex_id"] if card else None
    if dex_id and not q("SELECT 1 FROM binder WHERE dex_id=?", (dex_id,)):
        other = q("SELECT id FROM cards WHERE dex_id=? LIMIT 1", (dex_id,))
        if other:  # naechste vorhandene Karte rueckt in den Binder
            run("INSERT INTO binder VALUES(?,?)", (dex_id, other[0]["id"]))
    return jsonify(ok=True)


@app.get("/api/pricecheck")
def pricecheck():
    """Diagnose: zeigt, welche Preisdaten die Kartendatenbank zu einer Karte liefert."""
    lang, cid = request.args.get("lang", "de"), request.args["id"]
    try:
        c = fetch(f"{TCG}/{lang}/cards/{cid}")
        return jsonify(name=c.get("name"), hat_preisfeld="pricing" in c, pricing=c.get("pricing"), berechnet=best_price(c))
    except Exception as e:
        return jsonify(fehler=str(e)), 502


@app.post("/api/prices/refresh")
def prices_refresh():
    if not price_prog["running"]:
        threading.Thread(target=refresh_prices, daemon=True).start()
    return jsonify(ok=True)


def app_version():
    try:
        with open(os.path.join(app.root_path, "VERSION"), encoding="utf-8") as f:
            return f.read().strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def track_version():
    """Merkt sich, von welcher Version aus aktualisiert wurde (fuer die Anzeige "Was ist neu").
    prev_version: "" = Neuinstallation, "0" = Update von einer Version ohne diese Funktion."""
    cur, last = app_version(), meta_get("last_version", "") or ""
    if last == cur:
        return
    had_data = q("SELECT COUNT(*) AS n FROM cards")[0]["n"] or q("SELECT COUNT(*) AS n FROM pokemon")[0]["n"]
    meta_set("prev_version", last or ("0" if had_data else ""))
    meta_set("last_version", cur)


@app.get("/api/version")
def version_get():
    return jsonify(version=app_version(), prev=meta_get("prev_version", "") or "")


def startup():
    """Datenbank anlegen/migrieren und Hintergrundaufgaben starten.
    Wird von app.py selbst und vom Desktop-Starter (desktop/ninedex_desktop.py) aufgerufen."""
    init()
    track_version()
    n_names = q("SELECT COUNT(*) AS n FROM pokemon")[0]["n"]
    if (n_names < 1000 or q("SELECT COUNT(*) AS n FROM dex_info")[0]["n"] < n_names or q("SELECT COUNT(*) AS n FROM pokemon WHERE name_en IS NULL OR name_es IS NULL")[0]["n"]
            or q("SELECT COUNT(*) AS n FROM dex_text WHERE lang='es'")[0]["n"] < n_names):
        threading.Thread(target=load_pokemon, daemon=True).start()
    if q("SELECT COUNT(*) AS n FROM cards WHERE price IS NULL OR px_at IS NULL")[0]["n"]:
        threading.Thread(target=refresh_prices, args=(True,), daemon=True).start()
    if q("SELECT COUNT(*) AS n FROM cards WHERE image IS NULL OR image = ''")[0]["n"]:
        threading.Thread(target=backfill_images, daemon=True).start()
    if q("SELECT COUNT(*) AS n FROM cards WHERE lang='ja'")[0]["n"]:
        threading.Thread(target=backfill_ja_names, daemon=True).start()
    if q("SELECT COUNT(*) AS n FROM cards WHERE category IS NULL")[0]["n"]:
        threading.Thread(target=backfill_categories, daemon=True).start()


if __name__ == "__main__":
    startup()
    # lokal: 127.0.0.1 | im Heimnetz/Docker: HOST=0.0.0.0
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5000")))
