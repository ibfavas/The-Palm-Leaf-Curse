# The Palm-Leaf Curse

![A rain-darkened archive and an open palm-leaf manuscript](assets/cover.png)

A seven-chapter, single-player security and forensics CTF set in a fictional Thrissur archive during the 2026 monsoon. You investigate the death of Professor Raghavan Menon and trace manuscript `MS-1794-047` across a case journal, generated forensic artifacts, and three intentionally vulnerable local web services.

## Lab services and scope

Docker Compose starts four Python and Flask containers bound to `127.0.0.1`:

| Service | Address | Role in the case |
| --- | --- | --- |
| Case journal | [127.0.0.1:8780](http://127.0.0.1:8780) | Chapter narrative, SQLite progress tracking, evidence downloads, and an HTTP catcher endpoint |
| State archives | [127.0.0.1:8781](http://127.0.0.1:8781) | Reading-room catalogue search and digitisation portal |
| Trust documents | [127.0.0.1:8782](http://127.0.0.1:8782) | Endowment and archive document lookup portal |
| Kunnathu Properties | [127.0.0.1:8783](http://127.0.0.1:8783) | Developer enquiry site with a headless Chromium admin reviewer |

Across the seven chapters, the challenges cover web reconnaissance, LSB steganography on a synthetic palm-leaf scan, SQL injection in SQLite, insecure direct object reference (IDOR), Vigenere cipher decryption, stored XSS with filter bypass against an authenticated headless browser session, and deleted-file recovery from an `ext2` disk image.

## Requirements

- Docker Engine with Docker Compose v2

The narrative chapters, hint replies, evidence generators, and encoded flag values all live inside the repository. No separate configuration files or environment variables are needed.

## Start the lab

Run the stack from the repository root:

```sh
docker compose up
```

On the first run, Docker builds the container images and installs Flask, Gunicorn, Pillow, Chromium, and `e2fsprogs`. Once the health check passes, open [http://127.0.0.1:8780](http://127.0.0.1:8780). Keep using the same browser profile so your session cookie stays intact as chapters unlock.

Everything listens on `127.0.0.1` only. No port is exposed publicly.

## Flag storage

Flag values are stored in the repository as Base64 strings. Because anyone reading the source can decode Base64, treat this strictly as a self-contained local lab and do not reuse those strings as credentials or secrets elsewhere.

## Stop and reset

Stop the containers with `Ctrl+C` or run:

```sh
docker compose down
```

Your chapter progress is stored in a Docker volume and survives a normal stop. To wipe progress and start from chapter 1, remove the volumes and start again:

```sh
docker compose down -v
docker compose up
```

## Check a chapter

`check_chapter.py` runs an isolated smoke test in a temporary directory without touching your live progress database. It checks page access, attachment gating, and rejection of an invalid flag submission, printing `PASS` or `FAIL`:

```sh
docker compose run --rm --no-deps game python check_chapter.py 6
```

Replace `6` with any chapter number from `1` to `7`.

## License

Available under the MIT License. See [LICENSE](LICENSE).
