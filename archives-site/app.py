import hashlib
import hmac
import os
import secrets
from pathlib import Path

from flask import Flask, Response, abort, redirect, render_template, request, session, url_for

app = Flask(__name__)
accession = Path(os.environ.get("PALM_ACCESSION", "/var/lib/accession"))
app.secret_key = (accession / "seal").read_bytes()
app.config.update(SESSION_COOKIE_NAME="reading_room", SESSION_COOKIE_HTTPONLY=True,
                  SESSION_COOKIE_SAMESITE="Strict", MAX_CONTENT_LENGTH=4096,
                  TRUSTED_HOSTS=["127.0.0.1", "localhost"])
records = (
    ("MS-1794-047", "The Vadakkumkara grandham", "Palm leaf · 34 leaves"),
    ("MP-1931-012", "Paddy fields of the Kole wetlands", "Survey map · linen-backed paper"),
    ("RG-1908-032", "Reading room accession register", "Bound register · 108 folios"),
    ("OR-1964-081", "Thrissur monsoon observations", "Field notebooks · 3 volumes"),
)


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
    q = request.args.get("q", "").strip().casefold()
    items = [row for row in records if q in " ".join(row).casefold()]
    return render_template("archive.html", page=request.path, records=items)


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
    return Response("MS-1794-047 | After-hours accession register\n03:12  rmenon\n\n" +
                    (accession / "ledger").read_text() + "\n", mimetype="text/plain",
                    headers={"Content-Disposition": 'attachment; filename="night-register.txt"'})
