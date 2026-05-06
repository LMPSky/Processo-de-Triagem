from classifiers.trabalhista import classify_trabalhista_text

def test_classify_trabalhista_acao_trabalhista():
    text = "Trata-se de ação trabalhista rito ordinário."
    assert classify_trabalhista_text(text) == "Ação Trabalhista"

def test_classify_trabalhista_embargos():
    text = "O presente caso envolve embargos de declaração."
    assert classify_trabalhista_text(text) == "Embargos de Declaração"