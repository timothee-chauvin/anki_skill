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

## LaTeX cards

Anki compiles `[latex]...[/latex]` blocks while *rendering* a card, so on a headless machine nothing ever triggers it and cards sync out referencing images that exist nowhere. `add` therefore compiles them itself, and aborts rather than adding a card whose LaTeX failed.

You need a TeX install covering whatever your notetype's `latexPre` loads, plus `dvisvgm`:

```
sudo apt install texlive-latex-base texlive-latex-extra texlive-science texlive-fonts-extra dvisvgm
```

Your notetype must be set to SVG output:

```python
nt = col.models.by_name("b")
nt["latexsvg"] = True
col.models.update_dict(nt)
```

The PNG path shells out to `dvipng`, and Debian/Ubuntu's dvipng 1.15 segfaults on any document loading `\usepackage{pagecolor}` — a common way to bake a background colour into the image. `dvisvgm` handles the same preamble fine. Existing `latex-*.png` files stay valid, since the filename is a hash of the LaTeX body alone and doesn't depend on the preamble or the output format.

Anki's own "generate LaTeX images" preference stays off, and doesn't need turning on: `render_latex` skips images already present in media, so cards added this way display everywhere, while a deck you downloaded from someone else still gets no way to compile anything. TeX also runs with `openin_any=p`, which denies `\input`/`\openin` outside the working directory — LaTeX is a programming language, and would otherwise read any file you can and typeset it into an image that then syncs to AnkiWeb.

## List of things you need to change before use

1. replace my card subset in the skill with yours; change other instructions as needed
1. change the hardcoded constants at the top of [anki_add.py](/anki_add.py)
1. move SKILL.md to an appropriate location

You're on your own in any case, but particularly so if you're not on Linux.

