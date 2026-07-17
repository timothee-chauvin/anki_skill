#!/usr/bin/env python3
"""Add cards to Anki collection directly, closing Anki if running.

On headless machines (no desktop Anki), run `login` once then `full_download`;
search/add will then sync with AnkiWeb around each invocation.
"""

import datetime
import getpass
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from importlib.metadata import version as pkg_version
from pathlib import Path

import fire
import orjson
from anki.collection import Collection
from anki.sync import SyncAuth, SyncOutput

COLLECTION_PATH = Path.home() / ".local/share/Anki2/User 1/collection.anki2"
SYNC_CONFIG_PATH = Path.home() / ".config/anki_skill/sync.json"
VERSION_CACHE_PATH = Path.home() / ".cache/anki_skill/desktop_version.json"
NOTETYPE = "b"
DECK = "Kn"


def _get_installed_anki_version() -> str | None:
    binary = shutil.which("anki")
    if binary is None:
        return None
    # `anki --version` boots the whole desktop binary (~1s), so cache on mtime
    mtime = os.path.getmtime(binary)
    if VERSION_CACHE_PATH.exists():
        cached = orjson.loads(VERSION_CACHE_PATH.read_bytes())
        if cached["binary"] == binary and cached["mtime"] == mtime:
            return cached["version"]
    try:
        result = subprocess.run(
            ["anki", "--version"], capture_output=True, text=True, timeout=15
        )
    except subprocess.TimeoutExpired:
        return None
    version = None
    for line in result.stdout.strip().splitlines():
        if line.startswith("Anki ") and not line.startswith("Anki starting"):
            version = line.split()[-1]
    if version is not None:
        VERSION_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        VERSION_CACHE_PATH.write_bytes(
            orjson.dumps({"binary": binary, "mtime": mtime, "version": version})
        )
    return version


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


def _load_auth() -> SyncAuth | None:
    if not SYNC_CONFIG_PATH.exists():
        return None
    cfg = orjson.loads(SYNC_CONFIG_PATH.read_bytes())
    auth = SyncAuth(hkey=cfg["hkey"])
    if cfg.get("endpoint"):
        auth.endpoint = cfg["endpoint"]
    return auth


def _save_auth(hkey: str, endpoint: str):
    SYNC_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    SYNC_CONFIG_PATH.parent.chmod(0o700)
    SYNC_CONFIG_PATH.write_bytes(orjson.dumps({"hkey": hkey, "endpoint": endpoint}))
    SYNC_CONFIG_PATH.chmod(0o600)


def _sync_collection(col: Collection, auth: SyncAuth):
    out = col.sync_collection(auth, sync_media=False)
    if out.server_message:
        print(out.server_message, file=sys.stderr)
    if out.new_endpoint:
        _save_auth(auth.hkey, out.new_endpoint)
    if out.required != SyncOutput.NO_CHANGES:
        state = SyncOutput.ChangesRequired.Name(out.required)
        sys.exit(
            f"AnkiWeb requires a full sync ({state}); refusing to resolve automatically.\n"
            f"Run `anki_add.py full_download` to REPLACE the local collection with "
            f"AnkiWeb's copy, or resolve from the desktop app."
        )
    return out


def _sync_media(col: Collection, auth: SyncAuth):
    print("Syncing media...", file=sys.stderr)
    col.sync_media(auth)
    time.sleep(0.5)
    while col.media_sync_status().active:  # raises if the sync failed
        time.sleep(0.2)


def _open_snapshot(tmpdir: str) -> Collection:
    """Query a copy of the collection so the desktop app can stay open."""
    if not COLLECTION_PATH.exists():
        sys.exit(
            f"No collection at {COLLECTION_PATH}. On a headless machine, run "
            f"`anki_add.py login` then `anki_add.py full_download` first."
        )
    snap = Path(tmpdir) / "collection.anki2"
    src = sqlite3.connect(f"file:{COLLECTION_PATH}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(snap)
        src.backup(dst)
        dst.close()
    finally:
        src.close()
    return Collection(str(snap))


def _open_collection() -> Collection:
    COLLECTION_PATH.parent.mkdir(parents=True, exist_ok=True)
    return Collection(str(COLLECTION_PATH))


def login():
    """One-time AnkiWeb login: exchanges credentials for an auth key (the
    password is not stored). Meant for headless machines; where the desktop
    app is installed, it owns syncing and this should not be used."""
    username = input("AnkiWeb email: ")
    password = getpass.getpass("AnkiWeb password: ")
    col = _open_collection()
    try:
        auth = col.sync_login(username=username, password=password, endpoint=None)
    finally:
        col.close()
    _save_auth(auth.hkey, auth.endpoint)
    print(f"Auth key saved to {SYNC_CONFIG_PATH}. search/add will now sync with AnkiWeb.")


def full_download():
    """Replace the local collection with AnkiWeb's copy (local changes are lost)."""
    auth = _load_auth()
    if auth is None:
        sys.exit("No sync config; run `anki_add.py login` first.")
    if input("This OVERWRITES the local collection with AnkiWeb's copy. Type 'yes': ") != "yes":
        sys.exit("Aborted.")
    _close_anki()
    col = _open_collection()
    try:
        out = col.sync_collection(auth, sync_media=False)
        if out.required == SyncOutput.NO_CHANGES:
            print("Collection already in sync.")
        else:
            col.close_for_full_sync()
            col.full_upload_or_download(
                auth=auth, server_usn=out.server_media_usn, upload=False
            )
            col.reopen(after_full_sync=True)
            print("Downloaded collection from AnkiWeb.")
        _sync_media(col, auth)
    finally:
        col.close()


def _make_metadata(model: str, source: str = "/anki skill") -> str:
    today = datetime.date.today().isoformat()
    payload = orjson.dumps({"from": source, "model": model, "added": today}).decode()
    return (
        f'<div><br></div>'
        f'<div style="font-size: 0.7em; color: gray;">'
        f'{payload}'
        f'</div>'
    )


def add(cards_dir: str, model: str, notetype: str = NOTETYPE, deck: str = DECK):
    """Add cards to Anki. Reads N_front.html / N_back.html pairs from a directory.

    Args:
        cards_dir: Directory containing 1_front.html, 1_back.html, 2_front.html, ...
            All cards are added in a single invocation.
        model: ID of the AI model that generated the cards.
        notetype: Anki notetype name.
        deck: Anki deck name.
    """
    fronts = sorted(
        Path(cards_dir).glob("*_front.html"), key=lambda p: int(p.name.split("_")[0])
    )
    if not fronts:
        sys.exit(f"No *_front.html files in {cards_dir}")
    cards = []
    for front_path in fronts:
        back_path = front_path.with_name(front_path.name.replace("_front", "_back"))
        if not back_path.exists():
            sys.exit(f"Missing {back_path}")
        cards.append((front_path.read_text(), back_path.read_text()))

    _check_version()
    _close_anki()
    auth = _load_auth()
    col = _open_collection()
    try:
        if auth is not None:
            _sync_collection(col, auth)
        nt = col.models.by_name(notetype)
        if nt is None:
            sys.exit(f"Notetype '{notetype}' not found")
        deck_id = col.decks.id_for_name(deck)
        metadata = _make_metadata(model)
        for front, back in cards:
            note = col.new_note(nt)
            note["Front"] = front
            note["Back"] = back + metadata
            col.add_note(note, deck_id)
            print(f"Added card to {deck} (id={note.id})")
        if auth is not None:
            _sync_collection(col, auth)
            _sync_media(col, auth)
    finally:
        col.close()


def search(*queries: str, limit: int = 50):
    """Search non-suspended cards in the Kn deck by keywords.

    Args:
        queries: One or more keyword queries, all run in a single invocation.
            Pass plain words; the script enforces the deck and suspension
            filters. Words within a query are ANDed.
        limit: Max number of cards to print per query.
    """
    if not queries:
        sys.exit("No queries given.")
    auth = _load_auth()
    tmpdir = None
    if auth is None:
        tmpdir = tempfile.mkdtemp(prefix="anki_search_")
        col = _open_snapshot(tmpdir)
    else:
        _close_anki()
        col = _open_collection()
        _sync_collection(col, auth)
    try:
        seen_notes = set()
        for query in queries:
            full_query = f"deck:{DECK} -is:suspended {query}"
            card_ids = col.find_cards(full_query)
            print(f"# {len(card_ids)} match(es) for: {full_query}")
            shown = 0
            skipped = 0
            for cid in card_ids:
                if shown >= limit:
                    print("# ... more matches (raise --limit to see all)")
                    break
                note = col.get_card(cid).note()
                if note.id in seen_notes:
                    skipped += 1
                    continue
                seen_notes.add(note.id)
                shown += 1
                print(f"=== {shown} ===")
                print("FRONT:")
                print(note["Front"])
                print("BACK:")
                print(note["Back"])
                print()
            if skipped:
                print(f"# {skipped} note(s) omitted (already shown above)")
            print()
    finally:
        col.close()
        if tmpdir is not None:
            shutil.rmtree(tmpdir)


if __name__ == "__main__":
    fire.Fire(
        {"add": add, "search": search, "login": login, "full_download": full_download}
    )
