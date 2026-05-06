from ui.result_visuals import (
    severity_colors,
    health_card_colors,
    extract_alert_lines,
)


def test_severity_colors_for_alta():
    bg, fg, border = severity_colors("alta")
    assert bg == "#fef2f2"
    assert fg == "#dc2626"
    assert border == "#fecaca"


def test_severity_colors_for_media():
    bg, fg, border = severity_colors("media")
    assert bg == "#fff7ed"
    assert fg == "#ea580c"
    assert border == "#fdba74"


def test_severity_colors_for_baixa():
    bg, fg, border = severity_colors("baixa")
    assert bg == "#fefce8"
    assert fg == "#a16207"
    assert border == "#fde68a"


def test_severity_colors_for_unknown():
    bg, fg, border = severity_colors("qualquer")
    assert bg == "#f8fafc"
    assert fg == "#475569"
    assert border == "#cbd5e1"


def test_health_card_colors_for_saudavel():
    bg, fg, border = health_card_colors("Saudável")
    assert bg == "#ecfdf5"
    assert fg == "#047857"
    assert border == "#a7f3d0"


def test_health_card_colors_for_atencao():
    bg, fg, border = health_card_colors("Atenção")
    assert bg == "#fff7ed"
    assert fg == "#c2410c"
    assert border == "#fdba74"


def test_health_card_colors_for_critica():
    bg, fg, border = health_card_colors("Crítica")
    assert bg == "#fef2f2"
    assert fg == "#b91c1c"
    assert border == "#fecaca"


def test_health_card_colors_for_unknown():
    bg, fg, border = health_card_colors("desconhecido")
    assert bg == "#f8fafc"
    assert fg == "#475569"
    assert border == "#cbd5e1"


def test_extract_alert_lines_detects_severities():
    alert_text = (
        "• [ALTA] sem_match está acima da média\n"
        "• [MEDIA] queda de arquivos gerados\n"
        "• [BAIXA] queda de consolidados\n"
        "• mensagem informativa sem severidade"
    )

    lines = extract_alert_lines(alert_text)

    assert lines == [
        ("alta", "• [ALTA] sem_match está acima da média"),
        ("media", "• [MEDIA] queda de arquivos gerados"),
        ("baixa", "• [BAIXA] queda de consolidados"),
        ("info", "• mensagem informativa sem severidade"),
    ]


def test_extract_alert_lines_ignores_empty_lines():
    alert_text = "\n\n• [ALTA] alerta importante\n\n"
    lines = extract_alert_lines(alert_text)

    assert lines == [
        ("alta", "• [ALTA] alerta importante"),
    ]


def test_extract_alert_lines_with_empty_text():
    lines = extract_alert_lines("")
    assert lines == []