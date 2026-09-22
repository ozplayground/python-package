"""quiver.strings: String transformers, case conversions, slugification, and data masking.

Provides case transformations, URL-friendly slug creation, smart word-boundary truncation,
and privacy/financial data masking with ReDoS-safe patterns.
"""

from typing import Literal, Optional
import re
import unicodedata

_SPLIT_REGEX_1 = re.compile(r"([A-Z]+)([A-Z][a-z])")
_SPLIT_REGEX_2 = re.compile(r"([a-z\d])([A-Z])")
_WORD_REGEX = re.compile(r"[a-zA-Z\d]+")

_PHONE_DASH_REGEX = re.compile(r"^(\d{2,4})-(\d{3,4})-(\d{4})$")
_PHONE_DIGIT_REGEX = re.compile(r"^\d{10,11}$")
_RRN_DASH_REGEX = re.compile(r"^(\d{6})-([1-8])(\d{6})$")
_RRN_DIGIT_REGEX = re.compile(r"^(\d{6})([1-8])(\d{6})$")
_CARD_DASH_REGEX = re.compile(r"^(\d{4})-(\d{4})-(\d{4})-(\d{4})$")
_CARD_DIGIT_REGEX = re.compile(r"^\d{15,16}$")


def _tokenize(text: Optional[str]) -> list[str]:
    """Tokenize a string into lowercased alphanumeric words."""
    if not text:
        return []
    s = _SPLIT_REGEX_1.sub(r"\1_\2", text)
    s = _SPLIT_REGEX_2.sub(r"\1_\2", s)
    return [w.lower() for w in _WORD_REGEX.findall(s)]


def to_camel_case(text: Optional[str]) -> str:
    """Convert a string to camelCase."""
    words = _tokenize(text)
    if not words:
        return ""
    return words[0] + "".join(w.capitalize() for w in words[1:])


def to_snake_case(text: Optional[str]) -> str:
    """Convert a string to snake_case."""
    words = _tokenize(text)
    return "_".join(words)


def to_kebab_case(text: Optional[str]) -> str:
    """Convert a string to kebab-case."""
    words = _tokenize(text)
    return "-".join(words)


def to_pascal_case(text: Optional[str]) -> str:
    """Convert a string to PascalCase."""
    words = _tokenize(text)
    return "".join(w.capitalize() for w in words)


def slugify(
    text: Optional[str],
    separator: str = "-",
    allow_unicode: bool = False,
) -> str:
    """Convert a string to a normalized, URL-safe slug."""
    if not text:
        return ""

    if not allow_unicode:
        cleaned = (
            unicodedata.normalize("NFKD", text)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
        cleaned = cleaned.lower()
        cleaned = re.sub(r"[^a-z0-9\s-]", "", cleaned)
    else:
        cleaned = unicodedata.normalize("NFKC", text).lower()
        cleaned = re.sub(r"[^\w\s-]", "", cleaned)

    cleaned = re.sub(r"[-\s]+", separator, cleaned).strip(separator)
    return cleaned


def truncate(
    text: Optional[str],
    length: int,
    suffix: str = "...",
    preserve_words: bool = True,
) -> str:
    """Truncate text to at most `length` characters, optionally preserving word boundaries."""
    if not text:
        return ""

    suffix_len = len(suffix)
    if length < suffix_len:
        raise ValueError(
            f"length must be >= len(suffix) ({suffix_len}), got {length}"
        )

    if len(text) <= length:
        return text

    target_len = length - suffix_len
    if not preserve_words:
        return text[:target_len] + suffix

    cut = text[:target_len]
    if text[target_len] == " ":
        cut = cut.rstrip()
    else:
        last_space = cut.rfind(" ")
        if last_space != -1:
            cut = cut[:last_space].rstrip()

    return cut + suffix


def mask_sensitive(
    text: Optional[str],
    pattern_type: Optional[Literal["email", "phone", "rrn", "card"]] = None,
    mask_char: str = "*",
    keep_prefix: int = 0,
    keep_suffix: int = 0,
) -> str:
    """Mask sensitive information such as emails, phone numbers, RRNs, or card numbers."""
    if not text:
        return ""

    if len(mask_char) != 1:
        raise ValueError("mask_char must be a single character")

    if pattern_type is not None and pattern_type not in (
        "email",
        "phone",
        "rrn",
        "card",
    ):
        raise ValueError(f"Unsupported pattern_type: {pattern_type}")

    if pattern_type == "email":
        if "@" in text:
            user, domain = text.rsplit("@", 1)
            if len(user) <= 1:
                masked_user = mask_char
            elif len(user) == 2:
                masked_user = user[0] + mask_char
            else:
                masked_user = user[0] + (mask_char * (len(user) - 2)) + user[-1]
            return f"{masked_user}@{domain}"

    elif pattern_type == "phone":
        m_dash = _PHONE_DASH_REGEX.match(text)
        if m_dash:
            return f"{m_dash.group(1)}-{mask_char * len(m_dash.group(2))}-{m_dash.group(3)}"
        if _PHONE_DIGIT_REGEX.match(text):
            return f"{text[:3]}{mask_char * (len(text) - 7)}{text[-4:]}"

    elif pattern_type == "rrn":
        m_rrn_dash = _RRN_DASH_REGEX.match(text)
        if m_rrn_dash:
            return f"{m_rrn_dash.group(1)}-{m_rrn_dash.group(2)}{mask_char * 6}"
        m_rrn_digit = _RRN_DIGIT_REGEX.match(text)
        if m_rrn_digit:
            return f"{m_rrn_digit.group(1)}{m_rrn_digit.group(2)}{mask_char * 6}"

    elif pattern_type == "card":
        m_card_dash = _CARD_DASH_REGEX.match(text)
        if m_card_dash:
            return f"{m_card_dash.group(1)}-{mask_char * 4}-{mask_char * 4}-{m_card_dash.group(4)}"
        if _CARD_DIGIT_REGEX.match(text):
            return f"{text[:4]}{mask_char * (len(text) - 8)}{text[-4:]}"

    # Generic masking fallback using keep_prefix and keep_suffix
    if keep_prefix + keep_suffix >= len(text):
        return text

    prefix = text[:keep_prefix]
    suffix_part = text[len(text) - keep_suffix :] if keep_suffix > 0 else ""
    masked_count = len(text) - keep_prefix - keep_suffix
    return f"{prefix}{mask_char * masked_count}{suffix_part}"
