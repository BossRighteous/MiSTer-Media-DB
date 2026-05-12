"""System definitions for MiSTer Media DB ETL."""

from dataclasses import dataclass


@dataclass
class System:
    zaparoo_id: str
    mister_media_dirname: str
    mister_core_name: str
    screenscraper_id: int


SYSTEMS: list[System] = [
    System(
        zaparoo_id="CreatiVision",
        mister_media_dirname="CreatiVision",
        mister_core_name="CreatiVision",
        screenscraper_id=241,
    ),
]
