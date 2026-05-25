from mister_media_db.utils import safe_game_name_for_filename


def test_no_change_needed():
    assert safe_game_name_for_filename("Super Mario Bros") == "Super Mario Bros"

def test_invalid_chars_replaced():
    # : / → dash, " → ', everything else → space
    assert safe_game_name_for_filename('Game: A/B\\C*D?E"F<G>H|I') == "Game- A-B C D E'F G H I"

def test_tabs_and_newlines_replaced():
    assert safe_game_name_for_filename("Game\tName\r\nHere") == "Game Name Here"

def test_multiple_spaces_collapsed():
    assert safe_game_name_for_filename("Game  Name   Here") == "Game Name Here"

def test_leading_trailing_whitespace_stripped():
    assert safe_game_name_for_filename("  Game Name  ") == "Game Name"

def test_combined():
    assert safe_game_name_for_filename("  Game:\tA/B  ") == "Game- A-B"
