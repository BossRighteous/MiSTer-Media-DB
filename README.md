# MiSTer Media DB

Cross-platform ETL workflow to process and manage video game system metadata and media for MiSTer.

## Setup

```bash
# Install dependencies (none currently required, sqlite3 is built-in)
pip install -r requirements.txt
```

## Usage

Run all steps for all systems:
```bash
python main.py
```

Run specific steps:
```bash
python main.py --steps prepare-db process-system-csv
```

Process specific systems:
```bash
python main.py --systems nes snes genesis
```

Combine steps and systems:
```bash
python main.py --steps fetch-game-details download-images --systems n64 psx
```

Specify database path:
```bash
python main.py --db /path/to/custom.db
```

Enable verbose logging:
```bash
python main.py --verbose
```

View help:
```bash
python main.py --help
```

## Available Steps

- `prepare-db` - Initialize database schema
- `process-system-csv` - Process CSV files for each system
- `fetch-game-details` - Fetch game metadata from external sources
- `download-images` - Download game artwork and media
- `export-media` - Export processed media to output directory
- `export-zaparoo-map` - Export Zaparoo format mapping

## Available Systems

- `nes` - Nintendo Entertainment System
- `snes` - Super Nintendo
- `genesis` - Sega Genesis
- `n64` - Nintendo 64
- `psx` - PlayStation 1
- `dreamcast` - Sega Dreamcast

## Module Usage

```python
from mister_media_db.etl import ETLWorkflow

workflow = ETLWorkflow(db_path="mister_media.db")
workflow.run(
    steps=["prepare-db", "fetch-game-details"],
    systems=["nes", "snes"]
)
```
