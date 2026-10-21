"""Ninedex als Desktop-App.

Startet das Flask-Backend unsichtbar im Hintergrund (nur auf 127.0.0.1) und zeigt die
Oberflaeche in einem eigenen Fenster (pywebview: Windows = WebView2/Edge, macOS = WebKit).

Entwicklung (aus dem Repo-Ordner):
    pip install -r requirements.txt -r desktop/requirements-desktop.txt
    python desktop/ninedex_desktop.py

Umgebungsvariablen (optional):
    NINEDEX_DATA_DIR          eigener Datenordner statt des Standardordners
    NINEDEX_NO_UPDATE_CHECK=1 keine Pruefung auf neue Versionen bei GitHub
    NINEDEX_DEBUG=1           Entwicklerwerkzeuge im Fenster (Rechtsklick > Untersuchen)
Die alten Namen (BINDERDEX_*) aus der Zeit vor der Umbenennung funktionieren weiterhin.
"""
import json
import logging
import logging.handlers
import os
import sys
import threading
import urllib.request

APP_NAME = "Ninedex"
OLD_APP_NAME = "BinderDex"  # frueherer Name, Daten von dort werden beim ersten Start uebernommen
REPO = "askyonex/ninedex"
# Fester Port, damit Browser-Einstellungen (Design, Toene, Quiz-Rekord ...) erhalten bleiben:
# der Browser speichert sie pro Adresse inklusive Port.
PREFERRED_PORT = 47821
HOST = "127.0.0.1"

log = logging.getLogger("ninedex.desktop")


# ---------------------------------------------------------------- Pfade

def env(name, default=None):
    """NINEDEX_<name>, sonst der alte Name BINDERDEX_<name> (vor der Umbenennung)."""
    return os.environ.get("NINEDEX_" + name) or os.environ.get("BINDERDEX_" + name) or default


def resource_dir():
    """Ordner mit app.py, static/ und VERSION (im fertigen Programm: der entpackte Bundle-Ordner)."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS  # von PyInstaller gesetzt
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_dir():
    """Pro Benutzer beschreibbarer Ordner fuer Datenbank, Log und Browser-Speicher."""
    custom = env("DATA_DIR")
    if custom:
        os.makedirs(custom, exist_ok=True)
        return custom
    path = default_data_dir(APP_NAME)
    old = default_data_dir(OLD_APP_NAME)
    # Umbenennung BinderDex -> Ninedex: vorhandene Sammlung einmalig in den neuen Ordner verschieben
    if not os.path.exists(path) and os.path.isdir(old):
        try:
            os.rename(old, path)
        except OSError:
            path = old  # z. B. Ordner gerade gesperrt: dann einfach den alten Ordner weiterbenutzen
    os.makedirs(path, exist_ok=True)
    return path


def default_data_dir(name):
    if sys.platform == "win32":
        return os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), name)
    if sys.platform == "darwin":
        return os.path.expanduser(f"~/Library/Application Support/{name}")
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, name.lower())


def app_version():
    try:
        with open(os.path.join(resource_dir(), "VERSION"), encoding="utf-8") as f:
            return f.read().strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def installer_langs():
    """Sprachen aus ninedex.ini im Programmordner (schreibt der Windows-Installer)."""
    import configparser
    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else resource_dir()
    ini = configparser.ConfigParser()
    try:
        ini.read([os.path.join(base, "binderdex.ini"), os.path.join(base, "ninedex.ini")], encoding="utf-8")
        raw = ini.get("ui", "languages", fallback="")
    except (OSError, configparser.Error):
        return ""
    return ",".join(l for l in (x.strip().lower() for x in raw.split(",")) if l in ("de", "en", "es"))


def setup_logging(ddir):
    """Protokoll in ninedex.log; Abstuerze ausserhalb von Python (z. B. im Fenster) landen in crash.log."""
    # Im Fenster-Modus (ohne Konsole) sind stdout/stderr unter Windows None -> ins Log umleiten
    logfile = os.path.join(ddir, "ninedex.log")
    handler = logging.handlers.RotatingFileHandler(logfile, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    if sys.stdout is None or sys.stderr is None:
        stream = open(logfile, "a", encoding="utf-8", buffering=1)  # noqa: SIM115 (bleibt offen)
        sys.stdout = sys.stdout or stream
        sys.stderr = sys.stderr or stream
    else:
        root.addHandler(logging.StreamHandler())
    try:  # harte Abstuerze (z. B. in WebView2/.NET) mit Python-Stack festhalten
        import faulthandler
        faulthandler.enable(open(os.path.join(ddir, "crash.log"), "a", encoding="utf-8"), all_threads=True)  # noqa: SIM115
    except Exception:  # noqa: BLE001
        pass
    # Fehler in Hintergrund-Threads (Preise, Bilder ...) ebenfalls ins Log
    threading.excepthook = lambda a: logging.getLogger("ninedex.thread").error(
        "Fehler im Thread %s", a.thread.name if a.thread else "?", exc_info=(a.exc_type, a.exc_value, a.exc_traceback))
    return logfile


# ---------------------------------------------------------------- Nur eine Instanz

class SingleInstance:
    """Sperrdatei im Datenordner. Laeuft Ninedex schon, holt ein zweiter Start nur das Fenster nach vorn."""

    def __init__(self, ddir):
        self.path = os.path.join(ddir, "instance.lock")
        self.info = os.path.join(ddir, "instance.json")
        self.fh = None

    def acquire(self):
        self.fh = open(self.path, "a+")  # noqa: SIM115 (bleibt bis zum Ende offen)
        try:
            if sys.platform == "win32":
                import msvcrt
                self.fh.seek(0)
                msvcrt.locking(self.fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            self.fh.close()
            self.fh = None
            return False

    def write_port(self, port):
        with open(self.info, "w", encoding="utf-8") as f:
            json.dump({"port": port, "pid": os.getpid()}, f)

    def focus_running(self):
        try:
            with open(self.info, encoding="utf-8") as f:
                port = int(json.load(f)["port"])
            urllib.request.urlopen(f"http://{HOST}:{port}/__desktop/focus", timeout=3).read()
            return True
        except Exception as e:  # noqa: BLE001
            log.warning("Laufende Instanz nicht erreichbar: %s", e)
            return False


# ---------------------------------------------------------------- Server

def make_server(flask_app):
    from werkzeug.serving import make_server as wz_make_server
    try:
        # Werkzeug beendet bei belegtem Port das Programm (SystemExit), daher beides abfangen
        return wz_make_server(HOST, PREFERRED_PORT, flask_app, threaded=True)
    except (OSError, SystemExit):
        log.warning("Port %s belegt, nehme einen freien Port (Browser-Einstellungen starten dann leer).", PREFERRED_PORT)
        return wz_make_server(HOST, 0, flask_app, threaded=True)


# ---------------------------------------------------------------- Update-Hinweis

def _ver_tuple(v):
    parts = []
    for p in v.lstrip("vV").split("-")[0].split("."):
        parts.append(int(p) if p.isdigit() else 0)
    return tuple(parts + [0] * (3 - len(parts)))


def check_update(window, current):
    if env("NO_UPDATE_CHECK") or current == "0.0.0":
        return
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases/latest",
                                     headers={"Accept": "application/vnd.github+json", "User-Agent": f"{APP_NAME}/{current}"})
        with urllib.request.urlopen(req, timeout=8) as r:
            rel = json.load(r)
        latest, url = rel.get("tag_name", ""), rel.get("html_url", f"https://github.com/{REPO}/releases")
        if not latest or _ver_tuple(latest) <= _ver_tuple(current):
            return
        log.info("Neue Version verfuegbar: %s (installiert: %s)", latest, current)
        text = f"Neue Version {latest.lstrip('vV')} verfügbar (installiert: {current})"
        js = """(() => {
  if (document.getElementById('bdx-update')) return;
  const b = document.createElement('div');
  b.id = 'bdx-update';
  b.style.cssText = 'position:fixed;left:50%%;bottom:16px;transform:translateX(-50%%);z-index:99999;'
    + 'background:#1f2937;color:#fff;padding:10px 14px;border-radius:10px;box-shadow:0 4px 18px rgba(0,0,0,.35);'
    + 'font:14px system-ui,sans-serif;display:flex;gap:12px;align-items:center;max-width:calc(100%% - 32px)';
  const t = document.createElement('span'); t.textContent = %s;
  const a = document.createElement('a'); a.textContent = 'Herunterladen'; a.href = %s; a.target = '_blank';
  a.style.cssText = 'color:#fbbf24;font-weight:600';
  const x = document.createElement('button'); x.textContent = '✕'; x.title = 'Schließen';
  x.style.cssText = 'background:none;border:0;color:#fff;cursor:pointer;font-size:15px';
  x.onclick = () => b.remove();
  b.append(t, a, x); document.body.appendChild(b);
})();""" % (json.dumps(text), json.dumps(url))
        window.evaluate_js(js)
    except Exception as e:  # noqa: BLE001  (offline o. ae. ist kein Fehler)
        log.info("Update-Pruefung uebersprungen: %s", e)


# ---------------------------------------------------------------- Start

ERROR_HTML = """<!doctype html><meta charset="utf-8"><title>Ninedex</title>
<body style="font:15px system-ui,sans-serif;padding:32px;max-width:640px">
<h2>Ninedex konnte nicht starten</h2><p>%s</p>
<p>Details stehen in der Protokolldatei:<br><code>%s</code></p></body>"""


def main():
    ddir = data_dir()
    logfile = setup_logging(ddir)
    version = app_version()
    log.info("Ninedex %s startet, Datenordner: %s", version, ddir)

    import webview  # erst hier, damit Fehler im Log landen

    inst = SingleInstance(ddir)
    if not inst.acquire():
        if inst.focus_running():
            return 0
        log.warning("Sperre belegt, aber keine Instanz erreichbar. Starte trotzdem.")

    # Sprachauswahl aus dem Windows-Installer (ninedex.ini neben dem Programm), z. B. "en,de":
    # die erste ist die Startsprache. app.py uebernimmt sie, sobald sie sich aendert; ohne Datei
    # (macOS, Entwicklung) fragt die App beim ersten Start selbst.
    langs = installer_langs()
    if langs and not env("LANGS"):
        os.environ["NINEDEX_LANGS"] = langs
        log.info("Sprachen aus dem Installer: %s", langs)

    # Datenbank liegt im Datenordner, relative Dateien landen ebenfalls dort
    os.environ.setdefault("DB_PATH", os.path.join(ddir, "pokedex.db"))
    os.chdir(ddir)
    sys.path.insert(0, resource_dir())

    window_ref = {}
    try:
        import app as backend
        backend.startup()

        @backend.app.get("/__desktop/focus")
        def _desktop_focus():
            w = window_ref.get("w")
            if w:
                try:
                    w.restore()
                    w.show()
                    w.on_top = True
                    w.on_top = False
                except Exception as e:  # noqa: BLE001
                    log.warning("Fenster nach vorn holen fehlgeschlagen: %s", e)
            return "ok"

        server = make_server(backend.app)
    except Exception as e:  # noqa: BLE001
        log.exception("Start fehlgeschlagen")
        webview.create_window(APP_NAME, html=ERROR_HTML % (str(e).replace("<", "&lt;"), logfile), width=720, height=420)
        webview.start()
        return 1

    port = server.server_port
    inst.write_port(port)
    threading.Thread(target=server.serve_forever, name="flask", daemon=True).start()
    log.info("Backend laeuft auf http://%s:%s", HOST, port)

    webview.settings["ALLOW_DOWNLOADS"] = True              # Backup, Excel-, CSV-Export
    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True  # Cardmarket-Links, Verkaufsseite
    window = webview.create_window(
        f"{APP_NAME}", f"http://{HOST}:{port}/",
        width=1320, height=880, min_size=(900, 600),
        text_select=True, background_color="#1a1a1a",
    )
    window_ref["w"] = window

    def on_started():
        window.events.loaded.wait(30)
        check_update(window, version)

    # Kein eigenes Fenstersymbol uebergeben: Windows (WinForms) akzeptiert dort nur .ico und stuerzt bei
    # einer PNG-Datei ohne Python-Fehlermeldung ab. Windows nimmt das Symbol der .exe, macOS das der .app.
    try:
        webview.start(
            on_started,
            private_mode=False,  # Einstellungen der Oberflaeche (localStorage) behalten
            storage_path=os.path.join(ddir, "webview"),
            debug=bool(env("DEBUG")),
        )
    finally:
        log.info("Fenster geschlossen, beende Backend")
        server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
