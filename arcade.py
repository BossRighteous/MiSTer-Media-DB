#!/usr/bin/env python3
"""Entry point for the arcade ETL pipeline."""

import argparse
import logging
import sys
from mister_media_db.arcade import ArcadeETLWorkflow


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Arcade ETL workflow for MiSTer .mra-based arcade mappings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Run all steps
  %(prog)s --steps prepare-db mra-scan  # Run specific steps
  %(prog)s --mra-path /media/fat/_Arcade
        """,
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    parser.add_argument(
        "-a", "--artifact-path",
        default=None,
        metavar="PATH",
        help="Root path for DB and exports (default: ARTIFACT_PATH env var or current directory)",
    )

    parser.add_argument(
        "-d", "--db",
        default="arcade_media.db",
        help="Path to SQLite database, relative to artifact-path if not absolute (default: arcade_media.db)",
    )

    parser.add_argument(
        "--mra-path",
        default=None,
        metavar="PATH",
        help="Path to directory containing .mra files (default: <artifact-path>/_Arcade)",
    )

    parser.add_argument(
        "-s", "--steps",
        nargs="+",
        metavar="STEP",
        help="Steps to run (space-separated). Available: prepare-db, mra-scan, "
             "fetch-game-details, download-images, export-media, export-zaparoo-map",
    )

    return parser.parse_args(args)


def main(args=None):
    parsed = parse_args(args)
    setup_logging(parsed.verbose)
    workflow = ArcadeETLWorkflow(
        db_path=parsed.db,
        artifact_path=parsed.artifact_path,
        mra_path=parsed.mra_path,
    )
    workflow.run(steps=parsed.steps)


if __name__ == "__main__":
    main()
