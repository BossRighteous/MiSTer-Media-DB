# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run full ETL pipeline
python main.py

# Run specific steps
python main.py --steps prepare-db process-system-csv

# Run specific systems
python main.py --systems nes snes

# Combine
python main.py --steps fetch-game-details download-images --systems n64 psx

# Custom artifact path (DB + exports root); also settable via ARTIFACT_PATH env var
python main.py --artifact-path /mnt/mister

# Custom DB path (relative to artifact-path, or absolute)
python main.py --db /path/to/custom.db

# Verbose logging
python main.py --verbose
```

No external dependencies — `sqlite3` is stdlib. No install step needed beyond Python 3.

## Architecture

### ETL Pipeline

`main.py` → `cli.py:main()` → `ETLWorkflow.run()` in `etl.py`

`ETLWorkflow` holds ordered `STEPS` list. Each step maps to a method via `step_<name_with_underscores>` convention (e.g., `fetch-game-details` → `step_fetch_game_details`). Steps receive the full list of `System` instances to process.

All steps are currently **stubs** — they log `[STUB]` and do nothing. Implementation goes in the corresponding `step_*` methods.

### System Registry

`systems.py` defines `System` dataclass with four fields:
- `zaparoo_id` — short system key used in CLI (`nes`, `snes`, etc.)
- `mister_media_dirname` — folder name on MiSTer SD card
- `mister_core_name` — MiSTer core identifier
- `screenscraper_id` — numeric ID for ScreenScraper.fr API

`SYSTEMS` list in `systems.py` is the single source of truth. CLI `--systems` arg filters this list by `zaparoo_id`.

### Data Flow (intended)

1. `prepare-db` — create SQLite schema
2. `fetch-csvs` — download game list CSVs per system into `csv/` (gitignored)
3. `process-system-csv` — parse CSVs into DB
4. `fetch-game-details` — query ScreenScraper.fr API using `screenscraper_id`
5. `download-images` — fetch artwork into local cache
6. `export-media` — write processed media to `export/` (gitignored)
7. `export-zaparoo-map` — write Zaparoo NFC mapping file

### Adding a New System

Add a `System(...)` entry to `SYSTEMS` in `systems.py`. No other registration needed.

### Adding a New Step

1. Add step name string to `ETLWorkflow.STEPS` in `etl.py`
2. Implement `step_<name>` method on `ETLWorkflow`
3. Update `--steps` help text in `cli.py`
