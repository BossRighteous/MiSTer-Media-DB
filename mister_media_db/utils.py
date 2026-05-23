"""Shared utility functions."""

_FILENAME_INVALID_CHARS = str.maketrans('\\/:*?"<>|', '_________')


def safe_game_name_for_filename(name: str) -> str:
    return name.translate(_FILENAME_INVALID_CHARS)
