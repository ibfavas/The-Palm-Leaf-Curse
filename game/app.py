import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import tempfile
import time
from pathlib import Path

from flask import Flask, Response, abort, g, redirect, render_template, request, send_file, url_for

from files.leaves import first_page
from files.laptop import laptop
from files.correspondence import middle_leaves, priest_letter

app = Flask(__name__)
app.config.update(MAX_CONTENT_LENGTH=65536, TRUSTED_HOSTS=["localhost", "127.0.0.1"])
BASE = Path(__file__).resolve().parent
STATE = Path(os.environ.get("PALM_STATE", "/var/lib/palm"))
ACCESSION = Path(os.environ.get("PALM_ACCESSION", "/var/lib/accession"))
STATE.mkdir(parents=True, exist_ok=True)
ACCESSION.mkdir(parents=True, exist_ok=True)

SEED = json.loads((BASE / "seed.json").read_text())
flags_b64 = SEED["flags_b64"]
if (len(flags_b64) != 7 or len(set(flags_b64)) != 7 or
        not all(isinstance(value, str) and len(value) % 4 == 0 for value in flags_b64)):
    raise RuntimeError("The chapter seed is invalid.")
HINTS = SEED["meera_replies"]
if not isinstance(HINTS, list) or len(HINTS) != 3 or not all(isinstance(h, str) and h.strip() for h in HINTS):
    raise RuntimeError("The chapter seed is invalid.")

story_dir = BASE / "story" if (BASE / "story").is_dir() else BASE.parent / "story"
chapters = []
for path in sorted(story_dir.glob("*.md")):
    heading, body = path.read_text().strip().split("\n\n", 1)
    chapters.append((heading.split(": ", 1)[1], body.split("\n\n")))

PLAYABLE = {1, 2, 3, 4, 5, 6, 7}
workspace = tempfile.TemporaryDirectory(prefix="palm-records-")
downloads = Path(workspace.name)
evidence = SEED["evidence"]
first_page(downloads / "MS-1794-047-01.png", evidence["first_leaf_note"] + "\n" + flags_b64[1])
(downloads / "middle-leaves.txt").write_text(
    middle_leaves(evidence["confession"] + "\n" + flags_b64[4], SEED["cipher_key"])
)
priest_letter(downloads / "committee-copy.png", evidence["priest_letter"], SEED["temple"])
laptop(downloads / "RM-work.img", evidence["professor_note"], evidence["last_leaf"], flags_b64[6])
aftermath = {int(chapter): text for chapter, text in SEED["aftermath"].items()}
portraits = {
    "meera": (1, "Meera Menon in the archives courtyard"),
    "vasudevan": (4, "Vasudevan Namboothiri, 1974"),
    "lakshmikutty": (4, "Lakshmikutty Amma, 2009"),
    "kunjiraman": (6, "Kunjiraman at the manuscript desk, 1794"),
    "sankaran": (6, "Sankaran Namboothiri at the temple pond, 1794"),
    "devan": (6, "Devan Kunnathu at the township site"),
    "window": (7, "Photograph attached to the final email"),
}
attachments = {7: "RM-work.img", 2: "MS-1794-047-01.png", 5: "middle-leaves.txt"}


def connect():
    db = sqlite3.connect(STATE / "case.db", timeout=10)
    db.row_factory = sqlite3.Row
    return db


with connect() as setup:
    setup.executescript("""
        CREATE TABLE IF NOT EXISTS players(
            id TEXT PRIMARY KEY, chapter INTEGER NOT NULL DEFAULT 1,
            hints INTEGER NOT NULL DEFAULT 0, csrf TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    """)
    setup.execute("INSERT OR IGNORE INTO settings VALUES ('archive', ?)", (secrets.token_hex(32),))
    archive_key = setup.execute("SELECT value FROM settings WHERE key='archive'").fetchone()[0]
(ACCESSION / "ledger").write_text(flags_b64[0])
(ACCESSION / "seal").write_text(archive_key)
(ACCESSION / "ch3_flag").write_text(flags_b64[2])
(ACCESSION / "ch4_flag").write_text(flags_b64[3])
(ACCESSION / "ch6_flag").write_text(flags_b64[5])

CATCHER_LOGS = []


@app.route("/catcher", methods=["GET", "POST", "OPTIONS"])
def catcher():
    if request.method == "OPTIONS":
        resp = Response("", 204)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "*"
        return resp

    data = ""
    if request.method == "POST":
        data = request.get_data(as_text=True)
    elif request.method == "GET":
        data = request.args.get("data") or request.args.get("exfil") or request.args.get("q") or request.query_string.decode("utf-8", "ignore")

    if data:
        entry = {
            "time": time.strftime("%H:%M:%S"),
            "ip": request.remote_addr,
            "data": data[:16000]
        }
        CATCHER_LOGS.insert(0, entry)
        if len(CATCHER_LOGS) > 30:
            CATCHER_LOGS.pop()

    if request.headers.get("Accept", "").startswith("text/html"):
        return render_template("catcher.html", logs=CATCHER_LOGS)

    resp = Response("OK\n", 200, mimetype="text/plain")
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


@app.before_request
def open_session():
    if request.endpoint in ("health", "static", "catcher"):
        return
    g.db = connect()
    sid = request.cookies.get("casebook", "")
    g.player = g.db.execute("SELECT * FROM players WHERE id=?", (sid,)).fetchone()
    if g.player is None:
        if request.method != "GET" or request.endpoint != "desk":
            abort(403)
        sid = secrets.token_hex(24)
        with g.db:
            g.db.execute("INSERT INTO players(id, csrf) VALUES (?, ?)", (sid, secrets.token_hex(16)))
        g.player = g.db.execute("SELECT * FROM players WHERE id=?", (sid,)).fetchone()
        g.new_id = sid
    if request.method == "POST" and not secrets.compare_digest(
        request.form.get("csrf", "").encode(), g.player["csrf"].encode()
    ):
        abort(403)


@app.teardown_request
def close_db(_error):
    if "db" in g:
        g.db.close()


@app.after_request
def headers(response):
    if "new_id" in g:
        response.set_cookie("casebook", g.new_id, httponly=True, samesite="Strict", max_age=31536000)
    response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                             "Referrer-Policy": "no-referrer"})
    if request.endpoint == "catcher":
        response.headers.update({
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        })
    else:
        response.headers["Content-Security-Policy"] = "default-src 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'"
    return response


@app.get("/health")
def health():
    return "", 204


@app.get("/")
@app.get("/journal/<int:page>")
def desk(page=None):
    current = g.player["chapter"]
    page = current if page is None else page
    if not 0 <= page <= min(current, 8):
        abort(404)
    password = hmac.new(archive_key.encode(), g.player["id"].encode(), hashlib.sha256).hexdigest()[:16]
    messages = [(i, hint) for i, hint in enumerate(HINTS, 1) if current <= 3 and g.player["hints"] & (1 << i)]
    return render_template("desk.html", page=page, current=current, chapters=chapters,
                           messages=messages, hinted=bool(g.player["hints"] & (1 << current)),
                           password=password, archive=f"http://{request.host.split(':')[0]}:8781",
                           trust=f"http://{request.host.split(':')[0]}:8782",
                           developer=f"http://{request.host.split(':')[0]}:8783",
                           catcher_logs=CATCHER_LOGS,
                           playable=PLAYABLE, after=aftermath, portraits=portraits, error=request.args.get("result") == "unmatched")


@app.post("/message/<int:page>")
def message(page):
    if not 1 <= page <= 3 or page != g.player["chapter"]:
        abort(403)
    with g.db:
        g.db.execute("UPDATE players SET hints=hints | ? WHERE id=? AND chapter=?",
                     (1 << page, g.player["id"], page))
    return redirect(url_for("desk", _anchor="thread"), 303)


@app.post("/submit/<int:page>")
def submit(page):
    if page != g.player["chapter"] or page not in PLAYABLE:
        abort(403)
    submitted = request.form.get("entry", "").strip().encode()
    encoded = base64.b64encode(submitted).decode()
    if not secrets.compare_digest(encoded, flags_b64[page - 1]):
        return redirect(url_for("desk", result="unmatched", _anchor="entry"), 303)
    with g.db:
        g.db.execute("UPDATE players SET chapter=chapter+1 WHERE id=? AND chapter=?", (g.player["id"], page))
    return redirect(url_for("desk"), 303)


@app.get("/attachments/<int:page>")
def attachment(page):
    if page not in attachments or g.player["chapter"] < page:
        abort(404)
    return send_file(downloads / attachments[page], as_attachment=True, conditional=False)


@app.get("/correspondence/committee-copy")
def committee_copy():
    if g.player["chapter"] < 5:
        abort(404)
    return send_file(downloads / "committee-copy.png", as_attachment=True, conditional=False)


@app.get("/collection/<name>.jpg")
def portrait(name):
    if name not in portraits or g.player["chapter"] < portraits[name][0]:
        abort(404)
    portraits_dir = BASE / "portraits" if (BASE / "portraits").is_dir() else BASE.parent / "game" / "portraits"
    return send_file(portraits_dir / (name + ".jpg"), conditional=False)
