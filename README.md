# The Palm-Leaf Curse 🌧️

![A rain-darkened archive and an open palm-leaf manuscript](assets/cover.png)

A seven-chapter, single-player CTF set in a fictional Kerala archive during the 2026 monsoon. Follow the case through a journal and three local websites.

## What you need

- Docker Engine with Docker Compose v2

The story, Meera’s replies, puzzle evidence and encoded flag values are included in the repository. No separate files or environment variables are needed.

## Start the lab

From the repository directory, run:

```sh
docker compose up
```

Compose builds the images and downloads the required packages on the first run. When the services are ready, open the journal at [http://127.0.0.1:8780](http://127.0.0.1:8780). Keep using the same browser profile throughout the game.

| Local site | Address |
| --- | --- |
| Case journal | [127.0.0.1:8780](http://127.0.0.1:8780) |
| State archives | [127.0.0.1:8781](http://127.0.0.1:8781) |
| Trust documents | [127.0.0.1:8782](http://127.0.0.1:8782) |
| Kunnathu Properties | [127.0.0.1:8783](http://127.0.0.1:8783) |

Everything binds to localhost. Nothing needs to be deployed publicly. 🕯️

## About the flags

⚠️ The flag values are stored as Base64 strings. Base64 is an encoding, not encryption; anyone who reads the repository can decode them. This is an intentional tradeoff for a self-contained public lab. Do not reuse these flags as secrets anywhere else.

## Stop and reset

Stop the services with `Ctrl+C`, or run:

```sh
docker compose down
```

Your chapter progress survives a normal stop. To erase progress and start fresh, remove the Compose volumes:

```sh
docker compose down -v
docker compose up
```

## Check a chapter

The isolated chapter check prints only `PASS` or `FAIL`. It checks chapter access, attachment gating and rejection of an incorrect entry without changing the live progress database:

```sh
docker compose run --rm --no-deps game python check_chapter.py 6
```

Replace `6` with a chapter number from 1 to 7.

## License

This project is available under the MIT License. See [LICENSE](LICENSE).
