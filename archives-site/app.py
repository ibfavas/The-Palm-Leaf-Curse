import hashlib
import hmac
import os
import secrets
import sqlite3
from pathlib import Path

from flask import Flask, Response, abort, redirect, render_template, request, session, url_for

app = Flask(__name__)
accession = Path(os.environ.get("PALM_ACCESSION", "/var/lib/accession"))

if (accession / "seal").exists():
    app.secret_key = (accession / "seal").read_bytes()
else:
    app.secret_key = b"development-secret-key-12345678"

app.config.update(SESSION_COOKIE_NAME="reading_room", SESSION_COOKIE_HTTPONLY=True,
                  SESSION_COOKIE_SAMESITE="Strict", MAX_CONTENT_LENGTH=4096,
                  TRUSTED_HOSTS=["127.0.0.1", "localhost"])

DB_PATH = Path("/tmp/archives_catalogue.db")


def get_ch3_flag():
    try:
        return (accession / "ch3_flag").read_text().strip()
    except OSError as error:
        raise RuntimeError("Chapter data is unavailable.") from error


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('ATTACH DATABASE ":memory:" AS information_schema')
    conn.execute('CREATE TABLE IF NOT EXISTS information_schema.tables (table_name text, table_type text)')
    conn.execute('CREATE TABLE IF NOT EXISTS information_schema.columns (table_name text, column_name text)')
    conn.execute('DELETE FROM information_schema.tables')
    conn.execute('DELETE FROM information_schema.columns')
    conn.execute("INSERT INTO information_schema.tables VALUES ('catalogue', 'BASE TABLE'), ('readers', 'BASE TABLE'), ('portal_secrets', 'BASE TABLE')")
    conn.execute("INSERT INTO information_schema.columns VALUES ('catalogue', 'id'), ('catalogue', 'title'), ('catalogue', 'material'), ('readers', 'accession_id'), ('readers', 'reader_name'), ('readers', 'status'), ('portal_secrets', 'id'), ('portal_secrets', 'secret_name'), ('portal_secrets', 'secret_value')")
    return conn


def init_db():
    flag = get_ch3_flag()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS catalogue")
    cur.execute("DROP TABLE IF EXISTS readers")
    cur.execute("DROP TABLE IF EXISTS portal_secrets")

    cur.execute("""
        CREATE TABLE catalogue (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            material TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE readers (
            accession_id TEXT,
            reader_name TEXT,
            year INTEGER,
            status TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE portal_secrets (
            id INTEGER PRIMARY KEY,
            secret_name TEXT,
            secret_value TEXT
        )
    """)

    restricted_material = (
        "Palm leaf · 34 leaves\n\n"
        "Previous readers:\n"
        "· Vasudevan Namboothiri (Priest, 1974) — Deceased (snakebite)\n"
        "· Lakshmikutty Amma (Librarian, 2009) — Deceased (fall)\n"
        "· Prof. Raghavan Menon (Reader, 2026) — Deceased (heart attack)\n"
        "· Current reader: You (Active Session)\n\n"
        'Admin note: "Per donor request, MS-1794-047 is not to be digitised or exhibited. Donor: Kunnathu Charitable Trust."'
    )

    public_records = [
        ("MP-1931-012", "Paddy fields of the Kole wetlands", "Survey map · linen-backed paper", "public"),
        ("RG-1908-032", "Reading room accession register", "Bound register · 108 folios", "public"),
        ("OR-1964-081", "Thrissur monsoon observations", "Field notebooks · 3 volumes", "public"),
        ("MS-1794-047", "The Vadakkumkara grandham", restricted_material, "restricted"),
    ]
    cur.executemany("INSERT INTO catalogue VALUES (?, ?, ?, ?)", public_records)

    readers_data = [
        ("MS-1794-047", "Vasudevan Namboothiri", 1974, "Deceased (snakebite)"),
        ("MS-1794-047", "Lakshmikutty Amma", 2009, "Deceased (fall)"),
        ("MS-1794-047", "Prof. Raghavan Menon", 2026, "Deceased (heart attack)"),
        ("MS-1794-047", "You", 2026, "Active (Casebook reader)"),
    ]
    cur.executemany("INSERT INTO readers VALUES (?, ?, ?, ?)", readers_data)

    cur.execute("INSERT INTO portal_secrets VALUES (1, 'donor_covenant_flag', ?)", (flag,))

    conn.commit()
    conn.close()


init_db()


@app.after_request
def headers(response):
    response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                             "Referrer-Policy": "no-referrer",
                             "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'; object-src 'none'; form-action 'self'"})
    return response


@app.get("/")
@app.get("/catalogue")
@app.get("/staff")
def public():
    if request.path != "/catalogue":
        return render_template("archive.html", page=request.path)

    q = request.args.get("q", "").strip()
    error = None
    records = []

    conn = get_db()
    cur = conn.cursor()
    try:
        if not q:
            cur.execute("SELECT id, title, material FROM catalogue WHERE status = 'public'")
            records = cur.fetchall()
        else:
            query = f"SELECT id, title, material FROM catalogue WHERE status = 'public' AND title LIKE '%{q}%'"
            cur.execute(query)
            records = cur.fetchall()
    except sqlite3.OperationalError as e:
        error = f"Database error: {e}"
    except Exception as e:
        error = f"Query error: {e}"
    finally:
        conn.close()

    return render_template("archive.html", page=request.path, records=records, error=error)


@app.get("/robots.txt")
def robots():
    return Response("User-agent: *\nDisallow: /digitisation/\n", mimetype="text/plain")


@app.route("/digitisation/", methods=["GET", "POST"])
def room():
    sid = request.cookies.get("casebook", "")
    if request.method == "POST":
        expected = hmac.new(app.secret_key, sid.encode(), hashlib.sha256).hexdigest()[:16]
        if not sid or request.form.get("account") != "rmenon" or not secrets.compare_digest(
            request.form.get("password", "").encode(), expected.encode()
        ):
            return render_template("archive.html", page="login", failed=True), 401
        session["reader"] = sid
        return redirect(url_for("room"), 303)
    return render_template("archive.html", page="ledger" if sid and session.get("reader") == sid else "login")


@app.get("/digitisation/register.txt")
def extract():
    sid = request.cookies.get("casebook")
    if not sid or session.get("reader") != sid:
        abort(403)
    try:
        ledger_text = (accession / "ledger").read_text()
    except OSError:
        abort(503)
    return Response("MS-1794-047 | After-hours accession register\n03:12  rmenon\n\n" +
                    ledger_text + "\n", mimetype="text/plain",
                    headers={"Content-Disposition": 'attachment; filename="night-register.txt"'})
