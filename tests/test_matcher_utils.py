from classifiers.common import sanitize_sheet_name, contains_any
from classifiers.normalizer import normalize_text


def test_sanitize_sheet_name_removes_invalid_chars():
    assert sanitize_sheet_name("Por Tribunal/Sistema") == "Por Tribunal_Sistema"


def test_sanitize_sheet_name_limits_length():
    name = "a" * 50
    assert len(sanitize_sheet_name(name)) == 31


def test_normalize_text_removes_accents_and_lowercases():
    assert normalize_text("AÇÃO DE CUMPRIMENTO") == "acao de cumprimento"


def test_contains_any_finds_term():
    text = "processo de agravo de instrumento civel"
    assert contains_any(text, ["embargos", "agravo de instrumento"]) == "agravo de instrumento"