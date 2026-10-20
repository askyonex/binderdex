#!/usr/bin/env bash
# Packt dist/BinderDex.app in ein DMG mit Verknuepfung zum Programme-Ordner (nur macOS).
#   bash desktop/make_dmg.sh 1.0.0 arm64     ->  dist/BinderDex-1.0.0-macOS-arm64.dmg
set -euo pipefail

VERSION="${1:?Version fehlt, z. B. 1.0.0}"
ARCH="${2:-$(uname -m)}"
APP="dist/BinderDex.app"
OUT="dist/BinderDex-${VERSION}-macOS-${ARCH}.dmg"
STAGE="$(mktemp -d)/BinderDex"

[ -d "$APP" ] || { echo "Nicht gefunden: $APP (erst PyInstaller ausfuehren)"; exit 1; }

# Ohne Apple-Entwicklerkonto: "ad-hoc" signieren. Unsignierte Apps meldet macOS als "beschaedigt",
# ad-hoc signierte lassen sich ueber Systemeinstellungen > Datenschutz & Sicherheit > "Dennoch oeffnen" starten.
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP"

mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
rm -f "$OUT"
hdiutil create -volname "BinderDex ${VERSION}" -srcfolder "$STAGE" -ov -format UDZO "$OUT"
echo "Fertig: $OUT"
