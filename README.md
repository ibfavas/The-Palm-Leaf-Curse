# The Palm-Leaf Curse

A local, single-player investigation set in Thrissur during the 2026 monsoon.

Place the original author’s Markdown file at `~/Downloads/the-palm-leaf-curse-story.md`. To use another location, set `PALM_STORY_FILE` to its absolute path. Meera’s private correspondence is supplied alongside it as `the-palm-leaf-curse-correspondence.json` (or set `PALM_HINT_FILE`). This UTF-8 JSON array contains the three parables in chapter order. Keep both operator inputs outside the player’s checkout.

From this directory, start with Docker Compose v2 or later.

```sh
docker compose up
```

Open [the journal](http://127.0.0.1:8780). Use the same browser profile throughout. The archives open from the journal on port 8781. Both services bind to IPv4 loopback. The first build requires internet access for the base image and Python packages.

Progress persists in a Docker volume across restarts. To stop the game, use `docker compose down`. To erase all players’ progress and start a new installation, use `docker compose down -v`, then `docker compose up`.

The private source and Docker administration belong to the host operator. A player with access to the original file or the Docker daemon can inspect the answers.

## Build status

Chapters 1 and 2 are playable. Chapters 5 and 7, their downloads and the epilogue are implemented behind their respective gates. Chapters 3, 4 and 6 are pending. Normal play stops at chapter 3.

The operator can run a spoiler-free gate check against an isolated journal with `docker compose run --rm --no-deps game python check_chapter.py 5`. Use the chapter number you want to check. This checks page access, submission and progress. It prints PASS or FAIL and leaves live progress alone.
