"""Public demo mode.

Turn it on by setting the environment variable HOME_INVENTORY_DEMO=1. The
normal self-hosted app is unchanged when it is off.

In demo mode:
- the database is filled with sample bins and items
- it is wiped and re-seeded automatically every RESET_HOURS, so one visitor
  can't leave a mess for the next
- photo uploads and backup restores are switched off (no strangers' files on
  the server)
- bins, items and request sizes are capped so the demo can't be flooded
- a banner on every page says it's a demo
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

from flask import render_template, request

ENABLED = os.environ.get("HOME_INVENTORY_DEMO") == "1"

RESET_HOURS = 24
MAX_BINS = 40
MAX_ITEMS = 300
MAX_REQUEST_BYTES = 64 * 1024
MAX_FIELD_CHARS = 200

STAMP_FILE = Path(__file__).parent / ".demo_reset_at"

# (location, bin name, notes, printed?, [(item, qty, description), ...])
SAMPLE_BINS = [
    ("Garage", "Holiday Decorations", "Top shelf, left side", True, [
        ("String lights", 6, "Warm white, 100-bulb strands"),
        ("Ornaments", 112, "Glass ones are in the egg cartons"),
        ("Tree skirt", 1, "Red plaid"),
        ("Extension cords", 3, "Outdoor rated"),
    ]),
    ("Garage", "Car Care", "Under the workbench", True, [
        ("Microfiber towels", 12, ""),
        ("Tire pressure gauge", 1, "Digital"),
        ("Jumper cables", 1, "10 ft"),
        ("Windshield washer fluid", 2, "Winter mix"),
    ]),
    ("Garage", "Camping Gear", "", False, [
        ("Tent stakes", 24, "Spare set for the 4-person tent"),
        ("Headlamps", 3, "Take AAA batteries"),
        ("Camp stove", 1, "Propane, with windscreen"),
        ("Collapsible water jug", 1, "5 gallon"),
    ]),
    ("Basement", "Tools - Electrical", "Blue tote", True, [
        ("Voltage tester", 1, "Non-contact pen style"),
        ("Wire strippers", 1, ""),
        ("Wire nuts", 60, "Assorted sizes"),
        ("Electrical tape", 4, "Black"),
        ("Zip ties", 200, "8 inch"),
    ]),
    ("Basement", "Network Spares", "Shelf by the router", True, [
        ("Ethernet cables", 8, "Cat6, assorted lengths"),
        ("RJ45 connectors", 50, ""),
        ("Crimping tool", 1, ""),
        ("Old router", 1, "Backup if the main one dies"),
    ]),
    ("Basement", "Kids' Old Clothes", "Sizes 4T-6", False, [
        ("Winter coats", 2, ""),
        ("Rain boots", 3, "Pairs"),
        ("Halloween costumes", 4, "Dinosaur, pirate, astronaut, firefighter"),
    ]),
    ("Hall Closet", "Batteries & Bulbs", "", True, [
        ("AA batteries", 24, ""),
        ("AAA batteries", 16, ""),
        ("9V batteries", 2, "Smoke detectors"),
        ("LED bulbs", 6, "60W equivalent, soft white"),
    ]),
    ("Hall Closet", "First Aid", "Top shelf", True, [
        ("Adhesive bandages", 80, "Assorted"),
        ("Gauze pads", 20, ""),
        ("Instant cold packs", 4, ""),
        ("Thermometer", 1, "Digital"),
    ]),
    ("Attic", "Baseball Cards", "Keep out of the heat in summer", False, [
        ("Card binders", 3, "Sorted by team"),
        ("Toploaders", 150, ""),
        ("Unopened packs", 6, ""),
    ]),
    ("Attic", "Important Papers", "Fireproof box", True, [
        ("Appliance manuals", 14, "Washer, dryer, furnace, etc."),
        ("Warranty cards", 9, ""),
    ]),
]

# Fixed codes so screenshots and printed demo labels stay valid across resets.
SAMPLE_CODES = [
    "BIN-D3C0R8", "BIN-CA4C4R", "BIN-CA3P01", "BIN-E1EC74", "BIN-2E7A55",
    "BIN-C107E5", "BIN-BA77E2", "BIN-F1A1D0", "BIN-CA2D55", "BIN-PA9E25",
]


def seed(conn):
    """Replace everything with the sample inventory."""
    conn.execute("DELETE FROM items")
    conn.execute("DELETE FROM bins")
    conn.execute("DELETE FROM locations")

    printed_stamp = datetime.now().isoformat(timespec="seconds")
    location_ids = {}
    for code, (location, name, notes, printed, items) in zip(SAMPLE_CODES, SAMPLE_BINS):
        if location not in location_ids:
            location_ids[location] = conn.execute(
                "INSERT INTO locations (name) VALUES (?)", (location,)
            ).lastrowid
        bin_id = conn.execute(
            """INSERT INTO bins (code, name, location_id, notes, printed_at)
               VALUES (?, ?, ?, ?, ?)""",
            (code, name, location_ids[location], notes, printed_stamp if printed else None),
        ).lastrowid
        conn.executemany(
            "INSERT INTO items (bin_id, name, quantity, description) VALUES (?, ?, ?, ?)",
            [(bin_id, item, qty, desc) for item, qty, desc in items],
        )
    conn.commit()
    STAMP_FILE.write_text(datetime.now().isoformat(timespec="seconds"))


def reset_due():
    try:
        last = datetime.fromisoformat(STAMP_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        return True
    return datetime.now() - last >= timedelta(hours=RESET_HOURS)


def blocked(message, status=403):
    return (
        render_template(
            "backup_result.html", ok=False, heading="Not available in the demo", message=message
        ),
        status,
    )


def init_app(app, db):
    """Wire demo behaviour into the app. Does nothing unless demo mode is on."""

    @app.context_processor
    def inject_demo():
        return {"demo": ENABLED, "demo_reset_hours": RESET_HOURS}

    if not ENABLED:
        return

    app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES

    @app.before_request
    def demo_guard():
        conn = db.get_db()
        if reset_due():
            seed(conn)

        if request.method != "POST":
            return None

        if request.endpoint == "import_backup":
            return blocked("Restoring backups is turned off in the demo.")

        if request.files and any(f.filename for f in request.files.values()):
            return blocked("Photo uploads are turned off in the demo.")

        # The bulk "dictate" box holds many lines, so it gets more room.
        too_long = any(
            len(value) > (MAX_FIELD_CHARS * 10 if key == "text" else MAX_FIELD_CHARS)
            for key, value in request.form.items(multi=True)
        )
        if too_long:
            return blocked(f"Keep entries under {MAX_FIELD_CHARS} characters in the demo.", 400)

        if request.endpoint == "new_bin":
            count = conn.execute("SELECT COUNT(*) FROM bins").fetchone()[0]
            if count >= MAX_BINS:
                return blocked("The demo is full of bins right now. It resets daily.")

        if request.endpoint in ("add_item", "bulk_confirm"):
            count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
            adding = len(request.form.getlist("keep")) or 1
            if count + adding > MAX_ITEMS:
                return blocked("The demo is full of items right now. It resets daily.")

        return None
