import os
from pathlib import Path
from flask import Flask, abort, redirect, render_template, request, url_for

app = Flask(__name__)
app.config.update(MAX_CONTENT_LENGTH=4096, TRUSTED_HOSTS=["127.0.0.1", "localhost"])

accession = Path(os.environ.get("PALM_ACCESSION", "/var/lib/accession"))


def get_flag():
    flag_file = accession / "ch4_flag"
    if flag_file.exists():
        return flag_file.read_text().strip()
    return os.environ.get("PALM_CH4_FLAG", "")


@app.after_request
def headers(response):
    response.headers.update({
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'; object-src 'none'; form-action 'self'"
    })
    return response


@app.get("/")
def index():
    return redirect(url_for("view_doc", id="101"))


@app.get("/view")
@app.get("/document")
@app.get("/document/<id>")
def view_doc(id=None):
    doc_id = id or request.args.get("id", "").strip() or request.args.get("ref", "").strip()
    if not doc_id:
        return redirect(url_for("view_doc", id="101"))

    flag = get_flag()

    docs = {
        "101": {
            "id": "DOC-101",
            "title": "Annual Philanthropy & Endowment Report (2025-2026)",
            "classification": "Internal General",
            "author": "Trust Executive Office",
            "date": "March 15, 2026",
            "body": (
                "Kunnathu Charitable Trust — Internal Operating Report\n\n"
                "Summary of community endowments and temple restoration allocations. "
                "The Trust continues to oversee ancestral estates in Thrissur district. "
                "Capital reallocation pending for proposed Nilambur township integration."
            )
        },
        "102": {
            "id": "DOC-102",
            "title": "DRAFT ARTICLE: The 300-Year Grandham and the Missing Trustee",
            "classification": "Confidential / Suppressed Draft",
            "author": "Meera Menon (Journalism Intern, Kerala Press Academy)",
            "date": "May 19, 2026",
            "body": (
                "INTERCEPTED PRESS DRAFT — NOT FOR PUBLICATION\n\n"
                "Investigation into the provenance of MS-1794-047 at Thrissur State Archives.\n"
                "Temple lore surrounding the Vadakkumkara Bhagavathy grandham suggests the death of "
                "Sankaran Namboothiri in 1794 was not accidental. Kunnathu family historical acquisition "
                "of 140 acres of temple paddy land coincides with the disappearance of original temple records.\n\n"
                "[EDITOR NOTE: Publication blocked per Trustee instruction. Withhold all source copies.]"
            )
        },
        "103": {
            "id": "DOC-103",
            "title": "POLICE MEMO: Special Incident Report — Case 402/2026",
            "classification": "Law Enforcement Sensitive",
            "author": "Thrissur East Police Station / Liaison",
            "date": "May 22, 2026",
            "body": (
                "CONFIDENTIAL INCIDENT BRIEFING\n\n"
                "Subject: Menon, Meera (21) — Residence: Chembukkavu, Thrissur.\n"
                "Subject found deceased at family residence. Preliminary verdict: apparent suicide.\n"
                "All notebooks, digital records, and manuscript transcripts impounded.\n\n"
                "Cross-reference notes on file: Subject was investigating historical endowment claims. "
                "Inquiry references the 1974 temple priest's letter, filed under the Trust's restricted historical archive, ref TR-1974-047.\n\n"
                "Status: Investigation closed. Maintain media blackout."
            )
        },
        "TR-1974-047": {
            "id": "TR-1974-047",
            "title": "Restricted Archival Holding: Priest Vasudevan Namboothiri (1974)",
            "classification": "RESTRICTED HISTORICAL ARCHIVE",
            "author": "Vasudevan Namboothiri (Temple Priest)",
            "date": "August 14, 1974",
            "body": (
                "VADAKKUMKARA BHAGAVATHY TEMPLE\n"
                "Private correspondence / 1974 — To the temple committee\n\n"
                '"I have read one page of the grandham. It says the trustee was murdered and the deed forged. '
                'I am afraid. If something happens to me, look at the Kunnathu family. '
                'The key to the middle leaves is the name of the goddess. She will open what men have locked."\n\n'
                "— Vasudevan Namboothiri\n\n"
                f"Archival verification token: {flag}"
            )
        }
    }

    norm_id = doc_id.upper()
    doc = docs.get(doc_id) or docs.get(norm_id)

    return render_template("portal.html", doc=doc, requested_id=doc_id)


@app.get("/archive")
def archive():
    ref = request.args.get("ref", "").strip()
    if ref:
        return redirect(url_for("view_doc", id=ref))
    return render_template("portal.html", archive_search=True)
