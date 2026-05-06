"""Testes para o módulo number_extractor."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from number_extractor import extract_all_numbers, normalize_number


class TestNormalizeNumber:
    def test_remove_hyphens_and_dots(self):
        assert normalize_number("0001234-56.2020.8.26.0001") == "00012345620208260001"

    def test_remove_slashes(self):
        assert normalize_number("2025/0379643-0") == "202503796430"

    def test_empty_string(self):
        assert normalize_number("") == ""

    def test_none_returns_empty(self):
        assert normalize_number(None) == ""

    def test_plain_digits_unchanged(self):
        assert normalize_number("12345") == "12345"


class TestExtractAllNumbers:
    def test_extracts_cnj(self):
        cnj = "0001234-56.2020.8.26.0001"
        result = extract_all_numbers(cnj)
        assert cnj in result

    def test_extracts_cnj_digits_only(self):
        cnj = "0001234-56.2020.8.26.0001"
        result = extract_all_numbers(cnj)
        # Should also contain the version without punctuation
        assert "00012345620208260001" in result

    def test_extracts_stj_registro(self):
        result = extract_all_numbers("2025/0379643-0")
        assert "2025/0379643-0" in result

    def test_empty_returns_empty_set(self):
        assert extract_all_numbers("") == set()
        assert extract_all_numbers("   ") == set()

    def test_plain_digits(self):
        result = extract_all_numbers("12345678")
        assert "12345678" in result

    def test_cnj_embedded_in_text(self):
        text = "Processo: 0001234-56.2020.8.26.0001 — em andamento"
        result = extract_all_numbers(text)
        assert "0001234-56.2020.8.26.0001" in result
