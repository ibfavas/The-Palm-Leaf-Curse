import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import tempfile
from pathlib import Path

from flask import Flask, abort, g, redirect, render_template, request, send_file, url_for

from files.leaves import first_page
from files.laptop import laptop
from files.correspondence import middle_leaves, priest_letter

app = Flask(__name__)
app.config.update(MAX_CONTENT_LENGTH=4096, TRUSTED_HOSTS=["localhost", "127.0.0.1"])
BASE = Path(__file__).resolve().parent
STATE = Path(os.environ.get("PALM_STATE", "/var/lib/palm"))
ACCESSION = Path(os.environ.get("PALM_ACCESSION", "/var/lib/accession"))
STATE.mkdir(parents=True, exist_ok=True)
ACCESSION.mkdir(parents=True, exist_ok=True)

def find_story():
    env = os.environ.get("PALM_SOURCE")
    if env and Path(env).exists():
        return Path(env)
    if Path("/run/private/story.md").exists():
        return Path("/run/private/story.md")
    downloads = Path.home() / "Downloads" / "the-palm-leaf-curse-story.md"
    if downloads.exists():
        return downloads
    raise RuntimeError("The private story was not found.")

def find_hints():
    env = os.environ.get("PALM_HINTS")
    if env and Path(env).exists():
        return Path(env)
    if Path("/run/private/correspondence.json").exists():
        return Path("/run/private/correspondence.json")
    downloads = Path.home() / "Downloads" / "the-palm-leaf-curse-correspondence.json"
    if downloads.exists():
        return downloads
    raise RuntimeError("The private correspondence must contain three replies.")

source = find_story().read_text()
flags = re.findall(r'^\*\*Flag:\*\* `(flag\{[^}]+\})`$', source, re.M)
if len(flags) != 7 or len(set(flags)) != 7:
    raise RuntimeError("The private story does not contain seven distinct chapter records.")

story_dir = BASE / "story" if (BASE / "story").is_dir() else BASE.parent / "story"
chapters = []
for path in sorted(story_dir.glob("*.md")):
    heading, body = path.read_text().strip().split("\n\n", 1)
    chapters.append((heading.split(": ", 1)[1], body.split("\n\n")))

HINTS = json.loads(find_hints().read_text())
if not isinstance(HINTS, list) or len(HINTS) != 3 or not all(isinstance(h, str) and h.strip() for h in HINTS):
    raise RuntimeError("The private correspondence must contain three replies.")
PLAYABLE = {1, 2, 3, 5, 7}
workspace = tempfile.TemporaryDirectory(prefix="palm-records-")
downloads = Path(workspace.name)
sections = re.split(r"^### Chapter [1-7]: ", source, flags=re.M)[1:]
def quotations(page):
    return re.findall(r'^> "(.*?)"$', sections[page - 1], re.M)


first_page(downloads / "MS-1794-047-01.png", quotations(2)[0] + "\n" + flags[1])
aftermath = {
    1: sections[0].split("Then you see the login log.")[1].split("**Flag:**")[0].strip(),
    2: sections[1].split("As you read it,")[1].split("**Flag:**")[0].strip(),
    3: "And there is one field you did not see before. \"Current reader.\" It has your name in it.\n\nThe archive knows you are reading.",
}
aftermath[1] = "Then you see the login log. " + aftermath[1]
aftermath[2] = "As you read it, " + aftermath[2]
cipher_key = re.search(r"letter: ([A-Z]+)\.", sections[4])[1]
(downloads / "middle-leaves.txt").write_text(middle_leaves(quotations(5)[0] + "\n" + flags[4], cipher_key))
temple = re.search(r"accountant of the (.+? temple), 1794", source)[1]
priest_letter(downloads / "committee-copy.png", quotations(4)[0], temple)
last_note, last_line = quotations(7)[:2]
laptop(downloads / "RM-work.img", last_note, last_line, flags[6])
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
(ACCESSION / "ledger").write_text(flags[0])
(ACCESSION / "seal").write_text(archive_key)
(ACCESSION / "ch3_flag").write_text(flags[2])


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
    messages = [(i, hint) for i, hint in enumerate(HINTS, 1) if current <= 3 and g.player["hints"] & (1 << i)]
    return render_template("desk.html", page=page, current=current, chapters=chapters,
                           messages=messages, hinted=bool(g.player["hints"] & (1 << current)),
                           password=password, archive=f"http://{request.host.split(':')[0]}:8781",
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
    if not secrets.compare_digest(request.form.get("entry", "").strip().encode(), flags[page - 1].encode()):
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
