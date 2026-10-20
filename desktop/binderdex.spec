# PyInstaller-Bauplan fuer die BinderDex-Desktop-App (Windows und macOS).
# Aufruf aus dem Repo-Ordner:  pyinstaller desktop/binderdex.spec --noconfirm
# Ergebnis:  dist/BinderDex/ (Windows-Programmordner)  bzw.  dist/BinderDex.app (macOS)
import os
import sys

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
BUILD = os.path.join(ROOT, "desktop", "build")
with open(os.path.join(ROOT, "VERSION"), encoding="utf-8") as f:
    VERSION = f.read().strip()

a = Analysis(
    [os.path.join(ROOT, "desktop", "binderdex_desktop.py")],
    pathex=[ROOT],  # damit "import app" das Backend findet
    datas=[
        (os.path.join(ROOT, "static"), "static"),
        (os.path.join(ROOT, "VERSION"), "."),
    ],
    hiddenimports=["app", "openpyxl", "PIL.Image"],
    excludes=["tkinter", "PyQt5", "PyQt6", "PySide2", "PySide6", "gi", "cefpython3"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BinderDex",
    console=False,  # kein schwarzes Konsolenfenster
    icon=os.path.join(BUILD, "icon.ico" if sys.platform == "win32" else "icon.icns"),
    upx=False,
)

coll = COLLECT(exe, a.binaries, a.datas, name="BinderDex", upx=False)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="BinderDex.app",
        icon=os.path.join(BUILD, "icon.icns"),
        bundle_identifier="io.github.askyonex.binderdex",
        version=VERSION,
        info_plist={
            "CFBundleDisplayName": "BinderDex",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
            "LSApplicationCategoryType": "public.app-category.utilities",
            # Ohne diese Texte darf macOS der App keinen Kamerazugriff geben (Karten-Scan)
            "NSCameraUsageDescription": "BinderDex nutzt die Kamera, um Kartennummern zu scannen.",
            "NSMicrophoneUsageDescription": "BinderDex nimmt keinen Ton auf. Die Kamera-Abfrage des Systems kann trotzdem nach dem Mikrofon fragen.",
        },
    )
