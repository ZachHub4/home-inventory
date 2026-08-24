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

### Note on offline support

The service worker only registers over HTTPS (or on `localhost`). Over plain HTTP
on a local network, the app still installs to the home screen and runs fullscreen,
but offline caching is inactive until it's served over HTTPS.

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
