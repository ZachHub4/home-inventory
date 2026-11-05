# Home Inventory

A self-hosted web app for logging everything stored around the house. Print a QR
label for each storage bin, stick it on, then scan it with your phone to see or
update what's inside.

## Features

- **Bins** with names, locations, and auto-generated codes (`BIN-XXXXXX`)
- **Printable QR labels** — one per bin, generated on the fly
- **QR scanner** — point your phone camera at a label to jump straight to that bin
- **Items** with quantity, description, and an optional photo
- **Photos** are re-encoded to JPEG, capped at 1400px, with 400px thumbnails
- **Search** across all items and bins
- **Installable** — add it to your phone's home screen and it runs fullscreen

## Requirements

Python 3.11+. No Node, no build step.

## Setup

```bash
python -m venv venv
venv/Scripts/pip install -r requirements.txt   # Windows
# source venv/bin/activate && pip install -r requirements.txt   # macOS/Linux
```

## Running

```bash
venv/Scripts/python app.py
```

Then open <http://localhost:5000>.

The database (`inventory.db`) and uploaded photos (`static/uploads/`) are created
automatically on first run. Both are gitignored — your inventory stays local.

## Using it from your phone

The app listens on `0.0.0.0`, so any device on the same WiFi can reach it:

1. Find your computer's local IP (`ipconfig` on Windows, `ifconfig` on macOS/Linux)
2. On your phone, visit `http://<that-ip>:5000`
3. In Safari or Chrome, use **Share → Add to Home Screen** for an app icon

You may need to allow Python through your firewall for other devices to connect.

## HTTPS (required for QR scanning)

Browsers only expose the camera and service workers in a **secure context**.
Over plain HTTP on a LAN address, `navigator.mediaDevices` is undefined entirely,
so the scanner cannot start — the app falls back to manual bin-code entry.

To enable scanning, serve the app over HTTPS with a local certificate authority.
Nothing is exposed to the internet; the CA exists only on your machine.

### 1. Generate the certificates

```bash
./scripts/make-certs.sh 192.168.4.25    # your computer's LAN IP
```

This creates `certs/`, containing a CA (valid 10 years) and a server certificate
for that IP (820 days, within the 825-day limit iOS enforces). The whole folder
is gitignored — the CA private key must never leave the machine.

Reserve that IP for your computer in your router's DHCP settings. The server
certificate is issued *for that address*, so a changed IP breaks it. If the IP
does change, re-run the script: the CA is reused, so already-trusted devices keep
working and only the server certificate is replaced.

### 2. Trust the CA on your phone

`app.py` now serves HTTPS, which your phone won't trust yet — so hand over the CA
certificate using the setup-only helper (it serves that one file and nothing else;
never point a directory server at `certs/`):

```bash
python scripts/serve-ca.py
```

On the phone, open the URL it prints, then:

- **iOS**: Settings → Profile Downloaded → Install. Then
  Settings → General → About → Certificate Trust Settings → enable full trust.
  Both steps are required; installing alone is not enough.
- **Android**: Settings → Security → Install from storage → CA certificate.

Stop the helper with Ctrl+C once installed.

### 3. Use HTTPS

Visit `https://192.168.4.25:5000`. Scanning, offline caching, and Add to Home
Screen all work from here.

## Public demo mode

Set the environment variable `HOME_INVENTORY_DEMO=1` to run a version that's
safe to share publicly. It's off by default, so the self-hosted app is unchanged.

In demo mode the app:

- starts with sample bins and items, and **wipes and re-seeds itself every 24 hours**
  (checked on each request, so no scheduled task is needed)
- turns off photo uploads and backup restores, so strangers can't put files on the server
- caps bins (40), items (300), field length and request size so it can't be flooded
- shows a banner on every page saying it's a demo, with a link back to this repo

The sample bins use fixed codes (`BIN-E1EC74` is "Tools - Electrical"), so a printed
demo label keeps working after every reset.

### Deploying the demo to PythonAnywhere

A free PythonAnywhere account hosts one web app at `https://<username>.pythonanywhere.com`
with HTTPS included, which is what the camera scanner needs. Pick your username with
that in mind.

1. **Bash console:** open *Consoles → Bash* and run:
   ```bash
   git clone https://github.com/ZachHub4/home-inventory.git
   python3.12 -m venv ~/venv
   ~/venv/bin/pip install -r ~/home-inventory/requirements.txt
   ```
   Use the same Python version (`3.12` here) in step 2.
2. **Web tab:** *Add a new web app → Manual configuration → Python 3.12*.
3. On the web app's page, set:
   - **Source code:** `/home/<username>/home-inventory`
   - **Virtualenv:** `/home/<username>/venv`
   - **Static files:** URL `/static/` → directory `/home/<username>/home-inventory/static`
   - **Force HTTPS:** on
4. Click the **WSGI configuration file** link, replace its contents with this, and save:
   ```python
   import os
   import sys

   os.environ["HOME_INVENTORY_DEMO"] = "1"

   path = "/home/<username>/home-inventory"
   if path not in sys.path:
       sys.path.insert(0, path)

   from app import app as application
   ```
5. Click **Reload** and open your site.

To update the demo later: `cd ~/home-inventory && git pull` in a Bash console, then **Reload**.

Free web apps are switched off after a month unless you log in and click
**Run until 1 month from today** on the Web tab. The barcode product lookup may
not work on the free tier, which limits outbound internet access; the app shows a
"lookup failed" message and the rest works normally.

## Workflow

1. Create a bin, give it a name and location
2. Print its QR label and stick it on the bin
3. Scan the label any time to see or add contents

## Layout

| Path | Purpose |
|---|---|
| `app.py` | Routes, QR generation, photo processing |
| `db.py` | SQLite connection and migrations |
| `demo.py` | Public demo mode: sample data, daily reset, limits |
| `schema.sql` | Table definitions |
| `templates/` | Jinja2 pages |
| `static/` | CSS, JS, icons, uploaded photos |
