"""ETL workflow and step definitions."""

import atexit
import csv
import html
import io
import json
import os
import signal
import sqlite3
import logging
import time
import urllib.parse
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from zoneinfo import ZoneInfo


def _sigbreak_handler(signum, frame):
    raise KeyboardInterrupt()


if hasattr(signal, "SIGBREAK"):
    signal.signal(signal.SIGBREAK, _sigbreak_handler)

from mister_media_db.media_types import MEDIA_TYPE_MAP, MediaType
from mister_media_db.slugs import slugify_game_str
from mister_media_db.systems import SYSTEMS, System

logger = logging.getLogger(__name__)


def _clean_text(text: str) -> str:
    return " ".join(html.unescape(text).split())


_NOM_REGION_PRIORITY = ["ss", "wor", "us", "eu", "jp"]


def _pick_nom(noms: list) -> Optional[str]:
    by_region = {n.get("region", ""): n.get("text", "") for n in noms if n.get("text")}
    for region in _NOM_REGION_PRIORITY:
        if region in by_region:
            text = by_region[region]
            cleaned = html.unescape(text).replace("\t", "").replace("\n", "").replace("\r", "").strip()
            if cleaned:
                return cleaned
    for text in by_region.values():
        cleaned = html.unescape(text).replace("\t", "").replace("\n", "").replace("\r", "").strip()
        if cleaned:
            return cleaned
    return None


_SS_ENV_VARS = [
    "SS_DEV_ID",
    "SS_DEV_PASSWORD",
    "SS_USER_ID",
    "SS_USER_PASSWORD",
    "SS_SOFTNAME",
    "SS_THREADS",
]


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


class ETLWorkflow:
    """Manages ETL steps and execution."""

    STEPS = [
        "prepare-db",
        "fetch-csvs",
        "process-system-csv",
        "fetch-game-details",
        "download-images",
        "get-zaparoo-mediatitles",
        "export-media",
        "export-zaparoo-map",
    ]

    def __init__(self, db_path: str = "mister_media.db", artifact_path: Optional[str] = None):
        self.conn: Optional[sqlite3.Connection] = None
        _load_dotenv(Path(".env"))
        resolved_artifact = Path(artifact_path) if artifact_path else Path(os.environ.get("ARTIFACT_PATH", "."))
        self.artifact_path = resolved_artifact.resolve()
        if self.artifact_path != Path(".").resolve():
            _load_dotenv(self.artifact_path / ".env")
        db = Path(db_path)
        self.db_path = db if db.is_absolute() else self.artifact_path / db
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
        """Connect to SQLite database."""
        self.conn = sqlite3.connect(self.db_path)
        atexit.register(self.close)
        logger.info(f"Connected to database: {self.db_path}")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed")

    def run(
        self,
        steps: Optional[List[str]] = None,
        systems: Optional[List[str]] = None,
    ):
        """
        Execute ETL workflow.

        Args:
            steps: Step names to run. If None, run all steps.
            systems: zaparoo_id strings to process. If None, process all systems.
        """
        self.connect()

        try:
            steps_to_run = steps if steps else self.STEPS
            if systems:
                system_map = {s.zaparoo_id: s for s in SYSTEMS}
                unknown = [sid for sid in systems if sid not in system_map]
                if unknown:
                    raise ValueError(f"Unknown system IDs: {', '.join(unknown)}")
                systems_to_process = [system_map[sid] for sid in systems]
            else:
                systems_to_process = SYSTEMS

            for step in steps_to_run:
                if step not in self.STEPS:
                    logger.error(f"Unknown step: {step}")
                    continue

                logger.info(f"Running step: {step}")
                self._execute_step(step, systems_to_process)

        except KeyboardInterrupt:
            logger.warning("Interrupted — closing database")
            raise
        finally:
            self.close()

    def _execute_step(self, step: str, systems: List[System]):
        """Execute a single step for given systems."""
        handler = getattr(self, f"step_{step.replace('-', '_')}", None)
        if handler:
            handler(systems)
        else:
            logger.warning(f"No handler for step: {step}")

    def step_prepare_db(self, systems: List[System]):
        """Prepare database schema. Errors if tables already exist."""
        try:
            self.conn.executescript("""
                CREATE TABLE CSV (
                    system_id TEXT PRIMARY KEY,
                    game_count INTEGER,
                    blob BLOB NOT NULL
                );

                CREATE TABLE Games (
                    screenscraper_id INTEGER PRIMARY KEY,
                    system_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    image_count INTEGER,
                    zaparoo_title TEXT,
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

    def step_fetch_csvs(self, systems: List[System]):
        """Fetch CSV files for each system, skipping already-fetched systems."""
        system_ids = [s.zaparoo_id for s in systems]
        placeholders = ",".join("?" * len(system_ids))
        fetched = self.conn.execute(
            f"SELECT COUNT(*) FROM CSV WHERE system_id IN ({placeholders})", system_ids
        ).fetchone()[0]
        logger.info(f"  {fetched}/{len(systems)} systems already have CSVs")

        for system in systems:
            row = self.conn.execute(
                "SELECT 1 FROM CSV WHERE system_id = ?", (system.zaparoo_id,)
            ).fetchone()
            if row:
                logger.info(f"  Skipping CSV fetch for {system.zaparoo_id}: already in DB")
                continue

            url = f"https://screenscraper.fr/medias/{system.screenscraper_id}/gameslist.csv"
            logger.info(f"  Fetching CSV for {system.zaparoo_id}: {url}")
            try:
                with urllib.request.urlopen(url) as response:
                    blob = response.read()
            except urllib.error.HTTPError as e:
                logger.error(f"  HTTP {e.code} fetching CSV for {system.zaparoo_id}: {e.reason}")
                continue
            except urllib.error.URLError as e:
                logger.error(f"  URL error fetching CSV for {system.zaparoo_id}: {e.reason}")
                continue

            self.conn.execute(
                "INSERT INTO CSV (system_id, blob) VALUES (?, ?)",
                (system.zaparoo_id, blob),
            )
            self.conn.commit()
            logger.info(f"  Stored CSV for {system.zaparoo_id} ({len(blob)} bytes)")

    def step_process_system_csv(self, systems: List[System]):
        """Parse each system's CSV blob and insert games into Games table."""
        for system in systems:
            row = self.conn.execute(
                "SELECT blob FROM CSV WHERE system_id = ?", (system.zaparoo_id,)
            ).fetchone()
            if not row:
                logger.error(f"  No CSV blob for {system.zaparoo_id}: skipping")
                continue

            text = row[0].decode("utf-8")
            reader = csv.DictReader(io.StringIO(text), delimiter=";", quotechar='"')
            inserted = 0
            skipped = 0
            for record in reader:
                screenscraper_id = int(record["Game ID"])
                name = record["Game Name"]
                cursor = self.conn.execute(
                    "INSERT OR IGNORE INTO Games (screenscraper_id, system_id, name) VALUES (?, ?, ?)",
                    (screenscraper_id, system.zaparoo_id, name),
                )
                if cursor.rowcount:
                    inserted += 1
                else:
                    skipped += 1
            total = inserted + skipped
            self.conn.execute(
                "UPDATE CSV SET game_count = ? WHERE system_id = ?",
                (total, system.zaparoo_id),
            )
            self.conn.commit()
            db_count = self.conn.execute(
                "SELECT COUNT(*) FROM Games WHERE system_id = ?", (system.zaparoo_id,)
            ).fetchone()[0]
            logger.info(f"  {system.zaparoo_id}: {inserted} inserted, {skipped} skipped (CSV rows: {total}, DB games: {db_count})")
            if db_count != total:
                logger.warning(
                    f"  {system.zaparoo_id}: CSV has {total} rows but DB has {db_count} Games — rerun may be needed"
                )

    def step_fetch_game_details(self, systems: List[System]):
        """Fetch game details from ScreenScraper for games missing a fetch response."""
        for system in systems:
            game_ids = [
                row[0]
                for row in self.conn.execute(
                    """
                    SELECT g.screenscraper_id FROM Games g
                    LEFT JOIN GameFetchResponses gfr ON g.screenscraper_id = gfr.screenscraper_id
                    WHERE g.system_id = ? AND gfr.screenscraper_id IS NULL
                    """,
                    (system.zaparoo_id,),
                )
            ]
            total_games = self.conn.execute(
                "SELECT COUNT(*) FROM Games WHERE system_id = ?", (system.zaparoo_id,)
            ).fetchone()[0]
            logger.info(f"  {system.zaparoo_id}: {len(game_ids)}/{total_games} games to fetch")

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
                """SELECT COUNT(*) FROM GameFetchResponses gfr
                   JOIN Games g ON gfr.screenscraper_id = g.screenscraper_id
                   WHERE g.system_id = ?""",
                (system.zaparoo_id,),
            ).fetchone()[0]
            remaining = total_games - done_count
            if remaining:
                logger.warning(
                    f"  {system.zaparoo_id}: {done_count}/{total_games} fetch responses stored, {remaining} remaining — rerun needed"
                )
            else:
                logger.info(f"  {system.zaparoo_id}: {done_count}/{total_games} fetch responses stored, complete")

    def _fetch_remaining_requests(self) -> int:
        """Query ssuserInfos.php and return max - today. Returns -1 on error."""
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
        """Sleep until midnight Paris time (daily rate limit reset)."""
        paris = ZoneInfo("Europe/Paris")
        now = datetime.now(paris)
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        sleep_seconds = (midnight - now).total_seconds()
        logger.warning(
            f"  Rate limit reached. Sleeping {sleep_seconds:.0f}s until midnight Paris time ({midnight.isoformat()})"
        )
        time.sleep(sleep_seconds)

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

    def step_download_images(self, systems: List[System]):
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

        remaining = self._fetch_remaining_requests()
        if remaining == 0:
            self._sleep_until_paris_midnight()
            remaining = self._fetch_remaining_requests()

        for system in systems:
            # Fetch only IDs — avoids holding all blobs in memory at once
            game_ids: List[int] = [
                row[0]
                for row in self.conn.execute(
                    """
                    SELECT g.screenscraper_id
                    FROM Games g
                    JOIN GameFetchResponses gfr ON g.screenscraper_id = gfr.screenscraper_id
                    WHERE g.system_id = ?
                    """,
                    (system.zaparoo_id,),
                )
            ]
            logger.info(f"  {system.zaparoo_id}: {len(game_ids)} games to process")
            if not game_ids:
                continue

            # Preload all already-stored (screenscraper_id, type, region) for system —
            # one query replaces N×M per-media SELECTs inside the game loop
            placeholders = ",".join("?" * len(_TARGET_TYPE_STRS))
            done: set[tuple[int, str, str]] = {
                (row[0], row[1], row[2])
                for row in self.conn.execute(
                    f"""
                    SELECT gi.screenscraper_id, gi.type, gi.region
                    FROM GameImages gi
                    JOIN Games g ON gi.screenscraper_id = g.screenscraper_id
                    WHERE g.system_id = ? AND gi.type IN ({placeholders})
                    """,
                    (system.zaparoo_id, *_TARGET_TYPE_STRS),
                )
            }

            games_processed = 0
            for screenscraper_id in game_ids:
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

            row = self.conn.execute(
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
                WHERE g.system_id = ? AND g.image_count IS NOT NULL
                """,
                (*_TARGET_TYPE_STRS, system.zaparoo_id),
            ).fetchone()
            processed, complete = row[0], row[1] or 0
            if complete < processed:
                logger.warning(
                    f"  {system.zaparoo_id}: {complete}/{processed} games fully downloaded — rerun may be needed"
                )
            else:
                logger.info(f"  {system.zaparoo_id}: {complete}/{processed} games fully downloaded, complete")

    def _post_json(self, url: str, body: bytes, label: str = "") -> Optional[dict]:
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req) as response:
                payload = json.loads(response.read())
            return payload.get("result")
        except urllib.error.HTTPError as e:
            logger.error(f"  HTTP {e.code} posting {label or url}: {e.reason}")
            return None
        except urllib.error.URLError as e:
            logger.error(f"  URL error posting {label or url}: {e.reason}")
            return None
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"  Cannot parse response for {label or url}: {e}")
            return None

    def step_get_zaparoo_mediatitles(self, systems: List[System]):
        """Fetch zaparoo media title slugs for all rom filenames via Zaparoo JSON-RPC API."""
        zaparoo_host = os.environ.get("ZAPAROO_HOST")
        if not zaparoo_host:
            logger.error("  ZAPAROO_HOST env var not set: skipping get-zaparoo-mediatitles")
            return

        base_url = f"http://{zaparoo_host}:7497/api/v0.1"

        for system in systems:
            game_ids: List[int] = [
                row[0]
                for row in self.conn.execute(
                    """
                    SELECT g.screenscraper_id
                    FROM Games g
                    JOIN GameFetchResponses gfr ON g.screenscraper_id = gfr.screenscraper_id
                    WHERE g.system_id = ?
                    """,
                    (system.zaparoo_id,),
                )
            ]
            logger.info(f"  {system.zaparoo_id}: {len(game_ids)} game responses to process")

            inserted_system = 0
            for screenscraper_id in game_ids:
                row = self.conn.execute(
                    "SELECT blob FROM GameFetchResponses WHERE screenscraper_id = ?",
                    (screenscraper_id,),
                ).fetchone()
                if not row:
                    continue
                blob = row[0]
                try:
                    payload = json.loads(blob)
                    jeu = payload["response"]["jeu"]
                    roms = jeu["roms"]
                except (KeyError, ValueError, json.JSONDecodeError) as e:
                    logger.warning(f"  {system.zaparoo_id}: cannot parse roms: {e}")
                    continue

                zaparoo_title = _pick_nom(jeu.get("noms", []))
                if zaparoo_title:
                    self.conn.execute(
                        "UPDATE Games SET zaparoo_title = ? WHERE screenscraper_id = ? AND zaparoo_title IS NULL",
                        (zaparoo_title, screenscraper_id),
                    )
                    self.conn.commit()

                existing_slugs: set[str] = {
                    row[0]
                    for row in self.conn.execute(
                        "SELECT slug FROM GameZaparooTitles WHERE screenscraper_id = ?",
                        (screenscraper_id,),
                    )
                }

                for rom in roms:
                    romfilename = rom.get("romfilename")
                    if not romfilename:
                        continue

                    body = json.dumps({
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "mediatitle.frompath",
                        "params": {
                            "systemId": system.zaparoo_id,
                            "path": romfilename,
                        },
                    }).encode("utf-8")

                    result = self._post_json(
                        base_url, body, label=f"{system.zaparoo_id}/{romfilename}"
                    )
                    if result is None:
                        continue

                    slug = result.get("slug")
                    if not slug or slug in existing_slugs:
                        continue

                    self.conn.execute(
                        "INSERT OR IGNORE INTO GameZaparooTitles (screenscraper_id, slug, result)"
                        " VALUES (?, ?, ?)",
                        (screenscraper_id, slug, json.dumps(result)),
                    )
                    self.conn.commit()
                    existing_slugs.add(slug)
                    inserted_system += 1

            logger.info(f"  {system.zaparoo_id}: {inserted_system} new slug records inserted")

    def step_export_media(self, systems: List[System]):
        """Export media files to ./export/media/{system.mister_media_dirname}/."""
        _CONTENT_TYPE_EXT = {
            "image/png": "png",
            "image/jpeg": "jpg",
        }
        _INVALID_CHARS = str.maketrans('\\/:*?"<>|', '_________')

        base = self.artifact_path / "export" / "media"

        for system in systems:
            system_dir = base / system.mister_media_dirname
            system_dir.mkdir(parents=True, exist_ok=True)

            cursor = self.conn.execute(
                """
                SELECT g.name, gi.type, gi.region, gi.content_type, gi.blob
                FROM Games g
                JOIN GameImages gi ON g.screenscraper_id = gi.screenscraper_id
                WHERE g.system_id = ?
                ORDER BY g.name, gi.type, gi.region
                """,
                (system.zaparoo_id,),
            )

            exported = 0
            for name, media_type, region, content_type, blob in cursor:
                ext = _CONTENT_TYPE_EXT.get(content_type)
                if not ext:
                    logger.warning(f"  Unknown content_type '{content_type}' for {name}: skipping")
                    continue

                safe_name = name.translate(_INVALID_CHARS)
                parts = [safe_name, media_type]
                if region:
                    parts.append(region)
                filename = ".".join(parts) + f".{ext}"

                dest = system_dir / filename
                if dest.exists():
                    continue
                dest.write_bytes(blob)
                exported += 1

            logger.info(f"  {system.zaparoo_id}: {exported} images exported to {system_dir}")

    def step_export_zaparoo_map(self, systems: List[System]):
        """Export zaparoometa JSON fragments per game to ./export/zaparoometa/."""
        _INVALID_CHARS = str.maketrans('\\/:*?"<>|', '_________')
        base = self.artifact_path / "export" / "zaparoometa"

        for system in systems:
            system_dir = base / system.mister_media_dirname
            system_dir.mkdir(parents=True, exist_ok=True)

            rows = self.conn.execute(
                """
                SELECT g.name, gfr.blob
                FROM Games g
                JOIN GameFetchResponses gfr ON g.screenscraper_id = gfr.screenscraper_id
                WHERE g.system_id = ?
                ORDER BY g.name
                """,
                (system.zaparoo_id,),
            ).fetchall()

            exported = 0
            for name, blob in rows:
                try:
                    payload = json.loads(blob)
                    jeu = payload["response"]["jeu"]
                except (KeyError, ValueError, json.JSONDecodeError) as e:
                    logger.warning(f"  {system.zaparoo_id} / {name}: cannot parse response: {e}")
                    continue

                record = {
                    "screenscraper_id": int(jeu["id"]),
                    "publisher": jeu.get("editeur", {}).get("text"),
                    "developer": jeu.get("developpeur", {}).get("text"),
                    "players": jeu.get("joueurs", {}).get("text"),
                    "system": jeu.get("systeme", {}).get("text"),
                    "description": [
                        {**s, "text": _clean_text(s["text"])} if "text" in s else s
                        for s in jeu.get("synopsis", [])
                    ] or None,
                    "dates": jeu.get("dates"),
                    "genres": [genre["noms"] for genre in jeu.get("genres", [])],
                    "known_title_slugs": list(dict.fromkeys(
                        s for rom in jeu.get("roms", [])
                        if (s := slugify_game_str(
                            Path(rom["romfilename"]).stem
                        ))
                    )),
                    "known_hack_title_slugs": list(dict.fromkeys(
                        s for hack in jeu.get("hacks", [])
                        if (s := slugify_game_str(
                            Path(hack["filename"]).stem
                        ))
                    )),
                }

                safe_name = name.translate(_INVALID_CHARS)
                dest = system_dir / f"{safe_name}.zaparoometa.json"
                if dest.exists():
                    continue
                dest.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
                exported += 1

            logger.info(f"  {system.zaparoo_id}: {exported}/{len(rows)} zaparoometa files written to {system_dir}")
