"""Erzeugt die App-Symbole fuer den Build aus static/icon-512.png.

    python desktop/make_icons.py
    -> desktop/build/icon.ico   (Windows: Programm und Installer)
    -> desktop/build/icon.icns  (macOS: App-Bundle)
"""
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "static", "icon-512.png")
OUT = os.path.join(ROOT, "desktop", "build")


def main():
    os.makedirs(OUT, exist_ok=True)
    im = Image.open(SRC).convert("RGBA")
    if im.size != (512, 512):
        im = im.resize((512, 512), Image.LANCZOS)
    im.save(os.path.join(OUT, "icon.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    im.resize((1024, 1024), Image.LANCZOS).save(os.path.join(OUT, "icon.icns"))
    print("Symbole erzeugt in", OUT)


if __name__ == "__main__":
    main()
