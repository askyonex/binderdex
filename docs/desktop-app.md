# Desktop app (Windows / macOS)

Deutsch: [desktop-app.de.md](desktop-app.de.md)

The desktop app is the normal Ninedex web app in its own window. The Flask backend runs invisibly in the background and only listens on `127.0.0.1`, so nobody else on your network can reach it. Windows uses the Microsoft Edge WebView2 engine, macOS uses WebKit (Safari's engine).

## Install

Download from the [latest release](https://github.com/askyonex/ninedex/releases/latest), see the table in the [README](../README.md#download-desktop-app-windows--macos).

- **Windows 10 / 11:** run `Ninedex-Setup-x.y.z.exe` (setup in German, English or Spanish). By default it installs for your user only (no admin rights). The installer asks which **app languages** you want (German, English, Spanish, several possible) and which one to start in, offers a desktop shortcut and starts the app at the end. Running the installer again (for an update) suggests your previous choice.
  - *"Windows protected your PC"* (SmartScreen) appears because the app is not code-signed: **More info → Run anyway**.
  - WebView2 is part of Windows 11 and current Windows 10. If it is missing, the installer offers to open Microsoft's download page.
- **macOS 11 or newer:** open the DMG and drag Ninedex onto *Applications*.
  - First start: macOS says the app *cannot be checked for malware*. Open **System Settings → Privacy & Security**, scroll to the message about Ninedex and click **Open Anyway**, then confirm. Only needed once per version.
  - Alternative in the Terminal: `xattr -dr com.apple.quarantine /Applications/Ninedex.app`
  - Apple Silicon (M1 and newer) uses the `arm64` DMG, Intel Macs the `x86_64` DMG.

## Where your data lives

| System | Folder |
| ------ | ------ |
| Windows | `%APPDATA%\Ninedex` (paste into the Explorer address bar) |
| macOS | `~/Library/Application Support/Ninedex` (Finder: *Go → Go to Folder…*) |

The folder contains `pokedex.db` (your whole collection), `ninedex.log` (log file, useful for bug reports) and `webview/` (UI settings like theme and sounds).

- **Updates** keep the folder. When a new version is out, the app shows a hint with **Update now**: it downloads the new version, checks its SHA-256 checksum against the release and installs it (Windows: the installer runs silently and keeps your language choice; macOS: the app is replaced), then Ninedex restarts. You can still install a downloaded version over the old one by hand.
- **Uninstalling on Windows** asks whether to keep the folder (default: keep).
- **Backup:** the backup button in the app downloads a copy of the database, or copy `pokedex.db` while the app is closed.
- **Moving from the web version:** close the app, replace `pokedex.db` in the folder with your existing database, start the app again.
- Own folder (e.g. on a NAS or in a synced folder): set the environment variable `NINEDEX_DATA_DIR`.

## Good to know

- **Language:** switch in *Settings → Language*, add or remove languages with the **…** button next to it. On macOS the app asks for the languages on the first start. Details: [translating.md](translating.md)
- **Camera scan** works with the webcam. Windows and macOS ask for permission the first time.
- **Links** (Cardmarket, release page) and the printable **sales page** open in your normal browser. The sales page works there as long as the app is running.
- **Downloads** (backup, Excel, CSV) open a save dialog.
- Starting the app a second time just brings the open window to the front.
- The app checks GitHub once per start for a newer release and shows a small hint (see *Updates* above). Nothing else is sent. Turn it off with `NINEDEX_NO_UPDATE_CHECK=1`. On macOS the in-app update needs write access to the app (normally given in *Applications*); otherwise it opens the DMG so you can replace the app yourself.
- The app uses the fixed local port `47821` (so UI settings survive restarts). If another program uses it, a free port is used for that session.
- **Phone access** is not part of the desktop app. For that, run Ninedex on a server or Raspberry Pi ([self-hosting.md](self-hosting.md)).
- **AI camera help** (Ollama) is still installed separately, see [ai-scan.md](ai-scan.md).

## For developers: run, build, release

Run from source (in the repo folder):

```bash
pip install -r requirements.txt -r desktop/requirements-desktop.txt
python desktop/ninedex_desktop.py          # NINEDEX_DEBUG=1 enables the dev tools
```

| File | Purpose |
| ---- | ------- |
| `desktop/ninedex_desktop.py` | Launcher: data folder, backend thread, window, single instance, update check and in-app update |
| `desktop/ninedex.spec` | PyInstaller build (Windows program folder / macOS `.app` with camera permission text) |
| `desktop/make_icons.py` | Builds `icon.ico` / `icon.icns` from `static/icon-512.png` |
| `desktop/installer/ninedex.iss` | Inno Setup script for the Windows installer |
| `desktop/make_dmg.sh` | Ad-hoc signs the `.app` and packs the DMG |
| `desktop/build_windows.bat` | Local Windows build for testing |
| `.github/workflows/desktop-release.yml` | Builds everything on GitHub and attaches it to the release |

**Release:** set the version in `VERSION`, commit, then tag and push:

```bash
git tag v1.0.1
git push origin v1.0.1
```

GitHub Actions builds the Windows installer and both macOS DMGs (about 10 to 15 minutes) and publishes them with a `SHA256SUMS.txt` in the release *v1.0.1*. The tag decides the version number in the builds. A test build without a release: *Actions → Desktop release → Run workflow*; the files are then under *Artifacts* of that run.

**Code signing** (optional, removes the warnings): Windows, e.g. Azure Trusted Signing or a code-signing certificate; macOS needs an Apple Developer account (99 USD per year) for signing and notarization. Both can be added to the workflow later.
