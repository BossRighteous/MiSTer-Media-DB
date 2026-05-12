import re
import unicodedata
from dataclasses import dataclass, field


@dataclass
class SlugifyResult:
    slug: str
    tokens: list[str] = field(default_factory=list)


# ── Abbreviation / number-word tables ──────────────────────────────────────────

_PERIOD_REQUIRED_ABBREVS: dict[str, str] = {
    "feat.": "featuring",
    "no.":   "number",
    "st.":   "saint",
}

_FLEXIBLE_ABBREVS: dict[str, str] = {
    "vs":   "versus",
    "bros": "brothers",
    "dr":   "doctor",
    "mr":   "mister",
    "vol":  "volume",
    "pt":   "part",
    "ft":   "featuring",
    "jr":   "junior",
    "sr":   "senior",
}

_NUMBER_WORDS: dict[str, str] = {
    "one": "1",   "two": "2",     "three": "3",  "four": "4",   "five": "5",
    "six": "6",   "seven": "7",   "eight": "8",  "nine": "9",   "ten": "10",
    "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14",
    "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18",
    "nineteen": "19", "twenty": "20",
}

# X intentionally omitted — preserves "Mega Man X"
_ROMAN_NUMERALS: list[tuple[str, str]] = [
    ("XIX", "19"), ("XVIII", "18"), ("XVII", "17"), ("XVI", "16"),
    ("XV", "15"),  ("XIV", "14"),   ("XIII", "13"), ("XII", "12"),
    ("XI", "11"),  ("IX", "9"),     ("VIII", "8"),  ("VII", "7"),
    ("VI", "6"),   ("IV", "4"),     ("V", "5"),     ("III", "3"),
    ("II", "2"),   ("I", "1"),
]

# ── Pre-compiled regexes ───────────────────────────────────────────────────────

_EDITION_SUFFIX_RE = re.compile(
    r"(?i)\s+(version|edition|ausgabe|versione|edizione|versao|edicao"
    r"|バージョン|エディション|ヴァージョン)$"
)
_VERSION_SUFFIX_RE    = re.compile(r"\s+v[.]?(?:\d{1,3}(?:[.]\d{1,4})*|[IVX]{1,5})$")
_ORDINAL_SUFFIX_RE    = re.compile(r"\b(\d+)(?:st|nd|rd|th)\b")
_ORDINAL_CAMEL_RE     = re.compile(r"\b(\d+(?:st|nd|rd|th))([A-Z])")
_TRAILING_ARTICLE_RE  = re.compile(r"(?i),\s*the\s*($|[\s:\-\(\[])")
_DOTTED_INITIALISM_RE = re.compile(r"\b(?:[A-Za-z]\.){2,}")

# Final-stage slug filters
_NON_ALPHANUM_ASCII_RE = re.compile(r"[^a-z0-9]+")
_NON_ALPHANUM_UNICODE_RE = re.compile(
    r"[^a-z0-9"
    r"À-ɏḀ-ỿ"
    r"\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\uAC00-\uD7A3\u30FC\u30FB\u3005"
    r"\u0400-\u04FF"    # Cyrillic
    r"\u0370-\u03FF"    # Greek
    r"\u0900-\u097F\u0980-\u09FF\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF"
    r"\u0D00-\u0D7F\u0A00-\u0A7F\u0A80-\u0AFF\u0B00-\u0B7F\u0D80-\u0DFF"
    r"\u0600-\u06FF"    # Arabic
    r"\u0590-\u05FF"    # Hebrew
    r"\u0E00-\u0E7F"    # Thai
    r"\u1200-\u137F"    # Ethiopic
    r"]+",
    re.UNICODE,
)


# ── Utilities ──────────────────────────────────────────────────────────────────

def _is_ascii(s: str) -> bool:
    return all(ord(c) < 128 for c in s)


def _is_latin_word_char(c: str) -> bool:
    """ASCII letter, digit, or underscore — used for Roman numeral boundary detection."""
    return c.isascii() and (c.isalpha() or c.isdigit() or c == "_")


def _detect_script(s: str) -> str:
    """Returns dominant script: 'latin', 'cjk', 'cyrillic', 'greek', 'indic',
    'arabic', 'hebrew', 'thai', 'burmese', 'khmer', 'lao', 'amharic'."""
    for r in s:
        cp = ord(r)
        if cp <= 127:
            continue
        if (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF
                or 0x3040 <= cp <= 0x30FF or 0xAC00 <= cp <= 0xD7A3
                or cp in (0x30FC, 0x30FB, 0x3005)):
            return "cjk"
        if 0x0400 <= cp <= 0x04FF:
            return "cyrillic"
        if (0x0900 <= cp <= 0x097F or 0x0980 <= cp <= 0x09FF
                or 0x0B80 <= cp <= 0x0BFF or 0x0C00 <= cp <= 0x0C7F
                or 0x0C80 <= cp <= 0x0CFF or 0x0D00 <= cp <= 0x0D7F
                or 0x0A00 <= cp <= 0x0A7F or 0x0A80 <= cp <= 0x0AFF
                or 0x0B00 <= cp <= 0x0B7F or 0x0D80 <= cp <= 0x0DFF):
            return "indic"
        if 0x0600 <= cp <= 0x06FF:
            return "arabic"
        if 0x0E00 <= cp <= 0x0E7F:
            return "thai"
        if 0x0370 <= cp <= 0x03FF:
            return "greek"
        if 0x0590 <= cp <= 0x05FF:
            return "hebrew"
        if 0x1000 <= cp <= 0x109F:
            return "burmese"
        if 0x1780 <= cp <= 0x17FF:
            return "khmer"
        if 0x0E80 <= cp <= 0x0EFF:
            return "lao"
        if 0x1200 <= cp <= 0x137F:
            return "amharic"
    return "latin"


def _needs_unicode_slug(script: str) -> bool:
    return script in ("cjk", "cyrillic", "greek", "indic", "arabic",
                      "hebrew", "thai", "burmese", "khmer", "lao", "amharic")


# ── Character / Unicode normalization ─────────────────────────────────────────

def _normalize_width(s: str) -> str:
    """Stage 1: fullwidth ASCII → halfwidth, halfwidth katakana → fullwidth."""
    # golang.org/x/text/width.Fold does width-only folding. Python's NFKC covers this
    # plus more, but for ASCII chars it's equivalent, and for CJK it's compatible.
    result = []
    for c in s:
        cp = ord(c)
        # Fullwidth ASCII (U+FF01–U+FF5E) → halfwidth
        if 0xFF01 <= cp <= 0xFF5E:
            result.append(chr(cp - 0xFEE0))
        # Fullwidth space (U+3000) → ASCII space
        elif cp == 0x3000:
            result.append(" ")
        # Halfwidth katakana (U+FF65–U+FF9F) → fullwidth via NFKC
        elif 0xFF65 <= cp <= 0xFF9F:
            result.append(unicodedata.normalize("NFKC", c))
        else:
            result.append(c)
    return "".join(result)


def _normalize_punctuation(s: str) -> str:
    """Stage 2: curly quotes, dashes → ASCII equivalents."""
    for old, new in (
        ("\u2018", "'"), ("\u2019", "'"),
        ("\u201C", '"'), ("\u201D", '"'),
        ("\u2032", "'"), ("\u2033", '"'),
        ("`",      "'"), ("\u00B4", "'"),
        ("\u2013", "-"), ("\u2014", "-"),
        ("\u2015", "-"), ("\u2212", "-"), ("\u2012", "-"),
        ("\u2026", "..."),
    ):
        s = s.replace(old, new)
    return s


def _remove_diacritics(s: str) -> str:
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _transliterate_special_latin(s: str) -> str:
    for old, new in (
        ("Ł", "L"), ("ł", "l"),
        ("Ø", "O"), ("ø", "o"), ("Å", "A"), ("å", "a"),
        ("ß", "ss"), ("ẞ", "SS"),
        ("Æ", "AE"), ("æ", "ae"), ("Œ", "OE"), ("œ", "oe"),
        ("Þ", "TH"), ("þ", "th"), ("Ð", "D"), ("ð", "d"),
        ("Đ", "D"), ("đ", "d"),
    ):
        s = s.replace(old, new)
    return s


def _remove_arabic_vowel_marks(s: str) -> str:
    return "".join(c for c in s if not (0x064B <= ord(c) <= 0x065F))


def _remove_hebrew_vowel_marks(s: str) -> str:
    return "".join(c for c in s if not (0x0591 <= ord(c) <= 0x05C7))


def _remove_thai_tone_marks(s: str) -> str:
    return "".join(
        c for c in s
        if not (0x0E34 <= ord(c) <= 0x0E3A or 0x0E47 <= ord(c) <= 0x0E4E)
    )


def _normalize_by_script(s: str, script: str) -> str:
    if script == "cjk":
        return unicodedata.normalize("NFC", s)
    if script == "cyrillic":
        return _remove_diacritics(unicodedata.normalize("NFKC", s))
    if script == "greek":
        s = unicodedata.normalize("NFKC", s)
        s = _remove_diacritics(s)
        s = s.replace(";", "?").replace("ς", "σ")
        return s
    if script == "indic":
        return unicodedata.normalize("NFKC", s)
    if script == "arabic":
        s = unicodedata.normalize("NFKC", s)
        s = _remove_arabic_vowel_marks(s)
        for old, new in (("،", ","), ("؛", ";"), ("؟", "?")):
            s = s.replace(old, new)
        return s
    if script == "hebrew":
        return _remove_hebrew_vowel_marks(unicodedata.normalize("NFKC", s))
    if script == "thai":
        return _remove_thai_tone_marks(unicodedata.normalize("NFKC", s))
    if script in ("burmese", "khmer", "lao"):
        return unicodedata.normalize("NFKC", s)
    if script == "amharic":
        s = unicodedata.normalize("NFKC", s)
        for old, new in (("።", "."), ("፤", ";"), ("፣", ","), ("፡", " ")):
            s = s.replace(old, new)
        return s
    # latin / default: NFKC + special transliterations + diacritic removal
    s = unicodedata.normalize("NFKC", s)
    s = _transliterate_special_latin(s)
    s = s.replace("ı", "i").replace("İ", "I")  # Turkish
    s = _remove_diacritics(s)
    return s


def _normalize_unicode(s: str, script: str | None = None) -> str:
    """Stage 3: remove Unicode symbols, apply script-aware normalization."""
    s = "".join(
        c for c in s
        if unicodedata.category(c) not in ("So", "Sc")
    )
    if script is None:
        script = _detect_script(s)
    return _normalize_by_script(s, script)


# ── Separator / symbol normalization ──────────────────────────────────────────

def _normalize_symbols_and_separators(s: str) -> str:
    """Stage 4: conjunctions and separators → normalized forms."""
    s = s.replace(" & ", " and ").replace("&", " and ")
    s = s.replace(" + ", " and ")
    s = s.replace(" 'n' ", " and ").replace(" 'n ", " and ")
    s = s.replace(" n' ", " and ").replace(" n ", " and ")
    s = s.replace("+", " plus ")

    if not any(c in s for c in ":_/\\,;-"):
        return s

    result: list[str] = []
    chars = list(s)
    for i, c in enumerate(chars):
        if c in ":_/\\,;":
            result.append(" ")
        elif c == "-":
            prev_ok = i > 0 and (chars[i - 1].isalpha() or chars[i - 1].isdigit())
            next_ok = i < len(chars) - 1 and (chars[i + 1].isalpha() or chars[i + 1].isdigit())
            result.append("-" if (prev_ok and next_ok) else " ")
        else:
            result.append(c)
    return "".join(result)


# ── Game-specific helpers ──────────────────────────────────────────────────────

def _strip_metadata_brackets(s: str) -> str:
    result: list[str] = []
    paren = bracket = brace = angle = 0
    for c in s:
        if c == "(":   paren += 1
        elif c == ")": paren = max(0, paren - 1)
        elif c == "[": bracket += 1
        elif c == "]": bracket = max(0, bracket - 1)
        elif c == "{": brace += 1
        elif c == "}": brace = max(0, brace - 1)
        elif c == "<": angle += 1
        elif c == ">": angle = max(0, angle - 1)
        elif paren == 0 and bracket == 0 and brace == 0 and angle == 0:
            result.append(c)
    return "".join(result).strip()


def _strip_edition_and_version_suffixes(s: str) -> str:
    s = _EDITION_SUFFIX_RE.sub("", s).strip()
    s = _VERSION_SUFFIX_RE.sub("", s).strip()
    return s


def _collapse_dotted_initialisms(s: str) -> str:
    if "." not in s:
        return s
    return _DOTTED_INITIALISM_RE.sub(lambda m: m.group().replace(".", ""), s)


def _strip_leading_article(s: str) -> str:
    s = s.strip()
    lo = s.lower()
    if lo.startswith("the "):  return s[4:].strip()
    if lo.startswith("a "):    return s[2:].strip()
    if lo.startswith("an "):   return s[3:].strip()
    return s


def _split_and_strip_articles(s: str) -> str:
    """Split on first ':', ' - ', or \"'s \"; strip leading articles from both parts."""
    for delim, skip in ((":", 1), (" - ", 3), ("'s ", 3)):
        idx = s.find(delim)
        if idx == -1:
            continue
        if delim == "'s ":
            main = _strip_leading_article(s[:idx + 2])   # keep "'s"
            sub  = _strip_leading_article(s[idx + skip:])
        else:
            main = _strip_leading_article(s[:idx])
            sub  = _strip_leading_article(s[idx + skip:])
        return (main + " " + sub).strip()
    return _strip_leading_article(s)


def _strip_trailing_article(s: str) -> str:
    if _TRAILING_ARTICLE_RE.search(s):
        s = _TRAILING_ARTICLE_RE.sub(r"\1", s).strip()
    return s


def _expand_word(word: str) -> str | None:
    lo = word.lower()
    if lo in _PERIOD_REQUIRED_ABBREVS:
        return _PERIOD_REQUIRED_ABBREVS[lo]
    stripped = lo.rstrip(".")
    if stripped in _FLEXIBLE_ABBREVS:
        return _FLEXIBLE_ABBREVS[stripped]
    if lo in _NUMBER_WORDS:
        return _NUMBER_WORDS[lo]
    if stripped in _NUMBER_WORDS:
        return _NUMBER_WORDS[stripped]
    return None


def _expand_abbreviations_and_numbers(s: str) -> str:
    words = s.split()
    changed = False
    for i, w in enumerate(words):
        exp = _expand_word(w)
        if exp is not None:
            words[i] = exp
            changed = True
    return " ".join(words) if changed else s


def _normalize_ordinals(s: str) -> str:
    s = _ORDINAL_CAMEL_RE.sub(r"\1 \2", s)
    return _ORDINAL_SUFFIX_RE.sub(r"\1", s)


def _convert_roman_numerals(s: str) -> str:
    """Convert Roman numerals II–XIX (not X) to Arabic; lowercases entire string."""
    if not any(c in s for c in "ivxIVX"):
        return s.lower()

    chars = list(s)
    result: list[str] = []
    i = 0
    while i < len(chars):
        at_boundary = i == 0 or not _is_latin_word_char(chars[i - 1])

        # Don't convert when adjacent to Latin diacritics
        if i > 0:
            prev = chars[i - 1]
            if unicodedata.category(prev).startswith("L") and not _is_latin_word_char(prev):
                at_boundary = False
        if i < len(chars) - 1:
            nxt = chars[i + 1]
            if unicodedata.category(nxt).startswith("L") and not _is_latin_word_char(nxt):
                at_boundary = False

        if not at_boundary:
            result.append(chars[i].lower())
            i += 1
            continue

        matched = False
        for pattern, replacement in _ROMAN_NUMERALS:
            end = i + len(pattern)
            if end > len(chars):
                continue
            if "".join(chars[i:end]).upper() != pattern:
                continue
            if i == 0 and len(pattern) == 1:  # single letter at string start → skip
                continue
            at_end = end == len(chars) or not _is_latin_word_char(chars[end])
            if at_end:
                result.append(replacement)
                i = end
                matched = True
                break

        if not matched:
            result.append(chars[i].lower())
            i += 1

    return "".join(result)


# ── Core pipeline stages ───────────────────────────────────────────────────────

def _parse_game(title: str) -> str:
    """Game-specific normalization (mirrors Go ParseGame)."""
    s = title
    if not _is_ascii(s):
        s = _normalize_width(s)
    s = s.strip()
    s = _split_and_strip_articles(s)
    s = s.strip()
    s = _strip_trailing_article(s)
    s = s.strip()
    s = _strip_metadata_brackets(s)
    s = s.strip()
    s = _strip_edition_and_version_suffixes(s)
    s = s.strip()
    s = _collapse_dotted_initialisms(s)
    s = s.rstrip("-:;.,_/\\ ")

    # Inline separator normalization (no context-sensitive hyphen, no 'n' variants)
    s = s.replace(" & ", " and ").replace("&", " and ")
    s = s.replace(" + ", " and ").replace("+", " plus ")
    for sep in (":", "_", "/", "\\", ";", "."):
        s = s.replace(sep, " ")
    s = s.strip()

    s = _expand_abbreviations_and_numbers(s)
    s = _normalize_ordinals(s)
    s = _convert_roman_numerals(s)   # also lowercases
    return s


def _normalize_internal(s: str) -> tuple[str, str]:
    """Universal pipeline Stages 1–6. Returns (normalized_str, script)."""
    s = s.strip()
    if not s:
        return "", "latin"

    script = "latin"
    if not _is_ascii(s):
        s = _normalize_width(s)
        s = _normalize_punctuation(s)
        script = _detect_script(s)
        s = _normalize_unicode(s, script)

    s = _normalize_symbols_and_separators(s)
    s = s.replace(".", " ")
    s = s.lower()
    return s.strip(), script


def _tokenize_normalized(s: str) -> list[str]:
    """Extract word tokens, preserving internal apostrophes and hyphens."""
    buf: list[str] = []
    for c in s:
        if c.isalpha() or c.isnumeric():
            buf.append(c.lower())
        elif c in ("'", "-"):
            buf.append(c)
        else:
            buf.append(" ")
    tokens = "".join(buf).split()
    return [t.strip("'- ") for t in tokens if t.strip("'- ")]


# ── Public API ─────────────────────────────────────────────────────────────────

def slugify_game(title: str) -> SlugifyResult:
    """
    Equivalent to Go: SlugifyWithTokens(MediaTypeGame, title)

    Returns SlugifyResult(slug, tokens).
    """
    parsed = _parse_game(title)
    s, script = _normalize_internal(parsed)
    if not s:
        return SlugifyResult(slug="", tokens=[])

    tokens = _tokenize_normalized(s)

    if _needs_unicode_slug(script):
        slug = _NON_ALPHANUM_UNICODE_RE.sub("", s).strip()
    else:
        slug = _NON_ALPHANUM_ASCII_RE.sub("", s)

    return SlugifyResult(slug=slug, tokens=tokens)


def slugify_game_str(title: str) -> str:
    """Returns just the slug string."""
    return slugify_game(title).slug


assert slugify_game_str("The Legend of Zelda: Ocarina of Time (USA) [!]") == "legendofzeldaocarinaoftime"
assert slugify_game_str("Super Mario Bros. III (USA) [!]") == "supermariobrothers3"
assert slugify_game_str("Final Fantasy VII") == "finalfantasy7"
assert slugify_game_str("Mega Man X") == "megamanx"
assert slugify_game_str("Street Fighter II Version") == "streetfighter2"
assert slugify_game_str("Pokemon Red Version") == "pokemonred"