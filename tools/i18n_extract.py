"""Sammelt alle deutschen Oberflaechentexte aus static/index.html (Markup + JavaScript) und app.py.

    python tools/i18n_extract.py            -> tools/i18n_keys.json (Liste der Schluessel)
    python tools/i18n_extract.py --check    -> zeigt Texte, die in static/i18n/<lang>.json fehlen
                                               (ausser denen in tools/i18n_ignore.txt)

Schluessel sind die deutschen Originaltexte (Leerraum zusammengefasst). Eingefuegte Werte
(${...} in Template-Strings) werden zu Platzhaltern {0}, {1}, ...
"""
import html.parser
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LETTER = re.compile(r"[A-Za-zÄÖÜäöüß]")
GERMANISH = re.compile(r"[A-Za-zÄÖÜäöüß]{2,}")
ATTRS = ("title", "placeholder", "aria-label")


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def renumber(s):
    """Platzhalter in einem Textstueck neu ab {0} durchzaehlen."""
    i = iter(range(1000))
    return re.sub(r"\x00\d+\x00", lambda m: "{%d}" % next(i), s)


class Markup(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "svg"):
            self.skip += 1
        for k, v in attrs:
            if k in ATTRS and v:
                self.out.append(v)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "svg") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def markup_texts(fragment):
    """Texte und uebersetzbare Attribute aus einem HTML-Stueck (Platzhalter \x00n\x00 bleiben erhalten)."""
    p = Markup()
    # Tags mit Platzhaltern in Attributen nicht kaputt parsen: Platzhalter sind harmlose Zeichen
    p.feed(fragment)
    p.close()
    return p.out


def js_literals(src):
    """Alle String-Literale aus JavaScript-Code. Liefert (text, ist_template) mit Platzhaltern \x00n\x00."""
    out, i, n = [], 0, len(src)
    prev = "("  # letztes bedeutsames Zeichen (fuer Regex-Erkennung)

    def read_template(i):
        # i zeigt hinter das oeffnende `
        buf, k = [], 0
        while i < n:
            c = src[i]
            if c == "\\":
                nx = src[i + 1]
                buf.append({"n": "\n", "t": "\t"}.get(nx, nx)); i += 2; continue
            if c == "`":
                return "".join(buf), i + 1
            if c == "$" and i + 1 < n and src[i + 1] == "{":
                j, depth = i + 2, 1
                start = j
                # inneren Ausdruck ueberspringen, verschachtelte Literale rekursiv sammeln
                while j < n and depth:
                    ch = src[j]
                    if ch in "\"'":
                        s, j = read_quoted(j + 1, ch); out.append((s, False)); continue
                    if ch == "`":
                        s, j = read_template(j + 1); out.append((s, True)); continue
                    if ch == "{": depth += 1
                    elif ch == "}": depth -= 1
                    j += 1
                buf.append("\x00%d\x00" % k); k += 1
                i = j
                continue
            buf.append(c); i += 1
        return "".join(buf), i

    def read_quoted(i, q):
        buf = []
        while i < n:
            c = src[i]
            if c == "\\":
                nx = src[i + 1]
                buf.append({"n": "\n", "t": "\t"}.get(nx, nx)); i += 2; continue
            if c == q or c == "\n":
                return "".join(buf), i + 1
            buf.append(c); i += 1
        return "".join(buf), i

    while i < n:
        c = src[i]
        if src.startswith("//", i) and prev not in "\x01":
            # Kommentar oder Regex? // ist nie ein gueltiger Regex-Anfang -> Kommentar
            j = src.find("\n", i); i = n if j < 0 else j; continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2); i = n if j < 0 else j + 2; continue
        if c in "\"'":
            s, i = read_quoted(i + 1, c); out.append((s, False)); prev = "a"; continue
        if c == "`":
            s, i = read_template(i + 1); out.append((s, True)); prev = "a"; continue
        if c == "/":
            word = re.search(r"([A-Za-z_$][\w$]*)\s*$", src[max(0, i - 20):i])
            if prev in "(,=:[!&|?{};+-*%<>~^\n" or (word and word.group(1) in ("return", "typeof", "case")):
                # Regex-Literal ueberspringen
                j, cls = i + 1, False
                while j < n:
                    ch = src[j]
                    if ch == "\\": j += 2; continue
                    if ch == "[": cls = True
                    elif ch == "]": cls = False
                    elif ch == "/" and not cls: break
                    elif ch == "\n": break
                    j += 1
                i = j + 1
                while i < n and src[i].isalpha(): i += 1
                prev = "a"; continue
        if not c.isspace():
            prev = c if not (c.isalnum() or c in "_$") else "a"
        i += 1
    return out


def keys_from_literal(text, is_template):
    res = []
    if "<" in text and re.search(r"<[a-zA-Z/!]", text):
        parts = markup_texts(text)
    else:
        parts = [text]
    for p in parts:
        k = renumber(norm(p))
        if not k:
            continue
        literal = re.sub(r"\{\d+\}", "", k)
        if LETTER.search(literal):
            res.append(k)
        elif "{" in k and re.search(r"[^\s{}\d]", literal) and len(re.findall(r"\{\d+\}", k)) >= 1:
            res.append(k)  # reines Muster ohne Woerter (z. B. "{0}: {1}") -> Identitaet, damit Teile uebersetzt werden
    return res


SKIP = re.compile(r"""^(?:[#.\[]|[a-z0-9_-]+$|https?:|/api|/static|[a-z]+[A-Z]\w*$|\W*$|data:|image/|application/|text/|M\d)""")


def plausible(k):
    """Filtert Code-Strings (Selektoren, Klassen, IDs, Ereignisnamen, CSS) heraus."""
    lit = re.sub(r"\{\d+\}", "", k)
    if SKIP.match(k) and " " not in k:
        return False
    if re.fullmatch(r"[\w\s{}.,:;#%()\[\]\-+*/=<>!?&|'\"$]*", k) and not re.search(r"[A-ZÄÖÜa-zäöüß]{3,}", lit):
        return "{" in k and re.search(r"[·:–(),×/%€]", lit) is not None
    if re.search(r"(?:^|\s)(?:px|rem|em|vh|vw|rgba?\(|var\(--|solid|flex|none|auto|block|inherit|transparent|important)\b", k) and ";" in k:
        return False
    if re.fullmatch(r"[a-z][\w-]*(?: [a-z][\w-]*)*", k) and not re.search(r"[äöüß]", k):
        return False  # Klassenlisten, Ereignisnamen, Schluesselwoerter (alles klein, keine Umlaute)
    return True


def extract_html():
    src = open(os.path.join(ROOT, "static", "index.html"), encoding="utf-8").read()
    head, rest = src.split("<body>", 1)
    body, script = rest.split("<script>", 1)
    script = script.rsplit("</script>", 1)[0]
    keys = []
    title = re.search(r"<title>(.*?)</title>", head)
    if title:
        keys.append(title.group(1))
    for t in markup_texts(body):
        k = norm(t)
        if k and LETTER.search(k):
            keys.append(k)
    for text, tpl in js_literals(script):
        keys += keys_from_literal(text, tpl)
    return keys


def extract_py():
    """Meldungen aus app.py, die im Browser erscheinen (msg=..., error=..., Ueberschriften der Exporte)."""
    src = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    src = re.sub(r'"""[\s\S]*?"""', '""', src)  # Docstrings und SQL ueberspringen
    keys = []
    for m in re.finditer(r"""(?<![\w])(f?)("([^"\\\n]|\\.)*"|'([^'\\\n]|\\.)*')""", src):
        is_f, lit = m.group(1), m.group(2)[1:-1]
        if is_f:
            lit = re.sub(r"\{[^{}]*\}", "\x00\x00", lit.replace("{{", "\x01").replace("}}", "\x02"))
            lit = re.sub("\x00\x00", lambda _: "\x00%d\x00" % 0, lit)
            lit = lit.replace("\x01", "{").replace("\x02", "}")
        k = renumber(norm(lit))
        if len(re.findall(GERMANISH, re.sub(r"\{\d+\}", "", k))) >= 1 and re.search(r"[äöüßÄÖÜ]|\b(?:der|die|das|und|nicht|ist|mit|im|ein|eine|keine?|Karte|Karten|bitte|wurde|fehlt|Fehler|kein|zu|auf|vom|von|dem|den|des|oder|nur|noch|gefunden|Pokémon|Set|Preis|Name|Anzahl|Summe|Zustand|Sprache|Seltenheit|Nummer|Wert|Bild|Variante)\b", k):
            keys.append(k)
    return keys


# Texte, die der Server erzeugt oder die aus Kartendaten kommen und nicht als Literal im Code stehen
EXTRA = [
    # Grading (app.py)
    "hoch", "mittel", "niedrig", "Zentrierung vorne", "Zentrierung hinten", "Ecken", "Kanten", "Oberfläche",
    # Verkaufsseite (/verkauf)
    "Verkaufsliste", "Stand {0} · {1} Karten · Wert ca.", "Drucken / Als PDF speichern", "Einzelpreis",
    "Der Nebenstapel ist leer.", "Preise: Cardmarket-Trend (Richtwerte). Erstellt mit Ninedex.", "{0}×",
    # Exporte
    "ja", "nein", "Pokédex-Nr.", "Im Binder", "Cardmarket-Link",
    # zusammengesetzte Meldungen (app.py)
    "Modell nicht gefunden. Pruefe den Modellnamen in den KI-Einstellungen (mit 'ollama pull' installieren).",
    "Modell nicht gefunden. Pruefe den Modellnamen in den KI-Einstellungen.",
    "KI-Dienst nicht erreichbar. Laeuft Ollama auf dem PC, ist die Adresse richtig und der Port 11434 im Netzwerk freigegeben?",
    "KI-Dienst nicht erreichbar. Internetverbindung des Servers pruefen.",
    # kurze, kleingeschriebene Texte, die der Filter fuer Code-Strings sonst verwirft
    "gefangen", "ab Nr.", "Nr.", "Nr. {0}", "Nr. {0} {1}", "blauen", "gelben", "nicht scharf", "lohnt es sich", "bis",
    "keine", "Ja", ", ca.", "billiger", "teurer", "rechts", "links", "invers", "frei", "KI:", "{0} gefangen",
]


def main():
    keys, seen = [], set()
    for k in extract_html() + extract_py():
        if k not in seen and plausible(k):
            seen.add(k); keys.append(k)
    for k in EXTRA:
        if k not in seen:
            seen.add(k); keys.append(k)
    out = os.path.join(ROOT, "tools", "i18n_keys.json")
    json.dump(keys, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(len(keys), "Schluessel ->", out)
    if "--check" in sys.argv:
        ign = {l.rstrip("\n") for l in open(os.path.join(ROOT, "tools", "i18n_ignore.txt"), encoding="utf-8") if not l.startswith("# ")}
        langs = sorted(f[:-5] for f in os.listdir(os.path.join(ROOT, "static", "i18n")) if f.endswith(".json"))
        for lang in langs:
            d = json.load(open(os.path.join(ROOT, "static", "i18n", f"{lang}.json"), encoding="utf-8"))
            miss = [k for k in keys if k not in d and k not in ign]
            print(f"{lang}: {len(miss)} fehlen")
            for k in miss:
                print("   " + json.dumps(k, ensure_ascii=False))


if __name__ == "__main__":
    main()
