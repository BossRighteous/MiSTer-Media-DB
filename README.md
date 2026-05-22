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
python main.py --systems Nintendo64 PSX
```

Combine steps and systems:
```bash
python main.py --steps fetch-game-details download-images --systems Nintendo64 PSX
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

Pass `zaparoo_id` values to `--systems`.

### Consoles

| Zaparoo ID | System |
|---|---|
| `3DO` | 3DO Interactive Multiplayer |
| `AdventureVision` | Entex Adventure Vision |
| `AmigaCD32` | Amiga CD32 |
| `Arcadia` | Arcadia 2001 |
| `Astrocade` | Bally Astrocade |
| `Atari2600` | Atari 2600 |
| `Atari5200` | Atari 5200 |
| `Atari7800` | Atari 7800 |
| `AtariLynx` | Atari Lynx |
| `CasioPV1000` | Casio PV-1000 |
| `CDI` | Philips CD-i |
| `ChannelF` | Fairchild Channel F |
| `ColecoVision` | ColecoVision |
| `CreatiVision` | CreatiVision |
| `FDS` | Famicom Disk System |
| `Gamate` | Bit Corporation Gamate |
| `Gameboy` | Game Boy |
| `GameboyColor` | Game Boy Color |
| `GameGear` | Sega Game Gear |
| `GameNWatch` | Game & Watch |
| `GBA` | Game Boy Advance |
| `Genesis` | Sega Genesis / Mega Drive |
| `Intellivision` | Mattel Intellivision |
| `Jaguar` | Atari Jaguar |
| `JaguarCD` | Atari Jaguar CD |
| `MasterSystem` | Sega Master System |
| `MegaCD` | Sega Mega CD / Sega CD |
| `MegaDuck` | Mega Duck |
| `NeoGeoCD` | Neo Geo CD |
| `NeoGeoPocket` | Neo Geo Pocket |
| `NeoGeoPocketColor` | Neo Geo Pocket Color |
| `NES` | Nintendo Entertainment System |
| `Nintendo64` | Nintendo 64 |
| `Odyssey2` | Magnavox Odyssey 2 |
| `PocketChallengeV2` | Pocket Challenge V2 |
| `PokemonMini` | Pokémon Mini |
| `PSX` | PlayStation |
| `Saturn` | Sega Saturn |
| `Sega32X` | Sega 32X |
| `SG1000` | Sega SG-1000 |
| `SNES` | Super Nintendo |
| `SuperGameboy` | Super Game Boy |
| `SuperGrafx` | PC Engine SuperGrafx |
| `SuperVision` | Watara Supervision |
| `TurboGrafx16` | TurboGrafx-16 / PC Engine |
| `TurboGrafx16CD` | TurboGrafx-CD / PC Engine CD |
| `VC4000` | Interton VC 4000 |
| `Vectrex` | Vectrex |
| `VirtualBoy` | Virtual Boy |
| `WonderSwan` | WonderSwan |
| `WonderSwanColor` | WonderSwan Color |

### Computers

| Zaparoo ID | System |
|---|---|
| `AcornAtom` | Acorn Atom |
| `AcornElectron` | Acorn Electron |
| `Amstrad` | Amstrad CPC |
| `AppleII` | Apple II |
| `Atari800` | Atari 800 |
| `BBCMicro` | BBC Micro |
| `BK0011M` | Elektronika BK0011M |
| `C16` | Commodore 16 |
| `C64` | Commodore 64 |
| `CoCo2` | TRS-80 Color Computer 2 |
| `DOS` | DOS (ao486) |
| `Jupiter` | Jupiter Ace |
| `Lynx48` | Camputers Lynx 48 |
| `MSX` | MSX |
| `Oric` | Oric |
| `PET2001` | Commodore PET 2001 |
| `SAMCoupe` | SAM Coupé |
| `SVI328` | Spectravideo SVI-328 |
| `TI994A` | TI-99/4A |
| `VIC20` | Commodore VIC-20 |
| `X68000` | Sharp X68000 |
| `ZX81` | Sinclair ZX81 |
| `ZXSpectrum` | ZX Spectrum |

### Other

| Zaparoo ID | System |
|---|---|
| `Arcade` | Arcade (MiSTer MRA) |
| `Arduboy` | Arduboy |
| `ScummVM` | ScummVM |

## Arcade ETL

Separate pipeline for MiSTer `.mra`-based arcade games. Looks up games on ScreenScraper by MAME ROM name (`setname.zip`) rather than by system CSV.

### Required env vars

```
SS_DEV_ID
SS_DEV_PASSWORD
SS_USER_ID
SS_USER_PASSWORD
SS_SOFTNAME
SS_THREADS
MRA_PATH        # or pass --mra-path
ARTIFACT_PATH   # or pass --artifact-path
```

Place in `.env` at the project root or at `--artifact-path`.

### Usage

```bash
# Run all steps
python arcade.py

# Specify .mra directory and artifact output path
python arcade.py --mra-path /media/fat/_Arcade --artifact-path /mnt/mister

# Run specific steps
python arcade.py --steps prepare-db mra-scan

# Custom DB path
python arcade.py --db /path/to/arcade_media.db

# Verbose logging
python arcade.py --verbose
```

### Available Steps

- `prepare-db` — initialize database schema
- `mra-scan` — parse `.mra` files, populate MRAs table
- `fetch-game-details` — look up each game on ScreenScraper by `setname.zip`, store raw response and resolve `screenscraper_id`
- `download-images` — download artwork for resolved games
- `export-media` — export processed media to artifact path *(stub)*
- `export-zaparoo-map` — export Zaparoo NFC mapping file *(stub)*

### Module Usage

```python
from mister_media_db.arcade import ArcadeETLWorkflow

workflow = ArcadeETLWorkflow(
    db_path="arcade_media.db",
    artifact_path="/mnt/mister",
    mra_path="/media/fat/_Arcade",
)
workflow.run(steps=["prepare-db", "mra-scan", "fetch-game-details"])
```

## Database Recovery

`recover_db.py` copies rows one at a time from a potentially-corrupted `mister_media.db` into a fresh `mister_recover.db`. Each row is an individual committed transaction so a corrupt page causes a single-row error rather than aborting the entire table. `GameImages` is processed last; each blob is PNG/JPEG-validated before insertion — truncated images are skipped and logged.

Safe to interrupt (Ctrl-C) and resume; existing rows in the destination are skipped via `INSERT OR IGNORE`.

```bash
# Full recovery with defaults
python recover_db.py

# Custom source/dest
python recover_db.py --source /path/to/mister_media.db --dest /path/to/mister_recover.db

# Recover non-image tables first, GameImages separately
python recover_db.py --tables CSV Games GameFetchResponses GameZaparooTitles
python recover_db.py --tables GameImages

# Verbose log (DEBUG level)
python recover_db.py --verbose --log recover_debug.log
```

Progress is printed per row to stdout. Errors and skipped blobs go to `recover.log` (and WARNING+ to stderr).

---

## Module Usage

```python
from mister_media_db.etl import ETLWorkflow

workflow = ETLWorkflow(db_path="mister_media.db")
workflow.run(
    steps=["prepare-db", "fetch-game-details"],
    systems=["nes", "snes"]
)
```
