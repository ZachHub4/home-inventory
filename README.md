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

## Workflow

1. Create a bin, give it a name and location
2. Print its QR label and stick it on the bin
3. Scan the label any time to see or add contents

## Layout

| Path | Purpose |
|---|---|
| `app.py` | Routes, QR generation, photo processing |
| `db.py` | SQLite connection and migrations |
| `schema.sql` | Table definitions |
| `templates/` | Jinja2 pages |
| `static/` | CSS, JS, icons, uploaded photos |
