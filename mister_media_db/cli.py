"""Command-line interface for MiSTer Media DB."""

import argparse
import logging
import sys
from . import __version__
from .etl import ETLWorkflow


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def parse_args(args=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="ETL workflow for MiSTer game system media",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Run all steps for all systems
  %(prog)s --steps prepare-db        # Run only prepare-db step
  %(prog)s --systems nes snes        # Run all steps for NES and SNES
  %(prog)s --steps fetch-game-details --systems genesis n64
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "-a", "--artifact-path",
        default=None,
        metavar="PATH",
        help="Root path for DB and exports (default: ARTIFACT_PATH env var or current directory)",
    )

    parser.add_argument(
        "-d", "--db",
        default="mister_media.db",
        help="Path to SQLite database, relative to artifact-path if not absolute (default: mister_media.db)",
    )

    parser.add_argument(
        "-s", "--steps",
        nargs="+",
        metavar="STEP",
        help="Steps to run (space-separated). Available: prepare-db, fetch-csvs, process-system-csv, "
        "fetch-game-details, download-images, get-zaparoo-mediatitles, export-media, export-zaparoo-map",
    )

    parser.add_argument(
        "-sys", "--systems",
        nargs="+",
        metavar="SYSTEM",
        help="Systems to process (space-separated). Available: nes, snes, genesis, n64, psx, dreamcast",
    )

    return parser.parse_args(args)


def main(args=None):
    """Main CLI entry point."""
    parsed = parse_args(args)
    setup_logging(parsed.verbose)

    workflow = ETLWorkflow(db_path=parsed.db, artifact_path=parsed.artifact_path)
    workflow.run(steps=parsed.steps, systems=parsed.systems)


if __name__ == "__main__":
    main()
