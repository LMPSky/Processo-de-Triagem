def test_regression_alerts_assign_expected_severities(handler):
    comparison = {
        "execucao_anterior": "20260424_120000",
        "comparacoes": {
            "linhas_sem_match": {"delta": 3},
            "arquivos_gerados": {"delta": -2},
            "consolidados_gerados": {"delta": -1},
        },
    }

    average_comparison = {
        "quantidade_execucoes_referencia": 4,
        "comparacoes": {
            "linhas_sem_match": {"delta_vs_media": 2.5},
            "arquivos_gerados": {"delta_vs_media": -1.75},
        },
    }

    result = handler._build_regression_alerts(comparison, average_comparison)

    severities_by_type = {
        item["tipo"]: item["severidade"]
        for item in result["alertas"]
    }

    assert severities_by_type["aumento_sem_match_vs_anterior"] == "media"
    assert severities_by_type["queda_arquivos_gerados_vs_anterior"] == "media"
    assert severities_by_type["queda_consolidados_gerados_vs_anterior"] == "baixa"
    assert severities_by_type["aumento_sem_match_vs_media"] == "alta"
    assert severities_by_type["queda_arquivos_gerados_vs_media"] == "alta"


def test_regression_alerts_count_by_severity(handler):
    comparison = {
        "execucao_anterior": "20260424_120000",
        "comparacoes": {
            "linhas_sem_match": {"delta": 5},
            "arquivos_gerados": {"delta": -1},
            "consolidados_gerados": {"delta": -1},
        },
    }

    average_comparison = {
        "quantidade_execucoes_referencia": 3,
        "comparacoes": {
            "linhas_sem_match": {"delta_vs_media": 4.0},
            "arquivos_gerados": {"delta_vs_media": -2.25},
        },
    }

    result = handler._build_regression_alerts(comparison, average_comparison)

    counts = result["contagem_por_severidade"]

    assert counts["alta"] == 2
    assert counts["media"] == 2
    assert counts["baixa"] == 1
    assert result["quantidade_alertas"] == 5


def test_regression_alerts_summary_text_includes_severity_prefix(handler):
    comparison = {
        "execucao_anterior": "20260424_120000",
        "comparacoes": {
            "linhas_sem_match": {"delta": 1},
            "arquivos_gerados": {"delta": 0},
            "consolidados_gerados": {"delta": -1},
        },
    }

    average_comparison = {
        "quantidade_execucoes_referencia": 2,
        "comparacoes": {
            "linhas_sem_match": {"delta_vs_media": 1.25},
            "arquivos_gerados": {"delta_vs_media": 0},
        },
    }

    result = handler._build_regression_alerts(comparison, average_comparison)

    summary_text = result["texto_resumo"]

    assert "[MEDIA]" in summary_text
    assert "[BAIXA]" in summary_text
    assert "[ALTA]" in summary_text


def test_regression_alerts_without_alerts_has_zero_counts(handler):
    comparison = {
        "execucao_anterior": "20260424_120000",
        "comparacoes": {
            "linhas_sem_match": {"delta": -1},
            "arquivos_gerados": {"delta": 2},
            "consolidados_gerados": {"delta": 0},
        },
    }

    average_comparison = {
        "quantidade_execucoes_referencia": 3,
        "comparacoes": {
            "linhas_sem_match": {"delta_vs_media": -0.5},
            "arquivos_gerados": {"delta_vs_media": 1.5},
        },
    }

    result = handler._build_regression_alerts(comparison, average_comparison)

    counts = result["contagem_por_severidade"]

    assert result["quantidade_alertas"] == 0
    assert counts["alta"] == 0
    assert counts["media"] == 0
    assert counts["baixa"] == 0
    assert result["texto_resumo"] == "Nenhum alerta"