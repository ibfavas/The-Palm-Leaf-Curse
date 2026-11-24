"""Check a chapter in a disposable operator session. Prints only the result."""
import os
import sys
import tempfile
from pathlib import Path


def verify(page):
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["PALM_STATE"] = str(Path(tmp) / "journal")
        os.environ["PALM_ACCESSION"] = str(Path(tmp) / "archive")
        import app

        if page not in app.PLAYABLE:
            raise ValueError("Pending chapter")
        client = app.app.test_client()
        assert client.get("/").status_code == 200
        sid = client.get_cookie("casebook").value
        with app.connect() as db:
            if page > 1:
                assert client.get(f"/attachments/{page}").status_code == 404
            db.execute("UPDATE players SET chapter=? WHERE id=?", (page, sid))
            csrf = db.execute("SELECT csrf FROM players WHERE id=?", (sid,)).fetchone()[0]
        desk = client.get("/")
        assert desk.status_code == 200
        assert not any(f.encode() in desk.data for f in app.flags)
        if page in app.attachments:
            response = client.get(f"/attachments/{page}")
            assert response.status_code == 200 and len(response.data) > 0
            assert not any(f.encode() in response.data for f in app.flags)
        if page > 3:
            assert b"Message Meera" not in desk.data
            assert client.post("/message/3", data={"csrf": csrf}).status_code == 403
        def submit(value):
            return client.post(f"/submit/{page}", data={"csrf": csrf, "entry": value}, follow_redirects=True)
        assert b"did not match" in submit("unmatched").data
        assert f"{page} of 7 chapters solved".encode() in submit(app.flags[page - 1]).data


if __name__ == "__main__":
    try:
        verify(int(sys.argv[1]))
    except Exception:
        print("FAIL")
        sys.exit(1)
    print("PASS")
