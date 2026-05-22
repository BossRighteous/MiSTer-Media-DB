#!/usr/bin/env python3
"""
recover_db.py — Row-by-row SQLite recovery from a potentially-corrupted DB.

Reads each row via rowid cursor-forward (WHERE rowid > last ORDER BY rowid LIMIT 1)
so a corrupt page causes a single-row error rather than aborting the entire table.
Each recovered row is written as an individual flushed/committed transaction.
GameImages is processed last and each blob is validated before insertion.

Usage:
    python recover_db.py
    python recover_db.py --source mister_media.db --dest mister_recover.db
    python recover_db.py --tables Games GameFetchResponses
    python recover_db.py --verbose --log detailed.log
"""

import argparse
import logging
import os
import signal
import sqlite3
import sys
from pathlib import Path
from typing import Callable, Optional


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value

# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------
_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    _shutdown = True
    print(
        f"\n[signal] Signal {signum} received — finishing current write, then closing cleanly...",
        flush=True,
    )


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)
if hasattr(signal, "SIGBREAK"):
    signal.signal(signal.SIGBREAK, _handle_signal)


# ---------------------------------------------------------------------------
# Image validation
# ---------------------------------------------------------------------------
_PNG_SIG = b"\x89PNG\r\n\x1a\n"
_JPEG_SOI = b"\xff\xd8\xff"
_JPEG_EOI = b"\xff\xd9"

# Minimum viable PNG: 8 sig + 25 IHDR + 12 IDAT + 12 IEND = 57 bytes
_PNG_MIN_LEN = 57


def _is_valid_png(data: bytes) -> bool:
    """Check PNG magic and presence of IEND chunk near end of file."""
    if len(data) < _PNG_MIN_LEN:
        return False
    if not data.startswith(_PNG_SIG):
        return False
    # IEND chunk type must appear within the final 20 bytes.
    # The full IEND marker (length=0 + type + CRC) is exactly 12 bytes at EOF.
    return b"IEND" in data[-20:]


def _is_valid_jpeg(data: bytes) -> bool:
    if len(data) < 4:
        return False
    return data[:3] == _JPEG_SOI and data[-2:] == _JPEG_EOI


def _validate_game_image(row_dict: dict) -> bool:
    blob = row_dict.get("blob")
    if not blob:
        return False
    data = bytes(blob)
    content_type = row_dict.get("content_type", "")
    if content_type == "image/png":
        return _is_valid_png(data)
    if content_type == "image/jpeg":
        return _is_valid_jpeg(data)
    # Unknown type: require non-empty blob only.
    return len(data) > 0


# ---------------------------------------------------------------------------
# Recovery DB schema
# Note: trailing comma on zaparoo_title removed vs. etl.py (that SQL is a bug there).
# ---------------------------------------------------------------------------
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS CSV (
    system_id TEXT PRIMARY KEY,
    game_count INTEGER,
    blob BLOB NOT NULL
);

CREATE TABLE IF NOT EXISTS Games (
    screenscraper_id INTEGER PRIMARY KEY,
    system_id TEXT NOT NULL,
    name TEXT NOT NULL,
    image_count INTEGER,
    zaparoo_title TEXT
);

CREATE TABLE IF NOT EXISTS GameImages (
    id INTEGER PRIMARY KEY,
    screenscraper_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    region TEXT NOT NULL DEFAULT '',
    content_type TEXT NOT NULL,
    blob BLOB NOT NULL,
    UNIQUE(screenscraper_id, type, region)
);

CREATE TABLE IF NOT EXISTS GameFetchResponses (
    screenscraper_id INTEGER PRIMARY KEY,
    blob BLOB NOT NULL
);

CREATE TABLE IF NOT EXISTS GameZaparooTitles (
    id INTEGER PRIMARY KEY,
    screenscraper_id INTEGER NOT NULL,
    slug TEXT NOT NULL,
    result TEXT NOT NULL,
    UNIQUE(screenscraper_id, slug)
);
"""

# Processing order: GameImages last (most likely corrupted).
_TABLE_DEFS: list[tuple[str, list[str], Optional[Callable]]] = [
    (
        "CSV",
        ["system_id", "game_count", "blob"],
        None,
    ),
    (
        "Games",
        ["screenscraper_id", "system_id", "name", "image_count", "zaparoo_title"],
        None,
    ),
    (
        "GameFetchResponses",
        ["screenscraper_id", "blob"],
        None,
    ),
    (
        "GameZaparooTitles",
        ["id", "screenscraper_id", "slug", "result"],
        None,
    ),
    (
        "GameImages",
        ["id", "screenscraper_id", "type", "region", "content_type", "blob"],
        _validate_game_image,
    ),
]
_TABLE_NAMES = [td[0] for td in _TABLE_DEFS]

# After this many consecutive rowid read failures, abandon the table.
_MAX_CONSECUTIVE_ERRORS = 500


# ---------------------------------------------------------------------------
# Per-table recovery
# ---------------------------------------------------------------------------
def recover_table(
    src: sqlite3.Connection,
    dst: sqlite3.Connection,
    table: str,
    columns: list[str],
    validate_fn: Optional[Callable] = None,
) -> tuple[int, int, int]:
    """
    Copy rows one at a time using a rowid cursor-forward query.
    Each successful row is written as its own committed transaction.
    Returns (copied, skipped, errors).
    """
    col_list = ", ".join(columns)
    placeholders = ", ".join("?" * len(columns))
    insert_sql = (
        f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES ({placeholders})"
    )

    # Estimate total for progress context.  May fail on corrupt table — that's OK.
    total_hint: str = "?"
    try:
        n = src.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        total_hint = f"{n:,}"
    except sqlite3.DatabaseError as exc:
        logging.warning(f"[{table}] COUNT(*) failed: {exc}")

    print(f"\n[{table}] Starting — ~{total_hint} rows estimated", flush=True)
    logging.info(f"[{table}] Starting — ~{total_hint} rows estimated")

    last_rowid = 0
    consecutive_errors = 0
    copied = 0
    skipped = 0
    errors = 0

    while not _shutdown:
        # Cursor-forward: next rowid after the last successfully read one.
        try:
            row = src.execute(
                f"SELECT rowid, {col_list} FROM {table}"
                f" WHERE rowid > ? ORDER BY rowid LIMIT 1",
                (last_rowid,),
            ).fetchone()
            consecutive_errors = 0
        except sqlite3.DatabaseError as exc:
            logging.error(
                f"[{table}] rowid>{last_rowid}: read error: {exc}"
            )
            errors += 1
            consecutive_errors += 1
            last_rowid += 1  # skip over the offending rowid and try next
            if consecutive_errors >= _MAX_CONSECUTIVE_ERRORS:
                msg = (
                    f"[{table}] ABORT: {_MAX_CONSECUTIVE_ERRORS} consecutive read errors. "
                    f"See log for details."
                )
                print(msg, flush=True)
                logging.error(msg)
                break
            continue

        if row is None:
            break  # table exhausted

        actual_rowid = row[0]
        data = row[1:]
        pk = data[0] if data else "?"

        # Optional blob validation (used for GameImages).
        if validate_fn is not None:
            row_dict = dict(zip(columns, data))
            try:
                valid = validate_fn(row_dict)
            except Exception as exc:
                logging.error(
                    f"[{table}] rowid={actual_rowid} pk={pk}: validate error: {exc}"
                )
                valid = False

            if not valid:
                blob_len = len(bytes(row_dict.get("blob") or b""))
                logging.warning(
                    f"[{table}] rowid={actual_rowid} pk={pk}: "
                    f"invalid blob (content_type={row_dict.get('content_type')!r}, "
                    f"blob_len={blob_len}) — skipping"
                )
                skipped += 1
                print(
                    f"[{table}] rowid={actual_rowid} pk={pk}: SKIP invalid blob "
                    f"({copied:,}/{total_hint} copied, {skipped:,} skipped)",
                    flush=True,
                )
                last_rowid = actual_rowid
                continue

        # Write single-row transaction.
        try:
            dst.execute(insert_sql, data)
            dst.commit()
            copied += 1
            print(
                f"[{table}] rowid={actual_rowid} pk={pk}: OK ({copied:,}/{total_hint})",
                flush=True,
            )
            logging.debug(f"[{table}] rowid={actual_rowid} pk={pk}: copied")
        except sqlite3.DatabaseError as exc:
            logging.error(
                f"[{table}] rowid={actual_rowid} pk={pk}: write error: {exc}"
            )
            errors += 1

        last_rowid = actual_rowid

    status = "INTERRUPTED" if _shutdown else "COMPLETE"
    summary = (
        f"[{table}] {status}: {copied:,} copied, "
        f"{skipped:,} skipped (invalid blob), {errors:,} errors"
    )
    print(summary, flush=True)
    logging.info(summary)
    return copied, skipped, errors


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--artifact-path", default=None,
        help="Root path for DB files (overrides ARTIFACT_PATH env var; default: ./)",
    )
    parser.add_argument(
        "--source", default=None,
        help="Possibly-corrupt source DB (default: <artifact-path>/mister_media.db)",
    )
    parser.add_argument(
        "--dest", default=None,
        help="Destination recovery DB (default: <artifact-path>/mister_recover.db)",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        choices=_TABLE_NAMES,
        metavar="TABLE",
        help=(
            f"Only recover these tables (default: all in safe order). "
            f"Choices: {', '.join(_TABLE_NAMES)}"
        ),
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Write DEBUG-level entries to log file",
    )
    parser.add_argument(
        "--log", default="recover.log",
        help="Log file path (default: recover.log)",
    )
    args = parser.parse_args()

    # Resolve artifact path: arg > ARTIFACT_PATH env > ./
    _load_dotenv(Path(".env"))
    artifact_path = Path(
        args.artifact_path or os.environ.get("ARTIFACT_PATH", ".")
    ).resolve()
    if artifact_path != Path(".").resolve():
        _load_dotenv(artifact_path / ".env")

    # File log captures everything; stderr only shows WARNING+.
    log_level = logging.DEBUG if args.verbose else logging.INFO
    file_handler = logging.FileHandler(args.log, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))

    logging.basicConfig(level=log_level, handlers=[file_handler, stderr_handler])

    def _resolve_db(arg: Optional[str], default_name: str) -> Path:
        p = Path(arg) if arg else Path(default_name)
        return p if p.is_absolute() else (artifact_path / p)

    src_path = _resolve_db(args.source, "mister_media.db").resolve()
    dst_path = _resolve_db(args.dest, "mister_recover.db").resolve()
    log_path = Path(args.log).resolve()

    if not src_path.exists():
        print(f"ERROR: source not found: {src_path}")
        sys.exit(1)

    if dst_path.exists():
        print(
            f"WARNING: {dst_path} already exists.\n"
            f"Existing rows will be skipped via INSERT OR IGNORE (safe to resume).\n"
            f"Continue? [y/N] ",
            end="",
            flush=True,
        )
        if input().strip().lower() != "y":
            print("Aborted.")
            sys.exit(0)

    print(f"Artifact: {artifact_path}", flush=True)
    print(f"Source  : {src_path}", flush=True)
    print(f"Dest    : {dst_path}", flush=True)
    print(f"Log     : {log_path}", flush=True)
    selected = args.tables or "(all, GameImages last)"
    print(f"Tables : {selected}", flush=True)
    logging.info(f"Recovery started: source={src_path} dest={dst_path} tables={selected}")

    # Open source read-only to avoid any writes to the corrupt file.
    src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True)
    src.row_factory = None

    dst = sqlite3.connect(dst_path)
    dst.execute("PRAGMA journal_mode=WAL")
    dst.execute("PRAGMA synchronous=NORMAL")
    dst.execute("PRAGMA foreign_keys=OFF")
    dst.executescript(_SCHEMA_SQL)
    dst.commit()

    tables_to_run = (
        [td for td in _TABLE_DEFS if td[0] in args.tables]
        if args.tables
        else _TABLE_DEFS
    )

    grand_copied = grand_skipped = grand_errors = 0

    try:
        for table, columns, validate_fn in tables_to_run:
            if _shutdown:
                print("Shutdown flag set — stopping before next table.", flush=True)
                logging.info("Shutdown: stopping before next table.")
                break
            c, s, e = recover_table(src, dst, table, columns, validate_fn)
            grand_copied += c
            grand_skipped += s
            grand_errors += e
    finally:
        print("\nClosing connections...", flush=True)
        try:
            dst.close()
        except Exception:
            pass
        try:
            src.close()
        except Exception:
            pass

        final = (
            f"\nFINAL: {grand_copied:,} rows copied, "
            f"{grand_skipped:,} skipped (invalid blob), "
            f"{grand_errors:,} errors\n"
            f"Log: {log_path}"
        )
        print(final, flush=True)
        logging.info(final.strip())


if __name__ == "__main__":
    main()
