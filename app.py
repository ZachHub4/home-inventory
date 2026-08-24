import io
import secrets
from pathlib import Path

import qrcode
from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from PIL import Image, ImageOps, UnidentifiedImageError

import db

UPLOAD_DIR = Path(__file__).parent / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_PHOTO_DIM = 1400
THUMB_DIM = 400

app = Flask(__name__)
app.config["DATABASE"] = str(Path(__file__).parent / "inventory.db")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
db.init_app(app)

with app.app_context():
    db.init_db()


def save_photo(file_storage):
    """Re-encode an uploaded image to JPEG. Returns the stored filename, or None."""
    if not file_storage or not file_storage.filename:
        return None
    try:
        img = Image.open(file_storage.stream)
        img = ImageOps.exif_transpose(img)
    except (UnidentifiedImageError, OSError, ValueError):
        return None

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    name = secrets.token_hex(8)
    full = img.copy()
    full.thumbnail((MAX_PHOTO_DIM, MAX_PHOTO_DIM))
    full.save(UPLOAD_DIR / f"{name}.jpg", "JPEG", quality=85)

    thumb = img.copy()
    thumb.thumbnail((THUMB_DIM, THUMB_DIM))
    thumb.save(UPLOAD_DIR / f"{name}_thumb.jpg", "JPEG", quality=80)

    return f"{name}.jpg"


def delete_photo(name):
    if not name:
        return
    stem = Path(name).stem
    for path in (UPLOAD_DIR / f"{stem}.jpg", UPLOAD_DIR / f"{stem}_thumb.jpg"):
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def generate_bin_code(conn):
    while True:
        code = "BIN-" + secrets.token_hex(3).upper()
        exists = conn.execute("SELECT 1 FROM bins WHERE code = ?", (code,)).fetchone()
        if not exists:
            return code


def get_bin_or_404(conn, code):
    row = conn.execute(
        """SELECT bins.*, locations.name AS location_name
           FROM bins LEFT JOIN locations ON bins.location_id = locations.id
           WHERE code = ?""",
        (code,),
    ).fetchone()
    if row is None:
        abort(404)
    return row


@app.route("/")
def index():
    conn = db.get_db()
    bins = conn.execute(
        """SELECT bins.*, locations.name AS location_name,
                  (SELECT COUNT(*) FROM items WHERE items.bin_id = bins.id) AS item_count
           FROM bins LEFT JOIN locations ON bins.location_id = locations.id
           ORDER BY location_name IS NULL, location_name, bins.name"""
    ).fetchall()
    return render_template("index.html", bins=bins)


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    items, bins = [], []
    if q:
        like = f"%{q}%"
        conn = db.get_db()
        items = conn.execute(
            """SELECT items.*, bins.code AS bin_code, bins.name AS bin_name
               FROM items JOIN bins ON items.bin_id = bins.id
               WHERE items.name LIKE ? OR items.description LIKE ?
               ORDER BY items.name""",
            (like, like),
        ).fetchall()
        bins = conn.execute(
            "SELECT * FROM bins WHERE name LIKE ? OR code LIKE ? ORDER BY name",
            (like, like),
        ).fetchall()
    return render_template("search.html", q=q, items=items, bins=bins)


@app.route("/bins/new", methods=["GET", "POST"])
def new_bin():
    conn = db.get_db()
    if request.method == "POST":
        name = request.form["name"].strip()
        location_name = request.form.get("location", "").strip()
        notes = request.form.get("notes", "").strip()
        if not name:
            abort(400, "Bin name is required")

        location_id = None
        if location_name:
            row = conn.execute(
                "SELECT id FROM locations WHERE name = ?", (location_name,)
            ).fetchone()
            if row:
                location_id = row["id"]
            else:
                cur = conn.execute(
                    "INSERT INTO locations (name) VALUES (?)", (location_name,)
                )
                location_id = cur.lastrowid

        code = generate_bin_code(conn)
        conn.execute(
            "INSERT INTO bins (code, name, location_id, notes) VALUES (?, ?, ?, ?)",
            (code, name, location_id, notes),
        )
        conn.commit()
        return redirect(url_for("bin_label", code=code))

    locations = conn.execute("SELECT name FROM locations ORDER BY name").fetchall()
    return render_template("new_bin.html", locations=locations)


@app.route("/bin/<code>")
def bin_detail(code):
    conn = db.get_db()
    bin_row = get_bin_or_404(conn, code)
    items = conn.execute(
        "SELECT * FROM items WHERE bin_id = ? ORDER BY name", (bin_row["id"],)
    ).fetchall()
    return render_template("bin_detail.html", bin=bin_row, items=items)


@app.route("/bin/<code>/items", methods=["POST"])
def add_item(code):
    conn = db.get_db()
    bin_row = get_bin_or_404(conn, code)
    name = request.form["name"].strip()
    if not name:
        abort(400, "Item name is required")
    try:
        quantity = max(1, int(request.form.get("quantity") or 1))
    except ValueError:
        quantity = 1
    description = request.form.get("description", "").strip()
    photo = save_photo(request.files.get("photo"))
    conn.execute(
        """INSERT INTO items (bin_id, name, quantity, description, photo)
           VALUES (?, ?, ?, ?, ?)""",
        (bin_row["id"], name, quantity, description, photo),
    )
    conn.commit()
    return redirect(url_for("bin_detail", code=code))


@app.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
def edit_item(item_id):
    conn = db.get_db()
    item = conn.execute(
        """SELECT items.*, bins.code AS bin_code
           FROM items JOIN bins ON items.bin_id = bins.id
           WHERE items.id = ?""",
        (item_id,),
    ).fetchone()
    if item is None:
        abort(404)

    if request.method == "POST":
        name = request.form["name"].strip()
        if not name:
            abort(400, "Item name is required")
        try:
            quantity = max(1, int(request.form.get("quantity") or 1))
        except ValueError:
            quantity = 1
        description = request.form.get("description", "").strip()

        photo = item["photo"]
        if request.form.get("remove_photo"):
            delete_photo(photo)
            photo = None
        new_photo = save_photo(request.files.get("photo"))
        if new_photo:
            delete_photo(photo)
            photo = new_photo

        conn.execute(
            """UPDATE items SET name = ?, quantity = ?, description = ?, photo = ?
               WHERE id = ?""",
            (name, quantity, description, photo, item_id),
        )
        conn.commit()
        return redirect(url_for("bin_detail", code=item["bin_code"]))

    return render_template("edit_item.html", item=item)


@app.route("/items/<int:item_id>/delete", methods=["POST"])
def delete_item(item_id):
    conn = db.get_db()
    item = conn.execute(
        """SELECT items.photo, bins.code AS bin_code FROM items
           JOIN bins ON items.bin_id = bins.id WHERE items.id = ?""",
        (item_id,),
    ).fetchone()
    if item is None:
        abort(404)
    delete_photo(item["photo"])
    conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    return redirect(url_for("bin_detail", code=item["bin_code"]))


@app.route("/bin/<code>/delete", methods=["POST"])
def delete_bin(code):
    conn = db.get_db()
    bin_row = get_bin_or_404(conn, code)
    photos = conn.execute(
        "SELECT photo FROM items WHERE bin_id = ? AND photo IS NOT NULL",
        (bin_row["id"],),
    ).fetchall()
    for row in photos:
        delete_photo(row["photo"])
    conn.execute("DELETE FROM bins WHERE code = ?", (code,))
    conn.commit()
    return redirect(url_for("index"))


@app.route("/bin/<code>/qr.png")
def bin_qr(code):
    conn = db.get_db()
    get_bin_or_404(conn, code)
    img = qrcode.make(code, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/bin/<code>/label")
def bin_label(code):
    conn = db.get_db()
    bin_row = get_bin_or_404(conn, code)
    return render_template("label.html", bin=bin_row)


@app.route("/scan")
def scan():
    conn = db.get_db()
    recent = conn.execute(
        "SELECT code, name FROM bins ORDER BY created_at DESC LIMIT 6"
    ).fetchall()
    return render_template("scan.html", recent=recent)


@app.route("/go")
def go_to_bin():
    """Manual fallback for when the camera scanner isn't available."""
    raw = request.args.get("code", "").strip().upper()
    if not raw:
        return redirect(url_for("scan"))
    if not raw.startswith("BIN-"):
        raw = "BIN-" + raw.lstrip("-")
    conn = db.get_db()
    row = conn.execute("SELECT code FROM bins WHERE code = ?", (raw,)).fetchone()
    if row is None:
        return render_template("scan_notfound.html", code=raw), 404
    return redirect(url_for("bin_detail", code=row["code"]))


@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory(
        app.static_folder, "manifest.webmanifest", mimetype="application/manifest+json"
    )


@app.route("/sw.js")
def service_worker():
    # Served from the root so the worker's scope covers the whole site.
    response = send_from_directory(
        Path(app.static_folder) / "js", "sw.js", mimetype="application/javascript"
    )
    response.headers["Cache-Control"] = "no-cache"
    return response


if __name__ == "__main__":
    # Serve over HTTPS when certificates exist. Browsers only expose the camera
    # (and service workers) in a secure context, so QR scanning from a phone
    # requires this. Falls back to plain HTTP if the certs are missing.
    cert = Path(__file__).parent / "certs" / "server-cert.pem"
    key = Path(__file__).parent / "certs" / "server-key.pem"

    if cert.exists() and key.exists():
        print("Serving over HTTPS: https://localhost:5000")
        app.run(
            host="0.0.0.0", port=5000, debug=True, ssl_context=(str(cert), str(key))
        )
    else:
        print("No certificates found - serving over plain HTTP (camera will not work).")
        print("Run scripts/make-certs.sh <your-lan-ip> to enable HTTPS.")
        app.run(host="0.0.0.0", port=5000, debug=True)
