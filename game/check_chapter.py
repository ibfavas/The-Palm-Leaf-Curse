"""Check a chapter in a disposable operator session. Prints only the result."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def verify(page):
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["PALM_STATE"] = str(Path(tmp) / "journal")
        os.environ["PALM_ACCESSION"] = str(Path(tmp) / "archive")
        import app

        if page not in app.PLAYABLE:
            raise ValueError("Pending chapter")
        client = app.app.test_client()
        assert client.get("/").status_code == 200
        assert client.get("/seed.json").status_code == 404
        assert client.get("/static/seed.json").status_code == 404
        sid = client.get_cookie("casebook").value
        with app.connect() as db:
            if page > 1:
                assert client.get(f"/attachments/{page}").status_code == 404
            db.execute("UPDATE players SET chapter=? WHERE id=?", (page, sid))
            csrf = db.execute("SELECT csrf FROM players WHERE id=?", (sid,)).fetchone()[0]
        desk = client.get("/")
        assert desk.status_code == 200
        assert not any(value.encode() in desk.data for value in app.flags_b64)
        if page in app.attachments:
            response = client.get(f"/attachments/{page}")
            assert response.status_code == 200 and len(response.data) > 0
        if page > 3:
            assert b"Message Meera" not in desk.data
            assert client.post("/message/3", data={"csrf": csrf}).status_code == 403
        def submit(value):
            return client.post(f"/submit/{page}", data={"csrf": csrf, "entry": value}, follow_redirects=True)
        assert b"did not match" in submit("unmatched").data
        with app.connect() as db:
            assert db.execute("SELECT chapter FROM players WHERE id=?", (sid,)).fetchone()[0] == page


if __name__ == "__main__":
    try:
        verify(int(sys.argv[1]))
    except Exception:
        print("FAIL")
        sys.exit(1)
    print("PASS")
