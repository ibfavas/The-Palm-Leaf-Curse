# The Palm-Leaf Curse 🌧️

![A rain-darkened archive and an open palm-leaf manuscript](assets/cover.png)

A seven-chapter, single-player CTF set in a fictional Kerala archive during the 2026 monsoon. Follow the case through a journal and three local websites.

## What you need

- Docker Engine with Docker Compose v2
- The private story file and Meera’s correspondence file supplied by the project owner

The private files are runtime inputs. Keep them outside the repository. By default, Compose looks for:

- `~/Downloads/the-palm-leaf-curse-story.md`
- `~/Downloads/the-palm-leaf-curse-correspondence.json`

To use other locations, set `PALM_STORY_FILE` and `PALM_HINT_FILE` to their absolute paths before starting Compose.

For example:

```sh
PALM_STORY_FILE="$HOME/ctf/the-palm-leaf-curse-story.md" \
PALM_HINT_FILE="$HOME/ctf/the-palm-leaf-curse-correspondence.json" \
docker compose up --build
```

## Start the lab

From the repository directory, run:

```sh
docker compose up --build
```

The first run downloads the base images and packages. When the services are ready, open the journal at [http://127.0.0.1:8780](http://127.0.0.1:8780). Keep using the same browser profile throughout the game.

| Local site | Address |
| --- | --- |
| Case journal | [127.0.0.1:8780](http://127.0.0.1:8780) |
| State archives | [127.0.0.1:8781](http://127.0.0.1:8781) |
| Trust documents | [127.0.0.1:8782](http://127.0.0.1:8782) |
| Kunnathu Properties | [127.0.0.1:8783](http://127.0.0.1:8783) |

Everything binds to localhost. Nothing needs to be deployed publicly. 🕯️

## Stop and reset

Stop the services with `Ctrl+C`, or run:

```sh
docker compose down
```

Your chapter progress survives a normal stop. To erase progress and start fresh, remove the Compose volumes:

```sh
docker compose down -v
docker compose up --build
```

## Check a chapter

The isolated chapter check prints only `PASS` or `FAIL` and does not use the live progress database:

```sh
docker compose run --rm --no-deps game python check_chapter.py 6
```

Replace `6` with a chapter number from 1 to 7.

## License

This project is available under the MIT License. See [LICENSE](LICENSE).
