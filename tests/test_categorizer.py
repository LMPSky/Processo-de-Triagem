"""Testes para o módulo categorizer."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from categorizer import classify_text, _truncate_text_column, CATEGORIES


class TestClassifyText:
    def test_none_returns_none(self):
        assert classify_text(None) is None

    def test_empty_returns_none(self):
        assert classify_text("") is None
        assert classify_text("   ") is None

    def test_cumprimento_de_sentenca(self):
        assert classify_text("Cumprimento de Sentença") == "Cumprimento de Sentença"

    def test_execucao_fiscal(self):
        assert classify_text("Execução Fiscal") == "Execução Fiscal"

    def test_mandado_de_seguranca(self):
        assert classify_text("Mandado de Segurança Cível") == "Mandado de Segurança"

    def test_decio_freire(self):
        assert classify_text("Décio Freire") == "Décio Freire"
        assert classify_text("Decio Flavio Goncalves Torres Freire") == "Décio Freire"

    def test_carta_precatoria(self):
        assert classify_text("Carta Precatória") == "Carta Precatória"

    def test_unrecognized_returns_none(self):
        assert classify_text("Ação Ordinária Genérica") is None

    def test_case_insensitive_match(self):
        # Os termos são matchados com re.IGNORECASE
        assert classify_text("execução fiscal") == "Execução Fiscal"
        assert classify_text("EXECUÇÃO FISCAL") == "Execução Fiscal"

    def test_all_categories_have_at_least_one_term(self):
        for category, terms in CATEGORIES.items():
            assert len(terms) > 0, f"Categoria '{category}' sem termos"


class TestTruncateTextColumn:
    def test_long_text_is_truncated(self):
        df = pd.DataFrame({"_texto": ["A" * 600]})
        result = _truncate_text_column(df)
        assert result.loc[0, "_texto"].endswith("... [TRUNCADO]")
        assert len(result.loc[0, "_texto"]) < 600

    def test_short_text_unchanged(self):
        df = pd.DataFrame({"_texto": ["Texto curto"]})
        result = _truncate_text_column(df)
        assert result.loc[0, "_texto"] == "Texto curto"

    def test_no_texto_column(self):
        df = pd.DataFrame({"outra": ["valor"]})
        result = _truncate_text_column(df)
        assert "outra" in result.columns

    def test_does_not_modify_original(self):
        df = pd.DataFrame({"_texto": ["A" * 600]})
        _truncate_text_column(df)
        assert len(df.loc[0, "_texto"]) == 600  # original intacto
