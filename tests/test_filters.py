"""Testes para o módulo filters."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from filters import (
    classify_number,
    remove_duplicates,
    add_number_classification,
    _validate_cnj_check_digit,
    _parse_cnj,
    add_age_flag,
    _UF_POR_TRIBUNAL_ESTADUAL,
    _UF_POR_TRIBUNAL_FEDERAL,
)


class TestClassifyNumber:
    def test_cnj_format(self):
        assert classify_number("0001234-56.2020.8.26.0001") == "cnj"

    def test_empty_string(self):
        assert classify_number("") == "vazio"

    def test_sem_expediente(self):
        assert classify_number("sem expediente") == "sem_expediente"
        assert classify_number("não localizado") == "sem_expediente"
        assert classify_number("n/a") == "sem_expediente"

    def test_stj_registro(self):
        assert classify_number("2025/0379643-0") == "stj"

    def test_numero_puro(self):
        assert classify_number("123456789") == "numero_puro"

    def test_texto(self):
        assert classify_number("Processo Trabalhista") == "texto"


class TestRemoveDuplicates:
    def test_removes_duplicate_cnjs(self):
        df = pd.DataFrame({
            "cnj": ["0001234-56.2020.8.26.0001", "0001234-56.2020.8.26.0001", "0009999-11.2021.8.26.0002"],
            "_fonte": ["painel", "dw", "painel"],
        })
        unique, dups = remove_duplicates(df)
        assert len(unique) == 2
        assert len(dups) == 1

    def test_no_duplicates(self):
        df = pd.DataFrame({
            "cnj": ["0001234-56.2020.8.26.0001", "0009999-11.2021.8.26.0002"],
            "_fonte": ["painel", "dw"],
        })
        unique, dups = remove_duplicates(df)
        assert len(unique) == 2
        assert len(dups) == 0

    def test_all_duplicates_one_kept(self):
        df = pd.DataFrame({
            "cnj": ["0001234-56.2020.8.26.0001"] * 5,
            "_fonte": ["painel"] * 5,
        })
        unique, dups = remove_duplicates(df)
        assert len(unique) == 1
        assert len(dups) == 4


class TestParseCnj:
    def test_valid_estadual(self):
        result = _parse_cnj("0001234-56.2020.8.26.0001")
        assert result["ano_processo"] == "2020"
        assert result["ramo_justica"] == "Justiça Estadual"
        assert result["uf"] == "SP"  # tribunal 26 → SP

    def test_valid_trabalho(self):
        result = _parse_cnj("0001234-56.2020.5.14.0001")
        assert result["ramo_justica"] == "Justiça do Trabalho"
        assert result["uf"] == "TRT-14"

    def test_valid_federal(self):
        result = _parse_cnj("0001234-56.2020.4.01.0001")
        assert result["ramo_justica"] == "Justiça Federal"
        assert result["uf"] == "DF"  # tribunal 01 → DF (federal)

    def test_invalid_format(self):
        assert _parse_cnj("not-a-cnj") == {}

    def test_empty(self):
        assert _parse_cnj("") == {}


class TestUfPorTribunalNoKeyCollision:
    """Garante que os dicionários Federal e Estadual não se confundem."""

    def test_estadual_tribunal_01_is_ac(self):
        assert _UF_POR_TRIBUNAL_ESTADUAL["01"] == "AC"

    def test_federal_tribunal_01_is_df(self):
        assert _UF_POR_TRIBUNAL_FEDERAL["01"] == "DF"

    def test_estadual_tribunal_26_is_sp(self):
        assert _UF_POR_TRIBUNAL_ESTADUAL["26"] == "SP"

    def test_federal_tribunal_06_is_mg(self):
        assert _UF_POR_TRIBUNAL_FEDERAL["06"] == "MG"


class TestValidateCnjCheckDigit:
    def test_valid_cnj(self):
        # 0001234-19.2020.8.26.0001 → int("000123419202082600011") % 97 == 1
        assert _validate_cnj_check_digit("0001234-19.2020.8.26.0001") is True

    def test_wrong_digit(self):
        assert _validate_cnj_check_digit("0000001-00.2019.8.26.0001") is False

    def test_invalid_format(self):
        assert _validate_cnj_check_digit("not-a-cnj") is False


class TestAddAgeFlag:
    def test_marks_old_processes(self):
        df = pd.DataFrame({
            "cnj": ["0001234-56.2010.8.26.0001"],
            "tipo_numero": ["cnj"],
            "ano_processo": ["2010"],
        })
        result = add_age_flag(df, cutoff_year=2015)
        assert bool(result.loc[0, "processo_antigo"]) is True

    def test_marks_recent_processes(self):
        df = pd.DataFrame({
            "cnj": ["0001234-56.2020.8.26.0001"],
            "tipo_numero": ["cnj"],
            "ano_processo": ["2020"],
        })
        result = add_age_flag(df, cutoff_year=2015)
        assert bool(result.loc[0, "processo_antigo"]) is False
