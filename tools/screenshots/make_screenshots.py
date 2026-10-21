"""Erzeugt die Screenshots fuer README und Doku mit einer Demo-Sammlung.

    pip install playwright pillow && playwright install chromium
    git clone --depth 1 --filter=blob:none --sparse https://github.com/PokeAPI/pokeapi /tmp/pokeapi
    (cd /tmp/pokeapi && git sparse-checkout set --no-cone /data/v2/csv/pokemon_species_names.csv /data/v2/csv/pokemon_species_flavor_text.csv)
    python tools/screenshots/make_screenshots.py --pokeapi /tmp/pokeapi/data/v2/csv [--fonts DIR]

Ergebnis: docs/screenshots/*.png

Es werden KEINE echten Kartenbilder und kein offizielles Artwork verwendet: Kartenbilder sind selbst
gezeichnete Platzhalter, die Silhouetten fehlender Pokemon neutrale Formen. Alle Internetzugriffe des
Browsers werden abgefangen. Pokemon-Namen und Pokedex-Texte kommen aus den CSV-Dateien von PokeAPI.
Optional: --fonts mit PressStart2P-Regular.ttf und VT323-Regular.ttf (Google Fonts, OFL), sonst Ersatzschrift.
"""
import argparse
import csv
import datetime
import hashlib
import io
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.request

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "docs", "screenshots")
PORT = 5091
LANG_IDS = {"de": "6", "en": "9", "es": "7"}
GAME_BY_VERSION = {}  # version_id -> slug (aus versions.csv, falls vorhanden)

# ---------------------------------------------------------------- Demo-Sammlung

SETS = [  # (Set-ID, Name, Groesse, Sprache)
    ("sv01", "Karmesin & Purpur", 198, "de"), ("sv02", "Entwicklungen in Paldea", 193, "de"),
    ("sv03", "Obsidianflammen", 197, "de"), ("sv03.5", "151", 165, "de"), ("sv04", "Paradoxrift", 182, "de"),
    ("sv05", "Gewalten der Zeit", 162, "de"), ("sv06", "Maskerade im Zwielicht", 167, "de"),
    ("sv07", "Stellarkrone", 142, "de"), ("sv08", "Stürmische Funken", 191, "de"),
    ("sv09", "Reisegefährten", 159, "de"), ("sv08.5", "Prismatic Evolutions", 131, "en"),
    ("sv10", "Destined Rivals", 182, "en"), ("sv2a", "Pokémon Card 151", 165, "ja"),
]
RARITIES = [("Häufig", 0.08, 0.30), ("Ungewöhnlich", 0.15, 0.20), ("Selten", 0.4, 0.14), ("Holografisch Selten", 1.2, 0.08),
            ("Doppelselten", 3.5, 0.10), ("Ultra Selten", 9.0, 0.05), ("Selten, Illustration", 14.0, 0.08),
            ("Selten, besondere Illustration", 55.0, 0.03), ("Hyperselten", 25.0, 0.02)]
FULLART = {"Ultra Selten", "Selten, Illustration", "Selten, besondere Illustration", "Hyperselten"}
FAVS = [6, 25, 133, 149, 197, 248, 384, 445, 658, 778, 887, 1000]
STARS = [6, 25, 150, 151, 197, 249, 384, 448, 700, 778, 887, 1007]


def load_pokeapi(csvdir):
    names, genus = {}, {}
    for r in csv.DictReader(open(os.path.join(csvdir, "pokemon_species_names.csv"), encoding="utf-8")):
        sid = int(r["pokemon_species_id"])
        for l, lid in LANG_IDS.items():
            if r["local_language_id"] == lid:
                names[(sid, l)] = r["name"]
                genus[(sid, l)] = r["genus"]
            if r["local_language_id"] == "11":
                names[(sid, "ja")] = r["name"]
            if r["local_language_id"] == "1" and (sid, "ja") not in names:
                names[(sid, "ja")] = r["name"]
    flav = {}
    for r in csv.DictReader(open(os.path.join(csvdir, "pokemon_species_flavor_text.csv"), encoding="utf-8")):
        for l, lid in LANG_IDS.items():
            if r["language_id"] == lid:
                k = (int(r["species_id"]), l)
                v = int(r["version_id"])
                if k not in flav or v > flav[k][0]:
                    flav[k] = (v, re.sub(r"\s+", " ", r["flavor_text"].replace("­", "").replace("-\n", "")).strip())
    return names, genus, flav


GAME_NAMES = {"de": ["Karmesin", "Purpur", "Schwert", "Schild"], "en": ["Scarlet", "Violet", "Sword", "Shield"],
              "es": ["Escarlata", "Púrpura", "Espada", "Escudo"]}


def seed(db, csvdir):
    if os.path.exists(db):
        os.remove(db)
    os.environ["DB_PATH"] = db
    sys.path.insert(0, ROOT)
    import app as A
    A.init()
    names, genus, flav = load_pokeapi(csvdir)
    rnd = random.Random(151)
    con = A.sqlite3.connect(db)
    for i in range(1, 1026):
        n = {l: names.get((i, l), f"#{i}") for l in ("de", "en", "es", "ja")}
        con.execute("INSERT INTO pokemon(id,name,name_en,name_ja,name_es) VALUES(?,?,?,?,?)", (i, n["de"], n["en"], n["ja"], n["es"]))
        for l in ("de", "en", "es"):
            g = genus.get((i, l), "")
            t = flav.get((i, l), (0, ""))[1]
            game = rnd.choice(GAME_NAMES[l])
            if l == "de":
                con.execute("INSERT INTO dex_info VALUES(?,?,?,?)", (i, g, t, game))
            else:
                con.execute("INSERT INTO dex_text VALUES(?,?,?,?,?)", (i, l, g, t, game))

    today = datetime.date.today()
    owned = sorted(set([i for i in range(1, 31) if i not in (2, 11, 14, 20, 29)] + rnd.sample(range(31, 387), 190)
                       + rnd.sample(range(387, 1026), 125) + STARS))
    used = set()
    cards, binder, draw = [], {}, {}
    for dex in owned:
        k = 1 + (rnd.random() < 0.35) + (rnd.random() < 0.12)
        for j in range(k):
            sid, sname, size, lang = rnd.choices(SETS, weights=[1] * 10 + [0.6, 0.6, 0.5])[0]
            if dex <= 151 and rnd.random() < 0.35:
                sid, sname, size, lang = SETS[3] if rnd.random() < 0.8 else SETS[12]
            rar = rnd.choices(RARITIES, weights=[r[2] for r in RARITIES])[0]
            if dex in STARS and j == 0:
                rar = rnd.choice([RARITIES[6], RARITIES[7], RARITIES[5]])
            num = rnd.randint(1, size) if rar[0] not in FULLART else rnd.randint(size + 1, size + 40)
            base = names[(dex, "ja" if lang == "ja" else ("en" if lang == "en" else "de"))]
            suffix = " ex" if rar[0] in ("Doppelselten", "Ultra Selten", "Selten, besondere Illustration", "Hyperselten") else ""
            price = round(rar[1] * rnd.uniform(0.5, 1.8) * (2.5 if dex in (6, 25, 150, 151, 197) else 1), 2)
            while f"{sid}-{num:03d}" in used:
                num += 1
            cid = f"{sid}-{num:03d}"
            used.add(cid)
            added = (today - datetime.timedelta(days=rnd.randint(0, 40))).isoformat()
            qty = 1 + (rnd.random() < 0.25) + (rnd.random() < 0.08)
            variant = "reverse" if rar[0] in ("Häufig", "Ungewöhnlich") and rnd.random() < 0.2 else None
            draw[cid] = names[(dex, "en")] + suffix if lang == "ja" else None
            cards.append((cid, base + suffix, sname, f"{num:03d}", rar[0], f"https://demo.binderdex.invalid/card/{cid}.png", dex, qty, lang,
                          price, "Pokemon", added, added, round(price * rnd.uniform(0.75, 1.3), 2), variant, sid))
            cur = binder.get(dex)
            if cur is None or (rar[0] in FULLART and cur[1] not in FULLART):
                binder[dex] = (cid, rar[0])
    for i, (nm, sid) in enumerate((("Professor-Forschung", "sv01"), ("Pokéball", "sv01"), ("Supercapsule", "sv02"), ("Arven", "sv01"))):
        cards.append((f"{sid}-t{i}", nm, "Karmesin & Purpur", f"{180 + i}", "Ungewöhnlich", f"https://demo.binderdex.invalid/card/{sid}-t{i}.png",
                      None, 2 + i, "de", 0.12, "Trainer", today.isoformat(), today.isoformat(), 0.1, None, sid))
    for c in cards:
        con.execute("""INSERT OR IGNORE INTO cards(id,name,set_name,local_id,rarity,image,dex_id,qty,lang,price,category,added,px_at,price_old,variant)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", c[:15])
    for dex, (cid, _) in binder.items():
        con.execute("INSERT INTO binder VALUES(?,?)", (dex, cid))
    for f in FAVS:
        con.execute("INSERT OR IGNORE INTO favorites VALUES(?)", (f,))
    for dex, sname, rar, price in ((150, "151", "Selten, besondere Illustration", 89.0), (384, "Gewalten der Zeit", "Hyperselten", 34.5),
                                   (94, "Paldeas Schicksale", "Selten, Illustration", 21.0)):
        con.execute("INSERT INTO wishlist VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (f"w-{dex}", names[(dex, "de")] + " ex", sname, "sv", "201", rar,
                    f"https://demo.binderdex.invalid/card/w-{dex}.png", dex, "de", price, today.isoformat(), price * 1.15))
    side = [c for c in cards if c[0] not in {b[0] for b in binder.values()}][:6]
    for c in side[:3]:
        con.execute("INSERT INTO listings(card_id,qty,price,cond,status,ts) VALUES(?,?,?,?,?,?)", (c[0], 1, round(c[9] * 0.95, 2), "NM", "listed", today.isoformat()))
    con.execute("INSERT INTO listings(card_id,qty,price,cond,status,ts,done_ts) VALUES(?,?,?,?,?,?,?)", (side[3][0], 1, 4.5, "NM", "sold", today.isoformat(), today.isoformat()))
    star = binder[6][0]
    con.execute("""INSERT INTO grades(ts,card_id,name,set_name,image,best,low,high,limiting,conf,cen_f,cen_b,subs,notes,raw_price)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (today.isoformat(), star, "Glurak ex", "Obsidianflammen", f"https://demo.binderdex.invalid/card/{star}.png",
                                                            9, 8, 10, "Ecken", "hoch", 54.0, 61.0, json.dumps({"Ecken": 9, "Kanten": 9.5, "Oberfläche": 9.5}), "", 62.0))
    total = len(binder)
    for d in range(60, -1, -1):
        day = (today - datetime.timedelta(days=d)).isoformat()
        f = 1 - d / 75
        con.execute("INSERT OR REPLACE INTO value_history VALUES(?,?,?,?,?)", (day, round(980 * f + rnd.uniform(-15, 15), 2), round(1420 * f + rnd.uniform(-20, 20), 2),
                    int(len(cards) * f), int(total * f)))
    for k, v in {"scans": 412, "exports": 3, "sessions": 9, "big_sessions": 2, "grade_checks": 4, "grades_saved": 1, "listings": 4, "sold": 1,
                 "ui_langs": "de,en,es", "ui_default": "de"}.items():
        con.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (k, str(v)))
    con.commit()
    con.close()
    return draw


# ---------------------------------------------------------------- Selbst gezeichnete Bilder

PAL = [((220, 70, 60), (255, 190, 90)), ((40, 120, 220), (130, 220, 255)), ((60, 170, 90), (190, 240, 140)), ((140, 80, 200), (240, 170, 255)),
       ((230, 180, 40), (255, 240, 160)), ((90, 90, 110), (200, 200, 220)), ((200, 60, 140), (255, 180, 210))]


def _font(size, bold=False):
    for f in ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def card_png(key, title, sub, fullart):
    """Platzhalter-Karte: abstraktes Motiv, Name und Nummer. Kein echtes Kartenmotiv."""
    h = int(hashlib.md5(key.encode()).hexdigest(), 16)
    rnd = random.Random(h)
    a, b = PAL[h % len(PAL)]
    W, H = 300, 420
    im = Image.new("RGB", (W, H), (245, 214, 70) if not fullart else a)
    d = ImageDraw.Draw(im)
    inner = (12, 12, W - 12, H - 12)
    grad = Image.new("RGB", (W, H))
    gd = ImageDraw.Draw(grad)
    for y in range(H):
        t = y / H
        gd.line([(0, y), (W, y)], fill=tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3)))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle(inner, 14, fill=255)
    im.paste(grad, (0, 0), mask)
    art = (28, 58, W - 28, 238) if not fullart else (12, 12, W - 12, H - 12)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for _ in range(9 if fullart else 6):
        cx, cy = rnd.randint(art[0], art[2]), rnd.randint(art[1], art[3])
        r = rnd.randint(18, 70)
        ld.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, rnd.randint(40, 110)))
    for _ in range(3):
        y0 = rnd.randint(art[1], art[3])
        ld.arc((art[0] - 60, y0 - 80, art[2] + 60, y0 + 80), 200, 340, fill=(255, 255, 255, 140), width=6)
    layer = layer.filter(ImageFilter.GaussianBlur(1.5))
    if not fullart:
        frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(frame).rectangle(art, outline=(250, 230, 150, 255), width=4)
        clip = Image.new("L", (W, H), 0)
        ImageDraw.Draw(clip).rectangle(art, fill=255)
        im.paste(Image.blend(Image.new("RGB", (W, H), b), Image.new("RGB", (W, H), a), 0.4), (0, 0), clip)
        im.paste(layer, (0, 0), layer)
        im.paste(frame, (0, 0), frame)
    else:
        im.paste(layer, (0, 0), layer)
    d = ImageDraw.Draw(im)
    d.text((26, 22), title[:20], font=_font(20, True), fill=(20, 20, 30) if not fullart else (255, 255, 255))
    if not fullart:
        for i in range(3):
            y = 262 + i * 36
            d.rounded_rectangle((28, y, W - 28, y + 26), 6, fill=(255, 255, 255, 180))
            d.rectangle((40, y + 10, 40 + rnd.randint(80, 190), y + 15), fill=(120, 120, 130))
    d.text((26, H - 34), sub, font=_font(13), fill=(30, 30, 40) if not fullart else (255, 255, 255))
    d.text((W - 92, H - 34), "DEMO", font=_font(13, True), fill=(30, 30, 40) if not fullart else (255, 255, 255))
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def silhouette_png(dex):
    """Neutrale Form statt Pokemon-Artwork (fuer noch fehlende Pokemon)."""
    rnd = random.Random(dex)
    im = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((58, 70, 198, 220), fill=(20, 20, 20, 255))
    d.ellipse((82, 30, 174, 122), fill=(20, 20, 20, 255))
    for _ in range(rnd.randint(1, 3)):
        x = rnd.randint(70, 170)
        d.polygon([(x, 60), (x + 18, 10 + rnd.randint(0, 30)), (x + 30, 70)], fill=(20, 20, 20, 255))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


# ---------------------------------------------------------------- Aufnahmen

def run(args):
    from playwright.sync_api import sync_playwright
    os.makedirs(OUT, exist_ok=True)
    db = os.path.join(args.work, "demo.db")
    draw = seed(db, args.pokeapi)  # Kartentitel fuer japanische Karten in lateinischer Schrift
    meta = {}
    import sqlite3
    con = sqlite3.connect(db)
    for cid, name, setn, lid, rar, dex in con.execute("SELECT id, name, set_name, local_id, rarity, dex_id FROM cards"):
        meta[cid] = (draw.get(cid) or name, f"{setn} {lid}", rar in FULLART)
    for cid, name, setn, lid, rar in con.execute("SELECT card_id, name, set_name, local_id, rarity FROM wishlist"):
        meta[cid] = (name, f"{setn} {lid}", rar in FULLART)
    con.close()

    env = dict(os.environ, DB_PATH=db, PORT=str(PORT), HTTPS_PROXY="http://127.0.0.1:9", https_proxy="http://127.0.0.1:9",
               HTTP_PROXY="http://127.0.0.1:9", PYTHONUNBUFFERED="1")
    env.pop("BINDERDEX_LANGS", None)
    srv = subprocess.Popen([sys.executable, "app.py"], cwd=ROOT, env=env, stdout=open(os.path.join(args.work, "server.log"), "w"), stderr=subprocess.STDOUT)
    for _ in range(80):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/i18n", timeout=1)
            break
        except Exception:
            time.sleep(0.25)

    fonts = {}
    if args.fonts:
        for f in ("PressStart2P-Regular.ttf", "VT323-Regular.ttf"):
            p = os.path.join(args.fonts, f)
            if os.path.exists(p):
                fonts[f] = open(p, "rb").read()
    font_css = "".join(f"@font-face{{font-family:'{fam}';src:url(https://fonts.demo.invalid/{f}) format('truetype');}}"
                       for fam, f in (("Press Start 2P", "PressStart2P-Regular.ttf"), ("VT323", "VT323-Regular.ttf")) if f in fonts)
    cache = {}

    def route(r):
        u = r.request.url
        if u.startswith(f"http://127.0.0.1:{PORT}"):
            return r.continue_()
        if "fonts.googleapis.com" in u:
            return r.fulfill(status=200, content_type="text/css", body=font_css)
        if "fonts.demo.invalid" in u:
            return r.fulfill(status=200, content_type="font/ttf", body=fonts.get(u.rsplit("/", 1)[1], b""))
        m = re.search(r"/card/([^/]+?)\.png", u)
        if m and m.group(1) in meta:
            k = m.group(1)
            if k not in cache:
                n, sub, fa = meta[k]
                cache[k] = card_png(k, n, sub, fa)
            return r.fulfill(status=200, content_type="image/png", body=cache[k])
        m = re.search(r"official-artwork/(\d+)\.png", u)
        if m:
            return r.fulfill(status=200, content_type="image/png", body=silhouette_png(int(m.group(1))))
        if u.endswith(".js"):
            return r.fulfill(status=200, content_type="text/javascript", body="")
        return r.abort()

    shots = []
    with sync_playwright() as p:
        b = p.chromium.launch()

        def page(lang, w=1440, h=900, mobile=False):
            ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=1 if not mobile else 2, is_mobile=mobile, has_touch=mobile,
                                locale={"de": "de-DE", "en": "en-US", "es": "es-ES"}[lang])
            ctx.add_init_script(f"try{{localStorage.setItem('uiLang','{lang}');localStorage.setItem('theme','rot');}}catch(e){{}}")
            pg = ctx.new_page()
            pg.route("**/*", route)
            pg.goto(f"http://127.0.0.1:{PORT}/?ui={lang}")
            pg.wait_for_timeout(2500)
            pg.evaluate("() => { const t = document.querySelector('#toasts'); if (t) t.innerHTML = ''; document.querySelectorAll('.toast').forEach(e => e.remove()); }")
            return ctx, pg

        def snap(pg, name, full=False, clip=None):
            pg.evaluate("() => document.querySelectorAll('#toasts > *, .toast').forEach(e => e.remove())")
            pg.wait_for_timeout(600)
            path = os.path.join(OUT, name)
            pg.screenshot(path=path, full_page=full, clip=clip)
            shots.append(path)

        # 1) Pokedex auf Englisch und Deutsch
        for lang in ("en", "de"):
            ctx, pg = page(lang)
            snap(pg, f"pokedex-{lang}.png")
            ctx.close()
        # 2) Pokemon-Fenster (Glurak) auf Englisch
        ctx, pg = page("en")
        pg.evaluate("() => document.querySelector('.t[data-id=\"6\"] img').click()")
        pg.wait_for_timeout(1500)
        snap(pg, "pokemon-en.png")
        # 3) Statistik
        pg.evaluate("() => { document.querySelector('#modal').style.display='none'; openStats(); }")
        pg.wait_for_timeout(2000)
        pg.set_viewport_size({"width": 1440, "height": 1700})
        pg.wait_for_timeout(800)
        snap(pg, "statistics-en.png")
        pg.set_viewport_size({"width": 1440, "height": 900})
        # 4) Binder-Seite
        pg.evaluate("() => { document.querySelector('#stmodal').style.display='none'; openBinder(1); }")
        pg.wait_for_timeout(1500)
        snap(pg, "binder-en.png")
        # 5) Verkaufen auf Cardmarket (Assistent mit Auswahl)
        pg.evaluate("() => { document.querySelector('#bmodal').style.display='none'; document.querySelector('#side').click(); }")
        pg.wait_for_timeout(1500)
        pg.evaluate("() => document.querySelector('#msell').click()")
        pg.wait_for_timeout(1500)
        pg.evaluate("() => [...document.querySelectorAll('#vbody input[type=checkbox]')].slice(0, 5).forEach(c => { c.checked = true; c.dispatchEvent(new Event('change', {bubbles: true})); })")
        pg.wait_for_timeout(800)
        snap(pg, "sell-en.png")
        ctx.close()
        # 6) Spanisch: Pokedex + Sprachen-Dialog
        ctx, pg = page("es")
        pg.evaluate("() => openLangs(false)")
        pg.wait_for_timeout(800)
        snap(pg, "languages-es.png")
        ctx.close()
        # 7) Handy (Deutsch)
        ctx, pg = page("de", 390, 844, mobile=True)
        snap(pg, "mobile-de.png")
        ctx.close()
        b.close()
    srv.terminate()

    for path in shots:  # verkleinern (Breite max. 1280) und als Palette speichern
        im = Image.open(path).convert("RGB")
        if im.width > 1280:
            im = im.resize((1280, round(im.height * 1280 / im.width)), Image.LANCZOS)
        if "mobile" in path:
            im = im.resize((390, round(im.height * 390 / im.width)), Image.LANCZOS)
        im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(path, optimize=True)
        print(f"{os.path.relpath(path, ROOT)}  {os.path.getsize(path) // 1024} KB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pokeapi", required=True, help="Ordner mit pokemon_species_names.csv und pokemon_species_flavor_text.csv")
    ap.add_argument("--fonts", help="Ordner mit PressStart2P-Regular.ttf und VT323-Regular.ttf")
    ap.add_argument("--work", default=os.path.join(ROOT, "tools", "screenshots", ".work"))
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    run(a)
