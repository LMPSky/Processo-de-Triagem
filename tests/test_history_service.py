from ui.history_service import ExecutionHistoryService


def test_to_int_safe_handles_valid_and_invalid_values():
    service = ExecutionHistoryService()

    assert service.to_int_safe(10) == 10
    assert service.to_int_safe("12") == 12
    assert service.to_int_safe("12.0") == 12
    assert service.to_int_safe("") == 0
    assert service.to_int_safe(None) == 0
    assert service.to_int_safe("abc") == 0


def test_to_float_safe_handles_valid_and_invalid_values():
    service = ExecutionHistoryService()

    assert service.to_float_safe(10) == 10.0
    assert service.to_float_safe("12.5") == 12.5
    assert service.to_float_safe("") == 0.0
    assert service.to_float_safe(None) == 0.0
    assert service.to_float_safe("abc") == 0.0


def test_find_previous_history_row_returns_latest_previous():
    service = ExecutionHistoryService()

    rows = [
        {"timestamp": "20260424_100000", "status": "sucesso"},
        {"timestamp": "20260424_110000", "status": "erro"},
        {"timestamp": "20260424_120000", "status": "sucesso"},
    ]

    result = service.find_previous_history_row(rows, "20260424_120000")

    assert result is not None
    assert result["timestamp"] == "20260424_110000"


def test_find_previous_history_row_returns_none_when_no_previous():
    service = ExecutionHistoryService()

    rows = [
        {"timestamp": "20260424_120000", "status": "sucesso"},
    ]

    result = service.find_previous_history_row(rows, "20260424_120000")

    assert result is None


def test_find_previous_n_history_rows_returns_last_n():
    service = ExecutionHistoryService()

    rows = [
        {"timestamp": "20260424_100000"},
        {"timestamp": "20260424_110000"},
        {"timestamp": "20260424_120000"},
        {"timestamp": "20260424_130000"},
    ]

    result = service.find_previous_n_history_rows(rows, "20260424_130000", 2)

    assert len(result) == 2
    assert result[0]["timestamp"] == "20260424_110000"
    assert result[1]["timestamp"] == "20260424_120000"


def test_find_previous_n_success_history_rows_filters_success_only():
    service = ExecutionHistoryService()

    rows = [
        {"timestamp": "20260424_100000", "status": "erro"},
        {"timestamp": "20260424_110000", "status": "sucesso"},
        {"timestamp": "20260424_120000", "status": "sucesso"},
        {"timestamp": "20260424_130000", "status": "erro"},
    ]

    result = service.find_previous_n_success_history_rows(rows, "20260424_130000", 5)

    assert len(result) == 2
    assert result[0]["timestamp"] == "20260424_110000"
    assert result[1]["timestamp"] == "20260424_120000"


def test_resolve_average_reference_rows_prefers_success_rows():
    service = ExecutionHistoryService(average_reference_window=3)

    rows = [
        {"timestamp": "20260424_100000", "status": "erro"},
        {"timestamp": "20260424_110000", "status": "sucesso"},
        {"timestamp": "20260424_120000", "status": "sucesso"},
        {"timestamp": "20260424_130000", "status": "erro"},
    ]

    result_rows, criteria = service.resolve_average_reference_rows(rows, "20260424_130000")

    assert len(result_rows) == 2
    assert criteria == "ultimas_execucoes_com_sucesso"


def test_resolve_average_reference_rows_falls_back_to_general_rows():
    service = ExecutionHistoryService(average_reference_window=3)

    rows = [
        {"timestamp": "20260424_100000", "status": "erro"},
        {"timestamp": "20260424_110000", "status": "erro"},
        {"timestamp": "20260424_120000", "status": "erro"},
    ]

    result_rows, criteria = service.resolve_average_reference_rows(rows, "20260424_120000")

    assert len(result_rows) == 2
    assert criteria == "ultimas_execucoes_gerais"


def test_build_execution_comparison_returns_deltas():
    service = ExecutionHistoryService()

    current_row = {
        "timestamp": "20260424_130000",
        "status": "sucesso",
        "arquivos_gerados": 10,
        "novos_arquivos": 3,
        "consolidados_gerados": 2,
        "linhas_sem_match": 5,
        "linhas_numero_puro": 1,
        "linhas_outro": 0,
    }

    previous_row = {
        "timestamp": "20260424_120000",
        "status": "sucesso",
        "arquivos_gerados": 8,
        "novos_arquivos": 2,
        "consolidados_gerados": 2,
        "linhas_sem_match": 7,
        "linhas_numero_puro": 1,
        "linhas_outro": 1,
    }

    result = service.build_execution_comparison(current_row, previous_row)

    assert result["execucao_atual"] == "20260424_130000"
    assert result["execucao_anterior"] == "20260424_120000"
    assert result["comparacoes"]["arquivos_gerados"]["delta"] == 2
    assert result["comparacoes"]["linhas_sem_match"]["delta"] == -2
    assert result["comparacoes"]["linhas_outro"]["delta"] == -1


def test_build_execution_comparison_without_previous_returns_message():
    service = ExecutionHistoryService()

    current_row = {
        "timestamp": "20260424_130000",
        "status": "sucesso",
    }

    result = service.build_execution_comparison(current_row, None)

    assert result["execucao_anterior"] == ""
    assert "mensagem" in result


def test_build_average_comparison_returns_mean_and_delta():
    service = ExecutionHistoryService(average_reference_window=5)

    current_row = {
        "timestamp": "20260424_130000",
        "arquivos_gerados": 10,
        "novos_arquivos": 3,
        "consolidados_gerados": 2,
        "linhas_sem_match": 6,
        "linhas_numero_puro": 2,
        "linhas_outro": 1,
    }

    reference_rows = [
        {
            "timestamp": "20260424_100000",
            "arquivos_gerados": 8,
            "novos_arquivos": 2,
            "consolidados_gerados": 2,
            "linhas_sem_match": 4,
            "linhas_numero_puro": 1,
            "linhas_outro": 0,
        },
        {
            "timestamp": "20260424_110000",
            "arquivos_gerados": 12,
            "novos_arquivos": 4,
            "consolidados_gerados": 2,
            "linhas_sem_match": 8,
            "linhas_numero_puro": 3,
            "linhas_outro": 2,
        },
    ]

    result = service.build_average_comparison(
        current_row=current_row,
        reference_rows=reference_rows,
        reference_criteria="ultimas_execucoes_com_sucesso",
    )

    assert result["quantidade_execucoes_referencia"] == 2
    assert result["criterio_referencia"] == "ultimas_execucoes_com_sucesso"
    assert result["comparacoes"]["arquivos_gerados"]["media_referencia"] == 10
    assert result["comparacoes"]["arquivos_gerados"]["delta_vs_media"] == 0
    assert result["comparacoes"]["linhas_sem_match"]["media_referencia"] == 6
    assert result["comparacoes"]["linhas_sem_match"]["delta_vs_media"] == 0


def test_build_average_comparison_without_reference_returns_message():
    service = ExecutionHistoryService()

    current_row = {"timestamp": "20260424_130000"}

    result = service.build_average_comparison(current_row, [], "")

    assert result["quantidade_execucoes_referencia"] == 0
    assert "mensagem" in result


def test_build_comparison_ui_summary_formats_deltas():
    service = ExecutionHistoryService()

    comparison = {
        "execucao_anterior": "20260424_120000",
        "comparacoes": {
            "arquivos_gerados": {"delta": 2},
            "consolidados_gerados": {"delta": 0},
            "linhas_sem_match": {"delta": -3},
        },
    }

    result = service.build_comparison_ui_summary(comparison)

    assert result["Δ Arquivos gerados"] == "+2"
    assert result["Δ Consolidados gerados"] == "0"
    assert result["Δ Linhas sem_match"] == "-3"


def test_build_comparison_ui_summary_without_previous_returns_nd():
    service = ExecutionHistoryService()

    comparison = {
        "execucao_anterior": "",
        "comparacoes": {},
    }

    result = service.build_comparison_ui_summary(comparison)

    assert result["Δ Arquivos gerados"] == "N/D"
    assert result["Δ Consolidados gerados"] == "N/D"
    assert result["Δ Linhas sem_match"] == "N/D"


def test_build_average_comparison_ui_summary_formats_values():
    service = ExecutionHistoryService()

    average_comparison = {
        "quantidade_execucoes_referencia": 2,
        "comparacoes": {
            "linhas_sem_match": {"delta_vs_media": 1.5},
            "arquivos_gerados": {"delta_vs_media": -2},
        },
    }

    result = service.build_average_comparison_ui_summary(average_comparison)

    assert result["Δ vs média - sem_match"] == "+1.50"
    assert result["Δ vs média - arquivos gerados"] == "-2.00"


def test_build_average_comparison_ui_summary_without_reference_returns_nd():
    service = ExecutionHistoryService()

    average_comparison = {
        "quantidade_execucoes_referencia": 0,
        "comparacoes": {},
    }

    result = service.build_average_comparison_ui_summary(average_comparison)

    assert result["Δ vs média - sem_match"] == "N/D"
    assert result["Δ vs média - arquivos gerados"] == "N/D"


def test_build_regression_alerts_creates_expected_alerts():
    service = ExecutionHistoryService()

    comparison = {
        "execucao_anterior": "20260424_120000",
        "comparacoes": {
            "linhas_sem_match": {"delta": 4},
            "arquivos_gerados": {"delta": -2},
            "consolidados_gerados": {"delta": -1},
        },
    }

    average_comparison = {
        "quantidade_execucoes_referencia": 3,
        "comparacoes": {
            "linhas_sem_match": {"delta_vs_media": 2.5},
            "arquivos_gerados": {"delta_vs_media": -1.75},
        },
    }

    result = service.build_regression_alerts(comparison, average_comparison)

    assert result["quantidade_alertas"] == 5
    assert result["contagem_por_severidade"]["alta"] == 2
    assert result["contagem_por_severidade"]["media"] == 2
    assert result["contagem_por_severidade"]["baixa"] == 1
    assert "[ALTA]" in result["texto_resumo"]
    assert "[MEDIA]" in result["texto_resumo"]
    assert "[BAIXA]" in result["texto_resumo"]


def test_build_regression_alerts_without_history_reference():
    service = ExecutionHistoryService()

    comparison = {
        "execucao_anterior": "",
        "comparacoes": {},
    }

    average_comparison = {
        "quantidade_execucoes_referencia": 0,
        "comparacoes": {},
    }

    result = service.build_regression_alerts(comparison, average_comparison)

    assert result["quantidade_alertas"] == 0
    assert result["texto_resumo"] == "Nenhum alerta (sem base histórica suficiente para comparação)."


def test_build_regression_alerts_without_triggered_alerts():
    service = ExecutionHistoryService()

    comparison = {
        "execucao_anterior": "20260424_120000",
        "comparacoes": {
            "linhas_sem_match": {"delta": -1},
            "arquivos_gerados": {"delta": 2},
            "consolidados_gerados": {"delta": 0},
        },
    }

    average_comparison = {
        "quantidade_execucoes_referencia": 2,
        "comparacoes": {
            "linhas_sem_match": {"delta_vs_media": -0.5},
            "arquivos_gerados": {"delta_vs_media": 1.0},
        },
    }

    result = service.build_regression_alerts(comparison, average_comparison)

    assert result["quantidade_alertas"] == 0
    assert result["texto_resumo"] == "Nenhum alerta"


def test_build_execution_health_summary_when_no_alerts():
    service = ExecutionHistoryService()

    comparison_ui = {
        "Δ Linhas sem_match": "-1",
        "Δ Arquivos gerados": "+2",
    }

    average_comparison_ui = {
        "Δ vs média - sem_match": "-0.50",
        "Δ vs média - arquivos gerados": "+1.50",
    }

    alerts = {
        "quantidade_alertas": 0,
    }

    result = service.build_execution_health_summary(
        comparison_ui=comparison_ui,
        average_comparison_ui=average_comparison_ui,
        alerts=alerts,
    )

    assert result["Saúde da execução"] == "Saudável"
    assert result["Nível de atenção"] == "Baixo"
    assert result["Tendência do sem_match"] == "Estável/Melhorando"
    assert result["Tendência dos arquivos gerados"] == "Estável/Melhorando"


def test_build_execution_health_summary_when_few_alerts():
    service = ExecutionHistoryService()

    comparison_ui = {
        "Δ Linhas sem_match": "+1",
        "Δ Arquivos gerados": "-1",
    }

    average_comparison_ui = {
        "Δ vs média - sem_match": "-0.50",
        "Δ vs média - arquivos gerados": "+0.25",
    }

    alerts = {
        "quantidade_alertas": 2,
    }

    result = service.build_execution_health_summary(
        comparison_ui=comparison_ui,
        average_comparison_ui=average_comparison_ui,
        alerts=alerts,
    )

    assert result["Saúde da execução"] == "Atenção"
    assert result["Nível de atenção"] == "Moderado"


def test_build_execution_health_summary_when_many_alerts():
    service = ExecutionHistoryService()

    comparison_ui = {
        "Δ Linhas sem_match": "+4",
        "Δ Arquivos gerados": "-3",
    }

    average_comparison_ui = {
        "Δ vs média - sem_match": "+2.50",
        "Δ vs média - arquivos gerados": "-1.25",
    }

    alerts = {
        "quantidade_alertas": 5,
    }

    result = service.build_execution_health_summary(
        comparison_ui=comparison_ui,
        average_comparison_ui=average_comparison_ui,
        alerts=alerts,
    )

    assert result["Saúde da execução"] == "Crítica"
    assert result["Nível de atenção"] == "Alto"
    assert result["Tendência do sem_match"] == "Piora consistente"
    assert result["Tendência dos arquivos gerados"] == "Queda consistente"


def test_build_execution_health_summary_without_comparative_base():
    service = ExecutionHistoryService()

    comparison_ui = {
        "Δ Linhas sem_match": "N/D",
        "Δ Arquivos gerados": "N/D",
    }

    average_comparison_ui = {
        "Δ vs média - sem_match": "N/D",
        "Δ vs média - arquivos gerados": "N/D",
    }

    alerts = {
        "quantidade_alertas": 0,
    }

    result = service.build_execution_health_summary(
        comparison_ui=comparison_ui,
        average_comparison_ui=average_comparison_ui,
        alerts=alerts,
    )

    assert result["Tendência do sem_match"] == "Sem base comparativa"
    assert result["Tendência dos arquivos gerados"] == "Sem base comparativa"