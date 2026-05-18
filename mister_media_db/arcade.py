"""Arcade ETL workflow for MiSTer .mra-based arcade mappings."""

import atexit
import json
import os
import signal
import sqlite3
import logging
import time
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from zoneinfo import ZoneInfo

from mister_media_db.etl import _load_dotenv
from mister_media_db.media_types import MEDIA_TYPE_MAP, MediaType

logger = logging.getLogger(__name__)


def _sigbreak_handler(signum, frame):
    raise KeyboardInterrupt()


if hasattr(signal, "SIGBREAK"):
    signal.signal(signal.SIGBREAK, _sigbreak_handler)


_SS_ENV_VARS = [
    "SS_DEV_ID",
    "SS_DEV_PASSWORD",
    "SS_USER_ID",
    "SS_USER_PASSWORD",
    "SS_SOFTNAME",
    "SS_THREADS",
]


class ArcadeETLWorkflow:
    """Manages arcade ETL steps for MiSTer .mra files."""

    STEPS = [
        "prepare-db",
        "mra-scan",
        "fetch-game-details",
        "download-images",
        "export-media",
        "export-zaparoo-map",
    ]

    def __init__(
        self,
        db_path: str = "arcade_media.db",
        artifact_path: Optional[str] = None,
        mra_path: Optional[str] = None,
    ):
        self.conn: Optional[sqlite3.Connection] = None
        _load_dotenv(Path(".env"))
        resolved_artifact = Path(artifact_path) if artifact_path else Path(os.environ.get("ARTIFACT_PATH", "."))
        self.artifact_path = resolved_artifact.resolve()
        if self.artifact_path != Path(".").resolve():
            _load_dotenv(self.artifact_path / ".env")
        db = Path(db_path)
        self.db_path = db if db.is_absolute() else self.artifact_path / db
        resolved_mra = mra_path or os.environ.get("MRA_PATH")
        self.mra_path = Path(resolved_mra).resolve() if resolved_mra else None
        missing = [k for k in _SS_ENV_VARS if not os.environ.get(k)]
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")
        self.ss_dev_id = os.environ["SS_DEV_ID"]
        self.ss_dev_password = os.environ["SS_DEV_PASSWORD"]
        self.ss_user_id = os.environ["SS_USER_ID"]
        self.ss_user_password = os.environ["SS_USER_PASSWORD"]
        self.ss_softname = os.environ["SS_SOFTNAME"]
        try:
            self.ss_threads = max(1, int(os.environ.get("SS_THREADS", "") or "1"))
        except (ValueError, TypeError):
            self.ss_threads = 1

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        atexit.register(self.close)
        logger.info(f"Connected to database: {self.db_path}")

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed")

    def run(self, steps: Optional[List[str]] = None):
        """Execute arcade ETL workflow."""
        self.connect()
        try:
            steps_to_run = steps if steps else self.STEPS
            for step in steps_to_run:
                if step not in self.STEPS:
                    logger.error(f"Unknown step: {step}")
                    continue
                logger.info(f"Running step: {step}")
                self._execute_step(step)
        except KeyboardInterrupt:
            logger.warning("Interrupted — closing database")
            raise
        finally:
            self.close()

    def _execute_step(self, step: str):
        handler = getattr(self, f"step_{step.replace('-', '_')}", None)
        if handler:
            handler()
        else:
            logger.warning(f"No handler for step: {step}")

    def step_prepare_db(self):
        """Prepare database schema. Errors if tables already exist."""
        try:
            self.conn.executescript("""
                CREATE TABLE MRAs (
                    name TEXT PRIMARY KEY,
                    setname TEXT NOT NULL,
                    screenscraper_id INTEGER NOT NULL,
                    parent TEXT NOT NULL,
                    blob BLOB NOT NULL
                );

                CREATE TABLE Games (
                    screenscraper_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    image_count INTEGER
                );

                CREATE TABLE GameImages (
                    id INTEGER PRIMARY KEY,
                    screenscraper_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    region TEXT NOT NULL DEFAULT '',
                    content_type TEXT NOT NULL,
                    blob BLOB NOT NULL,
                    UNIQUE(screenscraper_id, type, region)
                );

                CREATE TABLE GameFetchResponses (
                    screenscraper_id INTEGER PRIMARY KEY,
                    blob BLOB NOT NULL
                );

                CREATE TABLE GameZaparooTitles (
                    id INTEGER PRIMARY KEY,
                    screenscraper_id INTEGER NOT NULL,
                    slug TEXT NOT NULL,
                    result TEXT NOT NULL,
                    UNIQUE(screenscraper_id, slug)
                );
            """)
            self.conn.commit()
            logger.info("Database schema created")
        except sqlite3.OperationalError as e:
            logger.error(f"prepare-db failed: {e}")

    def step_mra_scan(self):
        """Scan .mra XML files from mra_path and insert into MRAs table."""
        if self.mra_path is None:
            logger.error("  mra-scan: MRA_PATH not set — skipping (set via --mra-path or MRA_PATH env var)")
            return
        mra_files = list(self.mra_path.rglob("*.mra"))
        logger.info(f"  mra-scan: found {len(mra_files)} .mra files in {self.mra_path}")

        inserted = skipped = errors = 0
        for mra_file in mra_files:
            blob = mra_file.read_bytes()
            try:
                root = ET.fromstring(blob.decode("utf-8", errors="replace"))
            except ET.ParseError as e:
                logger.warning(f"  {mra_file.name}: XML parse error: {e}")
                errors += 1
                continue

            name = (root.findtext("n") or "").strip()
            setname = (root.findtext("setname") or "").strip()
            parent = (root.findtext("parent") or "").strip()

            if not name or not setname:
                logger.warning(f"  {mra_file.name}: missing <n> or <setname>, skipping")
                errors += 1
                continue

            cursor = self.conn.execute(
                "INSERT OR IGNORE INTO MRAs (name, setname, screenscraper_id, parent, blob)"
                " VALUES (?, ?, ?, ?, ?)",
                (name, setname, 0, parent, blob),
            )
            if cursor.rowcount:
                inserted += 1
            else:
                skipped += 1

        self.conn.commit()
        logger.info(f"  mra-scan: {inserted} inserted, {skipped} already present, {errors} errors")

    def _fetch_url(self, url: str, label: str = "") -> Optional[bytes]:
        try:
            with urllib.request.urlopen(url) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            logger.error(f"  HTTP {e.code} fetching {label or url}: {e.reason}")
            return None
        except urllib.error.URLError as e:
            logger.error(f"  URL error fetching {label or url}: {e.reason}")
            return None

    def _fetch_game_detail(self, game_id: int) -> tuple[int, Optional[bytes]]:
        url = (
            "https://api.screenscraper.fr/api2/jeuInfos.php"
            f"?gameid={game_id}"
            f"&devid={urllib.parse.quote(self.ss_dev_id)}"
            f"&devpassword={urllib.parse.quote(self.ss_dev_password)}"
            f"&softname={urllib.parse.quote(self.ss_softname)}"
            f"&ssid={urllib.parse.quote(self.ss_user_id)}"
            f"&sspassword={urllib.parse.quote(self.ss_user_password)}"
            f"&output=json"
        )
        return game_id, self._fetch_url(url, f"game {game_id}")

    def _fetch_remaining_requests(self) -> int:
        url = (
            "https://api.screenscraper.fr/api2/ssuserInfos.php"
            f"?devid={urllib.parse.quote(self.ss_dev_id)}"
            f"&devpassword={urllib.parse.quote(self.ss_dev_password)}"
            f"&softname={urllib.parse.quote(self.ss_softname)}"
            f"&ssid={urllib.parse.quote(self.ss_user_id)}"
            f"&sspassword={urllib.parse.quote(self.ss_user_password)}"
            f"&output=json"
        )
        try:
            with urllib.request.urlopen(url) as response:
                payload = json.loads(response.read())
            ssuser = payload["response"]["ssuser"]
            requests_today = int(ssuser["requeststoday"])
            max_requests = int(ssuser["maxrequestsperday"])
            remaining = max_requests - requests_today
            logger.info(f"  Rate limit: {requests_today}/{max_requests} today ({remaining} remaining)")
            return remaining
        except Exception as e:
            logger.warning(f"  Could not fetch rate limit info: {e}")
            return -1

    def _sleep_until_paris_midnight(self) -> None:
        paris = ZoneInfo("Europe/Paris")
        now = datetime.now(paris)
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        sleep_seconds = (midnight - now).total_seconds()
        logger.warning(
            f"  Rate limit reached. Sleeping {sleep_seconds:.0f}s until midnight Paris time ({midnight.isoformat()})"
        )
        time.sleep(sleep_seconds)

    def step_fetch_game_details(self):
        """Fetch game details from ScreenScraper for MRAs with a resolved screenscraper_id."""
        game_ids = [
            row[0]
            for row in self.conn.execute(
                """
                SELECT m.screenscraper_id FROM MRAs m
                LEFT JOIN GameFetchResponses gfr ON m.screenscraper_id = gfr.screenscraper_id
                WHERE m.screenscraper_id != 0 AND gfr.screenscraper_id IS NULL
                """
            )
        ]
        total = self.conn.execute(
            "SELECT COUNT(*) FROM MRAs WHERE screenscraper_id != 0"
        ).fetchone()[0]
        logger.info(f"  fetch-game-details: {len(game_ids)}/{total} games to fetch")

        for batch_start in range(0, len(game_ids), self.ss_threads):
            batch = game_ids[batch_start:batch_start + self.ss_threads]
            with ThreadPoolExecutor(max_workers=len(batch)) as executor:
                futures = [executor.submit(self._fetch_game_detail, gid) for gid in batch]
            last_rate_info: Optional[tuple[int, int]] = None
            for future in futures:
                game_id, blob = future.result()
                if blob is None:
                    continue
                self.conn.execute(
                    "INSERT OR IGNORE INTO GameFetchResponses (screenscraper_id, blob) VALUES (?, ?)",
                    (game_id, blob),
                )
                self.conn.commit()
                try:
                    payload = json.loads(blob)
                    ssuser = payload["response"]["ssuser"]
                    requests_today = int(ssuser["requeststoday"])
                    max_requests = int(ssuser["maxrequestsperday"])
                    last_rate_info = (requests_today, max_requests)
                    logger.info(f"  game {game_id}: fetched ({len(blob)} bytes), {requests_today}/{max_requests} requests today")
                except (KeyError, ValueError, json.JSONDecodeError):
                    logger.warning(f"  Could not parse rate limit from response for game {game_id}")
            if last_rate_info and last_rate_info[0] >= last_rate_info[1]:
                self._sleep_until_paris_midnight()

        done_count = self.conn.execute(
            """
            SELECT COUNT(*) FROM GameFetchResponses gfr
            JOIN MRAs m ON gfr.screenscraper_id = m.screenscraper_id
            WHERE m.screenscraper_id != 0
            """
        ).fetchone()[0]
        remaining = total - done_count
        if remaining:
            logger.warning(f"  {done_count}/{total} fetch responses stored, {remaining} remaining — rerun needed")
        else:
            logger.info(f"  {done_count}/{total} fetch responses stored, complete")

    def step_download_images(self):
        """Download game images for target media types; skips already-fetched rows."""
        _TARGET_TYPES = {
            MediaType.SSTITLE,
            MediaType.SS,
            MediaType.BOX_2D,
            MediaType.BOX_2D_SIDE,
            MediaType.BOX_2D_BACK,
            MediaType.BOX_3D,
        }
        _FORMAT_CONTENT_TYPE = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
        }
        _TARGET_TYPE_STRS = tuple(_TARGET_TYPES)
        placeholders = ",".join("?" * len(_TARGET_TYPE_STRS))

        remaining = self._fetch_remaining_requests()
        if remaining == 0:
            self._sleep_until_paris_midnight()
            remaining = self._fetch_remaining_requests()

        game_rows: List[tuple[int, str]] = [
            (row[0], row[1])
            for row in self.conn.execute(
                """
                SELECT m.screenscraper_id, m.name
                FROM MRAs m
                JOIN GameFetchResponses gfr ON m.screenscraper_id = gfr.screenscraper_id
                WHERE m.screenscraper_id != 0
                """
            )
        ]
        logger.info(f"  download-images: {len(game_rows)} games to process")
        if not game_rows:
            return

        done: set[tuple[int, str, str]] = {
            (row[0], row[1], row[2])
            for row in self.conn.execute(
                f"""
                SELECT gi.screenscraper_id, gi.type, gi.region
                FROM GameImages gi
                JOIN MRAs m ON gi.screenscraper_id = m.screenscraper_id
                WHERE gi.type IN ({placeholders})
                """,
                _TARGET_TYPE_STRS,
            )
        }

        games_processed = 0
        for screenscraper_id, mra_name in game_rows:
            games_processed += 1
            if games_processed % 1000 == 0:
                remaining = self._fetch_remaining_requests()
                if remaining == 0:
                    self._sleep_until_paris_midnight()
                    remaining = self._fetch_remaining_requests()

            row = self.conn.execute(
                "SELECT blob FROM GameFetchResponses WHERE screenscraper_id = ?",
                (screenscraper_id,),
            ).fetchone()
            if not row:
                continue

            try:
                payload = json.loads(row[0])
                medias = payload["response"]["jeu"]["medias"]
            except (KeyError, ValueError, json.JSONDecodeError) as e:
                logger.warning(f"  game {screenscraper_id}: cannot parse medias: {e}")
                continue

            target_medias = [
                m for m in medias
                if MEDIA_TYPE_MAP.get(m.get("type")) in _TARGET_TYPES
            ]
            self.conn.execute(
                "INSERT OR IGNORE INTO Games (screenscraper_id, name) VALUES (?, ?)",
                (screenscraper_id, mra_name),
            )
            self.conn.execute(
                "UPDATE Games SET image_count = ? WHERE screenscraper_id = ? AND image_count IS NULL",
                (len(target_medias), screenscraper_id),
            )
            self.conn.commit()

            needed = [
                m for m in target_medias
                if (screenscraper_id, MEDIA_TYPE_MAP[m["type"]], m.get("region", "")) not in done
            ]
            if not needed:
                continue

            valid_needed_map: dict[tuple, tuple] = {}
            for media in needed:
                mt = MEDIA_TYPE_MAP[media["type"]]
                region = media.get("region", "")
                url = media.get("url")
                fmt = media.get("format", "")
                content_type = _FORMAT_CONTENT_TYPE.get(fmt)
                if not url or not content_type:
                    logger.warning(
                        f"  game {screenscraper_id}: skip {mt.name}[{region}]: "
                        f"missing url or unknown format '{fmt}'"
                    )
                    continue
                valid_needed_map[(mt, region)] = (mt, region, url, content_type)
            valid_needed = list(valid_needed_map.values())

            for i in range(0, len(valid_needed), self.ss_threads):
                sub_batch = valid_needed[i:i + self.ss_threads]
                if remaining == 0:
                    self._sleep_until_paris_midnight()
                    remaining = self._fetch_remaining_requests()
                with ThreadPoolExecutor(max_workers=len(sub_batch)) as executor:
                    batch_futures = [
                        (mt, region, content_type, executor.submit(
                            self._fetch_url, url, f"game {screenscraper_id} {mt.name}[{region}]"
                        ))
                        for mt, region, url, content_type in sub_batch
                    ]
                for mt, region, content_type, future in batch_futures:
                    image_blob = future.result()
                    if image_blob is None:
                        continue
                    self.conn.execute(
                        "INSERT INTO GameImages (screenscraper_id, type, region, content_type, blob)"
                        " VALUES (?, ?, ?, ?, ?)",
                        (screenscraper_id, mt, region, content_type, image_blob),
                    )
                    self.conn.commit()
                    done.add((screenscraper_id, mt, region))
                    remaining -= 1
                    logger.info(
                        f"  game {screenscraper_id}: stored {mt.name}[{region}] ({len(image_blob)} bytes)"
                    )

        summary = self.conn.execute(
            f"""
            SELECT
                COUNT(*) AS processed,
                SUM(CASE WHEN COALESCE(gi_count.cnt, 0) >= g.image_count THEN 1 ELSE 0 END) AS complete
            FROM Games g
            LEFT JOIN (
                SELECT screenscraper_id, COUNT(*) AS cnt
                FROM GameImages
                WHERE type IN ({placeholders})
                GROUP BY screenscraper_id
            ) gi_count ON g.screenscraper_id = gi_count.screenscraper_id
            WHERE g.image_count IS NOT NULL
            """,
            _TARGET_TYPE_STRS,
        ).fetchone()
        processed, complete = summary[0], summary[1] or 0
        if complete < processed:
            logger.warning(f"  {complete}/{processed} games fully downloaded — rerun may be needed")
        else:
            logger.info(f"  {complete}/{processed} games fully downloaded, complete")

    def step_export_media(self):
        """[STUB] Export media files to artifact_path export directory."""
        logger.info("[STUB] export-media: not yet implemented")

    def step_export_zaparoo_map(self):
        """[STUB] Export Zaparoo NFC mapping file for arcade games."""
        logger.info("[STUB] export-zaparoo-map: not yet implemented")
