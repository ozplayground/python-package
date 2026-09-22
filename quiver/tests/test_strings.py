"""Tests for quiver.strings module.

Covers case conversions, slugify, truncate, and mask_sensitive.
"""

import pytest

from quiver.strings import (
    mask_sensitive,
    slugify,
    to_camel_case,
    to_kebab_case,
    to_pascal_case,
    to_snake_case,
    truncate,
)


# ==========================================
# 1. Case conversion tests
# ==========================================
class TestCaseConversions:
    @pytest.mark.parametrize(
        "input_str,expected",
        [
            ("hello_world", "helloWorld"),
            ("Hello World", "helloWorld"),
            ("hello-world", "helloWorld"),
            ("HelloWorld", "helloWorld"),
            ("HTTPResponse", "httpResponse"),
            ("user_id_123", "userId123"),
            ("", ""),
            (None, ""),
        ],
    )
    def test_to_camel_case(self, input_str, expected):
        assert to_camel_case(input_str) == expected

    @pytest.mark.parametrize(
        "input_str,expected",
        [
            ("helloWorld", "hello_world"),
            ("HelloWorld", "hello_world"),
            ("hello-world", "hello_world"),
            ("Hello World", "hello_world"),
            ("HTTPResponse", "http_response"),
            ("user_id_123", "user_id_123"),
            ("", ""),
            (None, ""),
        ],
    )
    def test_to_snake_case(self, input_str, expected):
        assert to_snake_case(input_str) == expected

    @pytest.mark.parametrize(
        "input_str,expected",
        [
            ("helloWorld", "hello-world"),
            ("HelloWorld", "hello-world"),
            ("hello_world", "hello-world"),
            ("Hello World", "hello-world"),
            ("HTTPResponse", "http-response"),
            ("", ""),
            (None, ""),
        ],
    )
    def test_to_kebab_case(self, input_str, expected):
        assert to_kebab_case(input_str) == expected

    @pytest.mark.parametrize(
        "input_str,expected",
        [
            ("hello_world", "HelloWorld"),
            ("helloWorld", "HelloWorld"),
            ("hello-world", "HelloWorld"),
            ("Hello World", "HelloWorld"),
            ("http_response", "HttpResponse"),
            ("", ""),
            (None, ""),
        ],
    )
    def test_to_pascal_case(self, input_str, expected):
        assert to_pascal_case(input_str) == expected


# ==========================================
# 2. slugify tests
# ==========================================
class TestSlugify:
    def test_slugify_ascii(self):
        assert slugify("Hello, World!") == "hello-world"
        assert slugify("  Multiple   Spaces   Here  ") == "multiple-spaces-here"
        assert slugify("---Leading and Trailing---") == "leading-and-trailing"

    def test_slugify_custom_separator(self):
        assert slugify("Hello World", separator="_") == "hello_world"

    def test_slugify_unicode(self):
        # Default: ascii only, converts accents
        assert slugify("Café au Lait") == "cafe-au-lait"
        # allow_unicode=True keeps unicode characters
        assert slugify("안녕하세요 세계", allow_unicode=True) == "안녕하세요-세계"

    def test_slugify_empty_or_none(self):
        assert slugify("") == ""
        assert slugify(None) == ""


# ==========================================
# 3. truncate tests
# ==========================================
class TestTruncate:
    def test_truncate_within_length(self):
        text = "Short text"
        assert truncate(text, 20) == text

    def test_truncate_preserve_words(self):
        text = "The quick brown fox jumps over the lazy dog"
        # length 18: "The quick brown..." (length 18)
        truncated = truncate(text, length=18, preserve_words=True)
        assert truncated == "The quick brown..."
        assert len(truncated) <= 18

    def test_truncate_no_preserve_words(self):
        text = "The quick brown fox"
        truncated = truncate(text, length=10, suffix="...", preserve_words=False)
        assert truncated == "The qui..."
        assert len(truncated) == 10

    def test_truncate_custom_suffix(self):
        text = "Hello world from python"
        assert truncate(text, length=15, suffix=" [more]") == "Hello [more]"

    def test_truncate_single_long_word(self):
        text = "Supercalifragilisticexpialidocious"
        truncated = truncate(text, length=10, preserve_words=True)
        assert truncated == "Superca..."
        assert len(truncated) == 10

    def test_truncate_empty_or_none(self):
        assert truncate("", 10) == ""
        assert truncate(None, 10) == ""

    def test_truncate_invalid_length(self):
        with pytest.raises(ValueError, match="length must be >= len"):
            truncate("Hello", length=2, suffix="...")


# ==========================================
# 4. mask_sensitive tests
# ==========================================
class TestMaskSensitive:
    def test_mask_email(self):
        assert (
            mask_sensitive("engineer@company.com", pattern_type="email")
            == "e******r@company.com"
        )
        assert mask_sensitive("ab@example.com", pattern_type="email") == "a*@example.com"
        assert mask_sensitive("a@example.com", pattern_type="email") == "*@example.com"

    def test_mask_phone(self):
        assert (
            mask_sensitive("010-1234-5678", pattern_type="phone")
            == "010-****-5678"
        )
        assert (
            mask_sensitive("01012345678", pattern_type="phone")
            == "010****5678"
        )

    def test_mask_rrn(self):
        assert (
            mask_sensitive("900101-1234567", pattern_type="rrn")
            == "900101-1******"
        )
        assert (
            mask_sensitive("9001011234567", pattern_type="rrn")
            == "9001011******"
        )

    def test_mask_card(self):
        assert (
            mask_sensitive("1234-5678-9012-3456", pattern_type="card")
            == "1234-****-****-3456"
        )
        assert (
            mask_sensitive("1234567890123456", pattern_type="card")
            == "1234********3456"
        )

    def test_mask_generic_prefix_suffix(self):
        text = "SECRET_TOKEN_VALUE"
        masked = mask_sensitive(text, keep_prefix=2, keep_suffix=3, mask_char="#")
        assert masked == "SE#############LUE"
        assert len(masked) == len(text)

    def test_mask_prefix_suffix_exceeds_length(self):
        assert mask_sensitive("abc", keep_prefix=2, keep_suffix=2) == "abc"

    def test_mask_empty_or_none(self):
        assert mask_sensitive("", pattern_type="email") == ""
        assert mask_sensitive(None, pattern_type="phone") == ""

    def test_mask_invalid_args(self):
        with pytest.raises(ValueError, match="mask_char must be a single character"):
            mask_sensitive("test", mask_char="**")
        with pytest.raises(ValueError, match="Unsupported pattern_type"):
            mask_sensitive("test", pattern_type="passport")  # type: ignore
