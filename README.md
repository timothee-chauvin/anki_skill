# anki skill

LLMs have gotten good enough to create valuable anki cards. Two ingredients that help a lot with that, and that this skill implements:

* showing the LLM a sample of your own collection
* telling the LLMs to search for related cards and concepts before adding anything

## Do I need ankiconnect?

No, I try to avoid third-party dependencies that look like servers when possible, and it turns out not much code is needed (see [anki_add.py](/anki_add.py)).

## Headless machines (AnkiWeb sync)

On a machine without the desktop app, run once:

```
uv run python anki_add.py login          # stores an AnkiWeb auth key (not the password)
uv run python anki_add.py full_download  # initial download of collection + media
```

The presence of the resulting `~/.config/anki_skill/sync.json` switches `search`/`add` into sync mode: they sync with AnkiWeb before (and, for `add`, after) touching the collection. Where the desktop app is installed, don't run `login` — the app owns syncing, and `search` reads a snapshot so the app can stay open.

## List of things you need to change before use

1. replace my card subset in the skill with yours; change other instructions as needed
1. change the hardcoded constants at the top of [anki_add.py](/anki_add.py)
1. move SKILL.md to an appropriate location

You're on your own in any case, but particularly so if you're not on Linux.

