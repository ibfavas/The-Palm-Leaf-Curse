# The Palm-Leaf Curse

A local, single-player investigation set in Thrissur during the 2026 monsoon.

Place the original author’s Markdown file at `~/Downloads/the-palm-leaf-curse-story.md`. To use another location, set `PALM_STORY_FILE` to its absolute path. Meera’s private correspondence is supplied alongside it as `the-palm-leaf-curse-correspondence.json` (or set `PALM_HINT_FILE`). This UTF-8 JSON array contains the three parables in chapter order. Keep both operator inputs outside the player’s checkout.

From this directory, start with Docker Compose v2 or later.

```sh
docker compose up
```

Open [the journal](http://127.0.0.1:8780). Use the same browser profile throughout. The archives open from the journal on port 8781, the Trust portal on port 8782, and the developer company website on port 8783. A local exfiltration listener feed is accessible at [http://127.0.0.1:8780/catcher](http://127.0.0.1:8780/catcher) to receive and inspect inbound HTTP data. Services bind to IPv4 loopback. The first build requires internet access for the base image, packages, and browser environment.

In Chapter 6, executive enquiries submitted via the developer site are reviewed by an automated administrative session on a short delay (a few seconds after submission).

Progress persists in a Docker volume across restarts. To stop the game, use `docker compose down`. To erase all players’ progress and start a new installation, use `docker compose down -v`, then `docker compose up`.

The private source and Docker administration belong to the host operator. A player with access to the original file or the Docker daemon can inspect the answers.

## Build status

All chapters (1 through 7), downloadable artifacts, and the epilogue are fully implemented and playable.

The operator can run a spoiler-free gate check against an isolated journal with `docker compose run --rm --no-deps game python check_chapter.py 6`. Use the chapter number you want to check. This checks page access, submission and progress. It prints PASS or FAIL and leaves live progress alone.
