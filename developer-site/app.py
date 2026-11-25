import json
import os
import re
import secrets
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from flask import Flask, Response, abort, make_response, redirect, render_template, request, url_for

app = Flask(__name__)
app.config.update(MAX_CONTENT_LENGTH=8192, TRUSTED_HOSTS=["127.0.0.1", "localhost"])

accession = Path(os.environ.get("PALM_ACCESSION", "/var/lib/accession"))
DB_PATH = Path("/tmp/developer_enquiries.db")
TOKEN_PATH = Path("/tmp/developer_tokens.json")

if not TOKEN_PATH.exists():
    TOKEN_PATH.write_text(json.dumps({
        "secret": secrets.token_hex(24),
        "token": secrets.token_hex(16)
    }))

tokens = json.loads(TOKEN_PATH.read_text())
ADMIN_SECRET = tokens["secret"]
ADMIN_TOKEN = tokens["token"]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS enquiries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                message TEXT,
                time TEXT
            )
        """)


init_db()


def get_flag():
    try:
        return (accession / "ch6_flag").read_text().strip()
    except OSError:
        abort(503)


def review_enquiry(enquiry_id):
    time.sleep(2)
    port = os.environ.get("PORT", "8783")
    login_url = f"http://127.0.0.1:{port}/admin/login?token={ADMIN_TOKEN}&target=/admin/enquiries/{enquiry_id}"
    browser = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
    if browser:
        tmpdir = tempfile.mkdtemp(prefix=f"bot-{enquiry_id}-")
        try:
            proc = subprocess.Popen([
                browser,
                "--headless=new",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                f"--user-data-dir={tmpdir}",
                login_url
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(4)
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except Exception:
                proc.kill()
        except Exception as e:
            app.logger.error("Bot error: %s", e)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


@app.after_request
def headers(response):
    response.headers.update({
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
    })
    return response


@app.get("/")
def index():
    return render_template("developer.html", page="home")


@app.get("/projects")
def projects():
    return render_template("developer.html", page="projects")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()[:64]
        email = request.form.get("email", "").strip()[:64]
        raw_message = request.form.get("message", "").strip()[:2048]

        cleaned_message = re.sub(r"(?is)<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", raw_message)
        cleaned_message = re.sub(r"(?i)</?script[^>]*>", "", cleaned_message)

        now = time.strftime("%Y-%m-%d %H:%M")
        with get_db() as db:
            cur = db.execute("INSERT INTO enquiries (name, email, message, time) VALUES (?, ?, ?, ?)",
                             (name, email, cleaned_message, now))
            enquiry_id = cur.lastrowid

        threading.Thread(target=review_enquiry, args=(enquiry_id,), daemon=True).start()

        return render_template("developer.html", page="contact", submitted=True)
    return render_template("developer.html", page="contact")


@app.get("/admin/login")
def admin_login():
    token = request.args.get("token")
    target = request.args.get("target", "/admin/inbox")
    if token != ADMIN_TOKEN:
        abort(403)
    resp = make_response(redirect(target))
    resp.set_cookie("admin_session", ADMIN_SECRET, httponly=True, samesite="Lax", path="/")
    return resp


@app.get("/admin/enquiries/<int:enquiry_id>")
def view_enquiry(enquiry_id):
    if request.cookies.get("admin_session") != ADMIN_SECRET:
        abort(403)
    with get_db() as db:
        row = db.execute("SELECT * FROM enquiries WHERE id=?", (enquiry_id,)).fetchone()
    if not row:
        abort(404)
    record = dict(row)
    return render_template("developer.html", page="admin_enquiry", enquiry=record)


@app.get("/admin/inbox")
def admin_inbox():
    if request.cookies.get("admin_session") != ADMIN_SECRET:
        abort(403)
    flag = get_flag()
    return render_template("inbox.html", flag=flag)
