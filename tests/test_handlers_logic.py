def test_build_execution_comparison_with_previous_row(handler):
    current_row = {
        "timestamp": "20260423_120000",
        "status": "sucesso",
        "arquivos_gerados": "10",
        "novos_arquivos": "4",
        "consolidados_gerados": "3",
        "linhas_sem_match": "12",
        "linhas_numero_puro": "5",
        "linhas_outro": "2",
    }
    previous_row = {
        "timestamp": "20260423_110000",
        "status": "sucesso",
        "arquivos_gerados": "8",
        "novos_arquivos": "2",
        "consolidados_gerados": "4",
        "linhas_sem_match": "10",
        "linhas_numero_puro": "4",
        "linhas_outro": "1",
    }

    result = handler._build_execution_comparison(current_row, previous_row)

    assert result["execucao_atual"] == "20260423_120000"
    assert result["execucao_anterior"] == "20260423_110000"

    assert result["comparacoes"]["arquivos_gerados"]["delta"] == 2
    assert result["comparacoes"]["novos_arquivos"]["delta"] == 2
    assert result["comparacoes"]["consolidados_gerados"]["delta"] == -1
    assert result["comparacoes"]["linhas_sem_match"]["delta"] == 2


def test_build_execution_comparison_without_previous_row(handler):
    current_row = {
        "timestamp": "20260423_120000",
        "status": "sucesso",
    }

    result = handler._build_execution_comparison(current_row, None)

    assert result["execucao_atual"] == "20260423_120000"
    assert result["execucao_anterior"] == ""
    assert "mensagem" in result
    assert result["comparacoes"] == {}


def test_build_average_comparison_with_reference_rows(handler):
    current_row = {
        "timestamp": "20260423_120000",
        "arquivos_gerados": "10",
        "novos_arquivos": "6",
        "consolidados_gerados": "3",
        "linhas_sem_match": "20",
        "linhas_numero_puro": "7",
        "linhas_outro": "4",
    }
    reference_rows = [
        {
            "timestamp": "20260423_100000",
            "arquivos_gerados": "8",
            "novos_arquivos": "4",
            "consolidados_gerados": "4",
            "linhas_sem_match": "10",
            "linhas_numero_puro": "5",
            "linhas_outro": "2",
        },
        {
            "timestamp": "20260423_101000",
            "arquivos_gerados": "12",
            "novos_arquivos": "6",
            "consolidados_gerados": "2",
            "linhas_sem_match": "20",
            "linhas_numero_puro": "7",
            "linhas_outro": "4",
        },
    ]

    result = handler._build_average_comparison(current_row, reference_rows)

    assert result["execucao_atual"] == "20260423_120000"
    assert result["quantidade_execucoes_referencia"] == 2

    assert result["comparacoes"]["arquivos_gerados"]["media_referencia"] == 10.0
    assert result["comparacoes"]["arquivos_gerados"]["atual"] == 10
    assert result["comparacoes"]["arquivos_gerados"]["delta_vs_media"] == 0.0

    assert result["comparacoes"]["linhas_sem_match"]["media_referencia"] == 15.0
    assert result["comparacoes"]["linhas_sem_match"]["delta_vs_media"] == 5.0


def test_build_average_comparison_without_reference_rows(handler):
    current_row = {"timestamp": "20260423_120000"}

    result = handler._build_average_comparison(current_row, [])

    assert result["execucao_atual"] == "20260423_120000"
    assert result["quantidade_execucoes_referencia"] == 0
    assert "mensagem" in result
    assert result["comparacoes"] == {}


def test_build_comparison_ui_summary_with_previous_data(handler):
    comparison = {
        "execucao_anterior": "20260423_110000",
        "comparacoes": {
            "arquivos_gerados": {"delta": 3},
            "consolidados_gerados": {"delta": -1},
            "linhas_sem_match": {"delta": 0},
        },
    }

    result = handler._build_comparison_ui_summary(comparison)

    assert result["Δ Arquivos gerados"] == "+3"
    assert result["Δ Consolidados gerados"] == "-1"
    assert result["Δ Linhas sem_match"] == "0"


def test_build_comparison_ui_summary_without_previous_data(handler):
    comparison = {
        "execucao_anterior": "",
        "comparacoes": {},
    }

    result = handler._build_comparison_ui_summary(comparison)

    assert result["Δ Arquivos gerados"] == "N/D"
    assert result["Δ Consolidados gerados"] == "N/D"
    assert result["Δ Linhas sem_match"] == "N/D"


def test_build_average_comparison_ui_summary_with_reference_data(handler):
    average_comparison = {
        "quantidade_execucoes_referencia": 3,
        "comparacoes": {
            "linhas_sem_match": {"delta_vs_media": 7.25},
            "arquivos_gerados": {"delta_vs_media": -2.5},
        },
    }

    result = handler._build_average_comparison_ui_summary(average_comparison)

    assert result["Δ vs média - sem_match"] == "+7.25"
    assert result["Δ vs média - arquivos gerados"] == "-2.50"


def test_build_average_comparison_ui_summary_without_reference_data(handler):
    average_comparison = {
        "quantidade_execucoes_referencia": 0,
        "comparacoes": {},
    }

    result = handler._build_average_comparison_ui_summary(average_comparison)

    assert result["Δ vs média - sem_match"] == "N/D"
    assert result["Δ vs média - arquivos gerados"] == "N/D"


def test_build_regression_alerts_without_history(handler):
    comparison = {
        "execucao_anterior": "",
        "comparacoes": {},
    }
    average_comparison = {
        "quantidade_execucoes_referencia": 0,
        "comparacoes": {},
    }

    result = handler._build_regression_alerts(comparison, average_comparison)

    assert result["quantidade_alertas"] == 0
    assert result["alertas"] == []
    assert "sem base histórica suficiente" in result["texto_resumo"].lower()


def test_build_regression_alerts_with_previous_and_average(handler):
    comparison = {
        "execucao_anterior": "20260423_110000",
        "comparacoes": {
            "linhas_sem_match": {"delta": 5},
            "arquivos_gerados": {"delta": -2},
            "consolidados_gerados": {"delta": -1},
        },
    }
    average_comparison = {
        "quantidade_execucoes_referencia": 5,
        "comparacoes": {
            "linhas_sem_match": {"delta_vs_media": 4.5},
            "arquivos_gerados": {"delta_vs_media": -3.25},
        },
    }

    result = handler._build_regression_alerts(comparison, average_comparison)

    assert result["quantidade_alertas"] == 5
    tipos = [item["tipo"] for item in result["alertas"]]

    assert "aumento_sem_match_vs_anterior" in tipos
    assert "queda_arquivos_gerados_vs_anterior" in tipos
    assert "queda_consolidados_gerados_vs_anterior" in tipos
    assert "aumento_sem_match_vs_media" in tipos
    assert "queda_arquivos_gerados_vs_media" in tipos
    assert any(item["severidade"] == "alta" for item in result["alertas"])
    assert any(item["severidade"] == "media" for item in result["alertas"])
    assert any(item["severidade"] == "baixa" for item in result["alertas"])


def test_build_regression_alerts_with_no_regression(handler):
    comparison = {
        "execucao_anterior": "20260423_110000",
        "comparacoes": {
            "linhas_sem_match": {"delta": -2},
            "arquivos_gerados": {"delta": 3},
            "consolidados_gerados": {"delta": 0},
        },
    }
    average_comparison = {
        "quantidade_execucoes_referencia": 5,
        "comparacoes": {
            "linhas_sem_match": {"delta_vs_media": -1.5},
            "arquivos_gerados": {"delta_vs_media": 2.0},
        },
    }

    result = handler._build_regression_alerts(comparison, average_comparison)

    assert result["quantidade_alertas"] == 0
    assert result["texto_resumo"] == "Nenhum alerta"


def test_build_execution_health_summary_saudavel(handler):
    comparison_ui = {
        "Δ Linhas sem_match": "-2",
        "Δ Arquivos gerados": "+3",
    }
    average_ui = {
        "Δ vs média - sem_match": "-1.00",
        "Δ vs média - arquivos gerados": "+2.00",
    }
    alerts = {
        "quantidade_alertas": 0,
    }

    result = handler._build_execution_health_summary(comparison_ui, average_ui, alerts)

    assert result["Saúde da execução"] == "Saudável"
    assert result["Nível de atenção"] == "Baixo"
    assert result["Tendência do sem_match"] == "Estável/Melhorando"
    assert result["Tendência dos arquivos gerados"] == "Estável/Melhorando"


def test_build_execution_health_summary_atencao(handler):
    comparison_ui = {
        "Δ Linhas sem_match": "+2",
        "Δ Arquivos gerados": "+1",
    }
    average_ui = {
        "Δ vs média - sem_match": "-1.00",
        "Δ vs média - arquivos gerados": "-2.00",
    }
    alerts = {
        "quantidade_alertas": 2,
    }

    result = handler._build_execution_health_summary(comparison_ui, average_ui, alerts)

    assert result["Saúde da execução"] == "Atenção"
    assert result["Nível de atenção"] == "Moderado"
    assert result["Tendência do sem_match"] == "Atenção"
    assert result["Tendência dos arquivos gerados"] == "Atenção"


def test_build_execution_health_summary_critica(handler):
    comparison_ui = {
        "Δ Linhas sem_match": "+5",
        "Δ Arquivos gerados": "-3",
    }
    average_ui = {
        "Δ vs média - sem_match": "+4.00",
        "Δ vs média - arquivos gerados": "-2.50",
    }
    alerts = {
        "quantidade_alertas": 4,
    }

    result = handler._build_execution_health_summary(comparison_ui, average_ui, alerts)

    assert result["Saúde da execução"] == "Crítica"
    assert result["Nível de atenção"] == "Alto"
    assert result["Tendência do sem_match"] == "Piora consistente"
    assert result["Tendência dos arquivos gerados"] == "Queda consistente"


def test_find_previous_history_row_returns_latest_before_current(handler):
    rows = [
        {"timestamp": "20260423_100000"},
        {"timestamp": "20260423_110000"},
        {"timestamp": "20260423_120000"},
    ]

    result = handler._find_previous_history_row(rows, "20260423_120000")

    assert result["timestamp"] == "20260423_110000"


def test_find_previous_n_history_rows_returns_last_n_before_current(handler):
    rows = [
        {"timestamp": "20260423_090000"},
        {"timestamp": "20260423_100000"},
        {"timestamp": "20260423_110000"},
        {"timestamp": "20260423_120000"},
    ]

    result = handler._find_previous_n_history_rows(rows, "20260423_120000", 2)

    assert [row["timestamp"] for row in result] == [
        "20260423_100000",
        "20260423_110000",
    ]


def test_count_selected_files_sums_all_sources(handler):
    selected_files = {
        "legalone": ["a.xlsx"],
        "webjur": ["b.csv", "c.csv"],
        "dw": [],
        "painel": ["d.xlsx"],
        "modo_legalone_intimacoes": [],
    }

    assert handler._count_selected_files(selected_files) == 4