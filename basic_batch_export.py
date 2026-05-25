#!/usr/bin/env python3
"""Basic batch export: gamelist.xml + media images per system from existing DBs."""

import argparse
import io
import json
import logging
import os
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from PIL import Image

from mister_media_db.etl import _load_dotenv, _clean_text
from mister_media_db.systems import SYSTEMS, System
from mister_media_db.utils import safe_game_name_for_filename

logger = logging.getLogger(__name__)

_REGION_PRIORITY = ["wor", "us", "eu", "jp"]
_MAX_DIM = 320
_JPEG_QUALITY = 80
_SCREENSHOT_AS_JPEG = False
_BOXART_AS_JPEG = False

# (screenscraper type, dir name, as_jpeg)
_ALL_MEDIA = [
    ("ss", "screenshot", _SCREENSHOT_AS_JPEG),
    ("box-2D", "boxart2d", _BOXART_AS_JPEG),
]
_MEDIA_CHOICES = [m[1] for m in _ALL_MEDIA]


def _pick_image(
    conn: sqlite3.Connection, screenscraper_id: int, media_type: str
) -> Optional[tuple[bytes, str]]:
    """Return (blob, content_type) for highest-priority region, or None."""
    rows = {
        row[0]: (row[1], row[2])
        for row in conn.execute(
            "SELECT region, blob, content_type FROM GameImages"
            " WHERE screenscraper_id = ? AND type = ?",
            (screenscraper_id, media_type),
        )
    }
    if not rows:
        return None
    for region in _REGION_PRIORITY:
        if region in rows:
            return rows[region]
    return next(iter(rows.values()))


def _pick_date(dates: list) -> Optional[str]:
    if not dates:
        return None
    by_region = {d.get("region", ""): d.get("text", "") for d in dates if d.get("text")}
    for region in _REGION_PRIORITY:
        if region in by_region:
            return by_region[region]
    return next(iter(by_region.values()), None)


def _pick_synopsis_en(synopsis: list) -> Optional[str]:
    for s in synopsis:
        if s.get("langue") == "en" and s.get("text"):
            return _clean_text(s["text"])
    for s in synopsis:
        if s.get("text"):
            return _clean_text(s["text"])
    return None


def _sub(parent: ET.Element, tag: str, text: Optional[str]) -> ET.Element:
    el = ET.SubElement(parent, tag)
    el.text = text or ""
    return el


def _process_and_write_image(blob: bytes, dest: Path, as_jpeg: bool) -> bool:
    """Process blob (resize, optionally convert to JPEG), write if not present. Returns True if written."""
    if dest.exists():
        return False
    try:
        img = Image.open(io.BytesIO(blob))
        resample = Image.Resampling.LANCZOS if as_jpeg else Image.Resampling.NEAREST
        img.thumbnail((_MAX_DIM, _MAX_DIM), resample)
        if as_jpeg:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(dest, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
        else:
            img.save(dest, format="PNG", optimize=True)
    except Exception as e:
        logger.warning(f"  image error {dest.name}: {e}")
        return False
    return True


def _write_gamelist(path: Path, root: ET.Element) -> None:
    ET.indent(root, space="  ")
    path.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")


def _export_games(
    conn: sqlite3.Connection,
    label: str,
    games: list[tuple[int, str, bytes]],
    slugs_by_game: dict[int, list[str]],
    system_dir: Path,
    media_types: Optional[list[str]] = None,
) -> None:
    """Core export loop: write images and build gamelist.xml for one system."""
    screenshot_dir = system_dir / "media" / "screenshot"
    boxart2d_dir = system_dir / "media" / "boxart2d"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    boxart2d_dir.mkdir(parents=True, exist_ok=True)

    total = len(games)
    logger.info(f"  {label}: {total} games to export")

    root = ET.Element("gameList")
    images_written = images_skipped = games_processed = 0

    for screenscraper_id, name, blob in games:
        games_processed += 1
        safe_name = safe_game_name_for_filename(name)

        try:
            jeu = json.loads(blob)["response"]["jeu"]
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.warning(f"  {label}/{name}: cannot parse response: {e}")
            jeu = {}

        screenshot_path: Optional[str] = None
        boxart2d_path: Optional[str] = None

        active_media = [m for m in _ALL_MEDIA if m[1] in media_types] if media_types else _ALL_MEDIA
        single_type_requested = media_types is not None and len(media_types) == 1
        for media_type, type_dir_name, as_jpeg in active_media:
            img = _pick_image(conn, screenscraper_id, media_type)
            if not img and single_type_requested:
                for fallback_ss_type, fallback_dir, _ in _ALL_MEDIA:
                    if fallback_dir != type_dir_name:
                        img = _pick_image(conn, screenscraper_id, fallback_ss_type)
                        if img:
                            break
            if not img:
                continue
            img_blob, _content_type = img
            ext = "jpg" if as_jpeg else "png"
            filename = f"{safe_name}.{ext}"
            dest = system_dir / "media" / type_dir_name / filename
            if _process_and_write_image(img_blob, dest, as_jpeg=as_jpeg):
                images_written += 1
            else:
                images_skipped += 1
            if media_type == "ss":
                screenshot_path = f"./media/screenshot/{filename}"
            else:
                boxart2d_path = f"./media/boxart2d/{filename}"

        game_el = ET.SubElement(root, "game")
        game_el.set("id", str(screenscraper_id))
        game_el.set("source", "ZaparooCompanion")
        _sub(game_el, "name", name)
        _sub(game_el, "desc", _pick_synopsis_en(jeu.get("synopsis", [])))
        _sub(game_el, "releasedate", _pick_date(jeu.get("dates", [])))
        _sub(game_el, "developer", jeu.get("developpeur", {}).get("text"))
        _sub(game_el, "publisher", jeu.get("editeur", {}).get("text"))
        _sub(game_el, "players", jeu.get("joueurs", {}).get("text"))
        if screenshot_path:
            _sub(game_el, "screenshot", screenshot_path)
        if boxart2d_path:
            _sub(game_el, "boxart2d", boxart2d_path)

        for slug in slugs_by_game.get(screenscraper_id, []):
            child_el = ET.SubElement(root, "game")
            child_el.set("parentid", str(screenscraper_id))
            child_el.set("source", "ZaparooCompanion")
            _sub(child_el, "path", f"{slug}.slug")

        if games_processed % 100 == 0 or games_processed == total:
            logger.info(f"  {label}: {games_processed}/{total} games processed")

    gamelist_path = system_dir / "gamelist.xml"
    _write_gamelist(gamelist_path, root)
    logger.info(
        f"  {label}: wrote {gamelist_path} "
        f"({images_written} new, {images_skipped} skipped)"
    )


class BasicBatchExporter:
    STEPS = ["export", "export-arcade"]

    def __init__(
        self,
        artifact_path: Optional[str] = None,
        db_path: str = "mister_media.db",
        arcade_db_path: str = "arcade_media.db",
        output_path: Optional[str] = None,
        media_types: Optional[list[str]] = None,
    ):
        _load_dotenv(Path(".env"))
        resolved_artifact = (
            Path(artifact_path) if artifact_path
            else Path(os.environ.get("ARTIFACT_PATH", "."))
        )
        self.artifact_path = resolved_artifact.resolve()
        if self.artifact_path != Path(".").resolve():
            _load_dotenv(self.artifact_path / ".env")

        def _resolve(p: str) -> Path:
            db = Path(p)
            return db if db.is_absolute() else self.artifact_path / db

        self.db_path = _resolve(db_path)
        self.arcade_db_path = _resolve(arcade_db_path)
        self.output_path = Path(output_path).resolve() if output_path else self.artifact_path / "gamelist-export"
        self.media_types = media_types

    def run(
        self,
        steps: Optional[list[str]] = None,
        systems: Optional[list[str]] = None,
    ) -> None:
        steps_to_run = steps if steps else self.STEPS
        for step in steps_to_run:
            if step not in self.STEPS:
                logger.error(f"Unknown step: {step}")
                continue
            logger.info(f"Running step: {step}")
            handler = getattr(self, f"step_{step.replace('-', '_')}", None)
            if handler:
                handler(systems)
            else:
                logger.warning(f"No handler for step: {step}")

    def step_export(self, systems: Optional[list[str]] = None) -> None:
        """Export gamelist.xml + media per system from mister_media.db."""
        if systems:
            system_map = {s.zaparoo_id: s for s in SYSTEMS}
            unknown = [sid for sid in systems if sid not in system_map]
            if unknown:
                logger.error(f"Unknown system IDs: {', '.join(unknown)}")
                return
            systems_to_run = [system_map[sid] for sid in systems]
        else:
            systems_to_run = SYSTEMS

        conn = sqlite3.connect(self.db_path)
        try:
            for system in systems_to_run:
                self._export_system(conn, system, self.media_types)
        finally:
            conn.close()

    def _export_system(self, conn: sqlite3.Connection, system: System, media_types: Optional[list[str]] = None) -> None:
        games = conn.execute(
            """
            SELECT g.screenscraper_id, g.name, gfr.blob
            FROM Games g
            JOIN GameFetchResponses gfr ON g.screenscraper_id = gfr.screenscraper_id
            WHERE g.system_id = ?
            ORDER BY g.name
            """,
            (system.zaparoo_id,),
        ).fetchall()

        slugs_by_game: dict[int, list[str]] = {}
        for row in conn.execute(
            """
            SELECT gzt.screenscraper_id, gzt.slug
            FROM GameZaparooTitles gzt
            JOIN Games g ON gzt.screenscraper_id = g.screenscraper_id
            WHERE g.system_id = ?
            ORDER BY gzt.id
            """,
            (system.zaparoo_id,),
        ):
            slugs_by_game.setdefault(row[0], []).append(row[1])

        _export_games(
            conn=conn,
            label=system.zaparoo_id,
            games=games,
            slugs_by_game=slugs_by_game,
            system_dir=self.output_path / system.zaparoo_id,
            media_types=media_types,
        )

    def step_export_arcade(self, _systems: Optional[list[str]] = None) -> None:
        """Export gamelist.xml + media for arcade from arcade_media.db."""
        conn = sqlite3.connect(self.arcade_db_path)
        try:
            games = conn.execute(
                """
                SELECT g.screenscraper_id, g.name, gfr.blob
                FROM Games g
                JOIN GameFetchResponses gfr ON g.screenscraper_id = gfr.screenscraper_id
                WHERE g.screenscraper_id != 0
                ORDER BY g.name
                """
            ).fetchall()

            slugs_by_game: dict[int, list[str]] = {}
            for row in conn.execute(
                "SELECT screenscraper_id, slug FROM GameZaparooTitles ORDER BY id"
            ):
                slugs_by_game.setdefault(row[0], []).append(row[1])

            _export_games(
                conn=conn,
                label="Arcade",
                games=games,
                slugs_by_game=slugs_by_game,
                system_dir=self.output_path / "Arcade",
                media_types=self.media_types,
            )
        finally:
            conn.close()


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Export gamelist.xml + media from existing MiSTer Media DB databases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Run both export steps for all systems
  %(prog)s --steps export               # Regular systems only
  %(prog)s --steps export-arcade        # Arcade only
  %(prog)s --steps export --systems nes snes
  %(prog)s --artifact-path /mnt/mister
        """,
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    parser.add_argument(
        "-a", "--artifact-path",
        default=None,
        metavar="PATH",
        help="Root path for DB files (default: ARTIFACT_PATH env var or current directory)",
    )

    parser.add_argument(
        "-d", "--db",
        default="mister_media.db",
        help="Main DB path, relative to artifact-path if not absolute (default: mister_media.db)",
    )

    parser.add_argument(
        "--arcade-db",
        default="arcade_media.db",
        help="Arcade DB path, relative to artifact-path if not absolute (default: arcade_media.db)",
    )

    parser.add_argument(
        "-o", "--output",
        default=None,
        metavar="PATH",
        help="Output root for gamelist-export/ (default: ./gamelist-export)",
    )

    parser.add_argument(
        "-s", "--steps",
        nargs="+",
        metavar="STEP",
        help="Steps to run. Available: export, export-arcade",
    )

    parser.add_argument(
        "-sys", "--systems",
        nargs="+",
        metavar="SYSTEM",
        help="Systems to process for 'export' step (e.g. nes snes genesis). Default: all systems",
    )

    parser.add_argument(
        "-m", "--media-types",
        nargs="+",
        choices=_MEDIA_CHOICES,
        metavar="TYPE",
        help=f"Media types to export. Choices: {', '.join(_MEDIA_CHOICES)}. Default: all",
    )

    return parser.parse_args(args)


def main(args=None):
    parsed = parse_args(args)
    setup_logging(parsed.verbose)
    exporter = BasicBatchExporter(
        artifact_path=parsed.artifact_path,
        db_path=parsed.db,
        arcade_db_path=parsed.arcade_db,
        output_path=parsed.output,
        media_types=parsed.media_types,
    )
    exporter.run(steps=parsed.steps, systems=parsed.systems)


if __name__ == "__main__":
    main()
