#!/usr/bin/env python3
"""Add cards to Anki collection directly, closing Anki if running."""

import datetime
from importlib.metadata import version as pkg_version
from pathlib import Path
import subprocess
import sys
import time

import fire
from anki.collection import Collection

COLLECTION_PATH = "/home/u/.local/share/Anki2/User 1/collection.anki2"
NOTETYPE = "b"
DECK = "Kn"


def _get_installed_anki_version() -> str | None:
    try:
        result = subprocess.run(
            ["anki", "--version"], capture_output=True, text=True, timeout=15
        )
        for line in result.stdout.strip().splitlines():
            if line.startswith("Anki ") and not line.startswith("Anki starting"):
                return line.split()[-1]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _check_version():
    """Guard against opening the collection with a pip ``anki`` whose schema
    differs from the desktop app: a mismatched library silently migrates the
    DB on open and can corrupt the collection for the desktop app."""
    desktop = _get_installed_anki_version()
    if desktop is None:
        print("Warning: could not detect desktop Anki version", file=sys.stderr)
        return
    lib = pkg_version("anki")
    desktop_parts = [int(x) for x in desktop.split(".")]
    lib_parts = [int(x) for x in lib.split(".")]
    if lib_parts[: len(desktop_parts)] != desktop_parts:
        major_minor = ".".join(str(p) for p in desktop_parts[:2])
        print(
            f"Version mismatch: pip anki is {lib}, desktop Anki is {desktop}.\n"
            f"Match the pip dependency to the desktop app:\n"
            f"  cd ~/prog/AI/anki && uv add 'anki~={major_minor}.0'",
            file=sys.stderr,
        )
        sys.exit(1)


def _close_anki():
    result = subprocess.run(["pgrep", "-x", "anki"], capture_output=True)
    if result.returncode == 0:
        print("Closing Anki...", file=sys.stderr)
        subprocess.run(["pkill", "-x", "anki"])
        for _ in range(30):
            time.sleep(0.5)
            if subprocess.run(["pgrep", "-x", "anki"], capture_output=True).returncode != 0:
                return
        print("Failed to close Anki", file=sys.stderr)
        sys.exit(1)


def _make_metadata(model: str, source: str = "/anki skill") -> str:
    today = datetime.date.today().isoformat()
    return (
        f'<div><br></div>'
        f'<div style="font-size: 0.7em; color: gray;">'
        f'{{"from":"{source}","model":"{model}","added":"{today}"}}'
        f'</div>'
    )


def add(front_file: str, back_file: str, model: str, notetype: str = NOTETYPE, deck: str = DECK):
    """Add a card to Anki. Front and back are read from HTML files.

    Args:
        front_file: Path to HTML file containing the front of the card.
        back_file: Path to HTML file containing the back of the card.
        model: ID of the AI model that generated the card.
        notetype: Anki notetype name.
        deck: Anki deck name.
    """
    front = Path(front_file).read_text()
    back = Path(back_file).read_text()

    _check_version()
    _close_anki()

    col = Collection(COLLECTION_PATH)
    try:
        nt = col.models.by_name(notetype)
        if nt is None:
            print(f"Notetype '{notetype}' not found", file=sys.stderr)
            sys.exit(1)

        note = col.new_note(nt)
        note["Front"] = front
        note["Back"] = back + _make_metadata(model)

        deck_id = col.decks.id_for_name(deck)
        col.add_note(note, deck_id)
        print(f"Added card to {deck} (id={note.id})")
    finally:
        col.close()


def search(query: str, limit: int = 50):
    """Search non-suspended cards in the Kn deck by keywords.

    Args:
        query: Keywords to search for. Pass plain words; the script enforces
            the deck and suspension filters. Anki search operators in the
            query string are passed through but should not be needed.
        limit: Max number of cards to print.
    """
    _check_version()
    _close_anki()

    full_query = f'deck:{DECK} -is:suspended {query}'
    col = Collection(COLLECTION_PATH)
    try:
        card_ids = col.find_cards(full_query)
        total = len(card_ids)
        print(f"# {total} match(es) for: {full_query}")
        if total == 0:
            return
        seen_notes = set()
        shown = 0
        for cid in card_ids:
            if shown >= limit:
                print(f"# ... {total - shown} more (raise --limit to see all)")
                break
            card = col.get_card(cid)
            note = card.note()
            if note.id in seen_notes:
                continue
            seen_notes.add(note.id)
            shown += 1
            print(f"=== {shown} ===")
            print("FRONT:")
            print(note["Front"])
            print("BACK:")
            print(note["Back"])
            print()
    finally:
        col.close()


if __name__ == "__main__":
    fire.Fire({"add": add, "search": search})
