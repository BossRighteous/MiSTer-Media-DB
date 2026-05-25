"""Shared utility functions."""

import re

_FILENAME_INVALID_CHARS = str.maketrans('\\/:*?"<>|\t\r\n', " --  '      ")


def safe_game_name_for_filename(name: str) -> str:
    name = name.translate(_FILENAME_INVALID_CHARS)
    name = re.sub(r' {2,}', ' ', name)
    return name.strip()
