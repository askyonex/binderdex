# Self-hosting

Ninedex needs very little: a Raspberry Pi 4 (2 GB is enough), a mini PC, a NAS with Docker or any always-on computer. The text recognition runs in the browser, the server only does light work.

## 1. Run it locally (no Docker)

```bash
pip install -r requirements.txt
python app.py                # http://localhost:5000
```

Environment variables: `DB_PATH` (database file), `HOST` (`127.0.0.1` or `0.0.0.0`), `PORT`. For example `HOST=0.0.0.0 python app.py` makes it reachable from other devices in your network.

## 2. Docker

```bash
docker compose up -d --build        # http://localhost:5000, data in ./data
```

The compose file only publishes the port on `127.0.0.1`. To use the app from other devices change `"127.0.0.1:5000:5000"` to `"5000:5000"`. **There is no login, never expose the port to the internet.**

## 3. Raspberry Pi

1. Install a 64-bit Raspberry Pi OS, then Docker: `curl -fsSL https://get.docker.com | sh` and `sudo usermod -aG docker $USER` (log in again).
2. `git clone https://github.com/askyonex/ninedex.git && cd ninedex`
3. `docker compose up -d --build`

The container restarts automatically after a reboot (`restart: unless-stopped`).

Note: the Docker image installs `openpyxl` and `pillow` (from `requirements.txt`) for the Excel export. Without them everything else works and only the *Excel mit Bildern* button reports the missing packages.

## 4. HTTPS (required for the camera on phones and other computers)

Browsers only allow camera access on `https://` pages or on `localhost`. A simple way at home is Caddy with its own small certificate authority.

1. **DNS name:** create a local DNS record that points a name such as `ninedex.home.arpa` to the IP of your server (router, Pi-hole, AdGuard Home ...). Do not use `.local`.
2. **Caddy:** copy `docs/examples/docker-compose.https.yml` and `docs/examples/Caddyfile.example` next to the Dockerfile (rename the second to `Caddyfile`, adjust the name) and start `docker compose -f docker-compose.https.yml up -d --build`.
3. **Trust the certificate on every device.** Export the root certificate:
   ```bash
   docker compose -f docker-compose.https.yml exec caddy cat /data/caddy/pki/authorities/local/root.crt > caddy-root.crt
   ```
   Hand out **only `root.crt`, never `root.key`.**
   - **iPhone / iPad:** open the file in *Safari* (for example via AirDrop or a temporary `python3 -m http.server` in the folder), allow the profile, install it in *Settings*, then enable it under *Settings > General > About > Certificate Trust Settings*.
   - **Android:** *Settings > Security > Encryption & credentials > Install a certificate > CA certificate*.
   - **macOS:** double-click, add to Keychain, set to *Always Trust*.
   - **Windows:** double-click, *Install Certificate*, store in *Trusted Root Certification Authorities* (local computer), restart the browser.
4. Open `https://ninedex.home.arpa`. No warning should appear.

Keep the `caddy_data` volume in your backups. If it is lost, Caddy creates a new certificate authority and the certificate has to be installed on all devices again.

**iPhone and "site cannot be reached":** if the router hands out its own IPv6 DNS server, iOS may ask it instead of your local DNS and fail to resolve the name. In *Settings > Wi-Fi > (i) > Configure DNS > Manual* enter only your local DNS server.

## 5. Install as a home-screen app

Open the HTTPS address in **Safari** on the iPhone, tap *Share > Add to Home Screen*. The app opens full screen with its own icon. (On Android: browser menu > *Install app* / *Add to Home screen*.) The camera permission may be asked on every start; that is iOS behavior. It only works inside your network unless you add a VPN.

## 6. Backups

Your whole collection is one SQLite file (`data/pokedex.db`). Three ways to back it up:

- **In the app:** *Statistik > Datenbank sichern* downloads a consistent copy.
- **Script:** `scripts/backup.sh` creates a daily backup (safe while the app runs) and optionally copies it to a mounted network share. Example cron job (daily 03:15):
  ```
  15 3 * * * DB_FILE=/home/pi/ninedex/data/pokedex.db BACKUP_DIR=/home/pi/ninedex/backups /home/pi/ninedex/scripts/backup.sh
  ```
  For a NAS share add `NAS_MOUNT=/mnt/nas` (and mount it, for example with an `/etc/fstab` entry using `cifs` and `credentials=`). If the share is mounted by root, run the cron job as root.
- **Restore:** stop the app, copy a backup over `data/pokedex.db`, start the app.

## 7. Updating

```bash
git pull
docker compose up -d --build
```

Database changes are applied automatically at startup. On the first start after an update the app may fill in new data (prices, images, categories) in the background; the header shows progress.

## 8. Merging two databases

If two copies of the database drifted apart (for example a test copy on your PC), merge them into a copy of the main one:

```bash
python merge_db.py source.db target.db            # preview
python merge_db.py source.db target.db --apply    # writes into target.db after making a backup
```

## 9. Troubleshooting

| Problem | Solution |
| --- | --- |
| Camera does not start | Needs HTTPS or `localhost` (section 4). Check the browser's camera permission |
| Browser says "site not reachable" | DNS name does not resolve on that device (section 4, iPhone note) |
| Certificate warning | Root certificate not installed or not trusted on that device |
| Prices show "–" | Click *Preise aktualisieren*. Check one card: `/api/pricecheck?lang=de&id=<card id>` |
| Cards without images | `/api/imgcheck?lang=ja&set=<set id>` shows whether the fallback source knows the set |
| A set is missing in the Sets view | `/api/seriesdebug?lang=ja` lists the series and whether they were included |
| "database is locked" | Rare with several users; the app waits up to 30 seconds. Make sure only one app instance uses the file |
| Old version after an update | Reload with Ctrl+F5; for the home-screen app remove it and add it again |

## 10. Security checklist

- No login: keep it in your home network or behind your own authentication.
- Do not publish your `pokedex.db` or Caddy's `root.key`.
- The app contacts TCGdex, PokeAPI and tcgcsv.com from the server, and your browser loads fonts from Google Fonts and Tesseract.js from jsDelivr.
