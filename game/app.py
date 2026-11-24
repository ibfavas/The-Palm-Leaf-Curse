import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from pathlib import Path

from flask import Flask, abort, g, redirect, render_template, request, url_for

app = Flask(__name__)
app.config.update(MAX_CONTENT_LENGTH=4096, TRUSTED_HOSTS=["localhost", "127.0.0.1"])
BASE = Path(__file__).parent
STATE = Path(os.environ.get("PALM_STATE", "/var/lib/palm"))
ACCESSION = Path(os.environ.get("PALM_ACCESSION", "/var/lib/accession"))
STATE.mkdir(parents=True, exist_ok=True)
ACCESSION.mkdir(parents=True, exist_ok=True)
source = Path(os.environ.get("PALM_SOURCE", "/run/private/story.md")).read_text()
flags = re.findall(r'^\*\*Flag:\*\* `(flag\{[^}]+\})`$', source, re.M)
if len(flags) != 7 or len(set(flags)) != 7:
    raise RuntimeError("The private story does not contain seven distinct chapter records.")
chapters = []
for path in sorted((BASE / "story").glob("*.md")):
    heading, body = path.read_text().strip().split("\n\n", 1)
    chapters.append((heading.split(": ", 1)[1], body.split("\n\n")))
HINTS = json.loads(Path(os.environ.get("PALM_HINTS", "/run/private/correspondence.json")).read_text())
if not isinstance(HINTS, list) or len(HINTS) != 3 or not all(isinstance(h, str) and h.strip() for h in HINTS):
    raise RuntimeError("The private correspondence must contain three replies.")
PLAYABLE = {1}


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
(ACCESSION / "ledger").write_text(flags[0])
(ACCESSION / "seal").write_text(archive_key)


@app.before_request
def open_session():
    if request.endpoint in ("health", "static"):
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
                             "Referrer-Policy": "no-referrer",
                             "Content-Security-Policy": "default-src 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'"})
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
    messages = [(i, hint) for i, hint in enumerate(HINTS, 1) if g.player["hints"] & (1 << i)]
    return render_template("desk.html", page=page, current=current, chapters=chapters,
                           messages=messages, hinted=bool(g.player["hints"] & (1 << current)),
                           password=password, archive=f"http://{request.host.split(':')[0]}:8781",
                           playable=PLAYABLE, error=request.args.get("result") == "unmatched")


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
    if not secrets.compare_digest(request.form.get("entry", "").strip().encode(), flags[page - 1].encode()):
        return redirect(url_for("desk", result="unmatched", _anchor="entry"), 303)
    with g.db:
        g.db.execute("UPDATE players SET chapter=chapter+1 WHERE id=? AND chapter=?", (g.player["id"], page))
    return redirect(url_for("desk"), 303)
