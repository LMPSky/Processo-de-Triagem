import pandas as pd
from matcher import classify_civel_record

def test_classify_civel_priority_name():
    row = pd.Series({
        "_texto": "Publicação em nome de Décio Freire referente ao processo.",
        "_cliente": "",
        "cnj": "0001234-56.2026.8.13.0000"
    })
    result = classify_civel_record(row)
    assert result["_prioridade_civel"] == "PRIORIDADE"

def test_classify_civel_excludente():
    row = pd.Series({
        "_texto": "Ação envolvendo Telemar.",
        "_cliente": "",
        "cnj": "0001234-56.2026.8.13.0000"
    })
    result = classify_civel_record(row)
    assert result["_categoria_civel"] == "EXCLUIDO"

def test_classify_civel_categoria_especifica():
    row = pd.Series({
        "_texto": "Trata-se de agravo de instrumento interposto.",
        "_cliente": "",
        "cnj": "0001234-56.2026.8.13.0000"
    })
    result = classify_civel_record(row)
    assert result["_categoria_civel"] == "Agravo de Instrumento"
    assert result["_confidence_civel"] >= 90

def test_classify_civel_numero_relevante():
    row = pd.Series({
        "_texto": "Processo distribuído recentemente.",
        "_cliente": "",
        "cnj": "0001234-56.2026.8.13.0000"
    })
    result = classify_civel_record(row)
    assert result["_subcategoria_civel"] == "numero_relevante"