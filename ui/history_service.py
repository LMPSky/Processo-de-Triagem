"""
Serviço de histórico de execuções, comparativos e alertas.
"""
from __future__ import annotations


class ExecutionHistoryService:
    COMPARISON_FIELDS = [
        "arquivos_gerados",
        "novos_arquivos",
        "consolidados_gerados",
        "linhas_sem_match",
        "linhas_numero_puro",
        "linhas_outro",
    ]

    SEM_MATCH_DELTA_OBSERVATION_THRESHOLD = 20
    SEM_MATCH_AVG_OBSERVATION_THRESHOLD = 25
    FILES_DROP_OBSERVATION_THRESHOLD = 2
    CONSOLIDATED_DROP_OBSERVATION_THRESHOLD = 2

    def __init__(self, average_reference_window: int = 5):
        self.average_reference_window = average_reference_window

    def to_int_safe(self, value) -> int:
        try:
            if value is None or value == "":
                return 0
            return int(float(str(value)))
        except Exception:
            return 0

    def to_float_safe(self, value) -> float:
        try:
            if value is None or value == "":
                return 0.0
            return float(str(value))
        except Exception:
            return 0.0

    def find_previous_history_row(self, history_rows: list[dict], current_timestamp: str) -> dict | None:
        valid_rows = [
            row for row in history_rows
            if row.get("timestamp") and row.get("timestamp") != current_timestamp
        ]

        if not valid_rows:
            return None

        valid_rows.sort(key=lambda r: r.get("timestamp", ""))
        return valid_rows[-1]

    def find_previous_n_history_rows(self, history_rows: list[dict], current_timestamp: str, n: int) -> list[dict]:
        valid_rows = [
            row for row in history_rows
            if row.get("timestamp") and row.get("timestamp") != current_timestamp
        ]

        if not valid_rows:
            return []

        valid_rows.sort(key=lambda r: r.get("timestamp", ""))
        return valid_rows[-n:]

    def find_previous_n_success_history_rows(self, history_rows: list[dict], current_timestamp: str, n: int) -> list[dict]:
        valid_rows = [
            row for row in history_rows
            if row.get("timestamp")
            and row.get("timestamp") != current_timestamp
            and str(row.get("status", "")).strip().lower() == "sucesso"
        ]

        if not valid_rows:
            return []

        valid_rows.sort(key=lambda r: r.get("timestamp", ""))
        return valid_rows[-n:]

    def resolve_average_reference_rows(
        self,
        history_rows: list[dict],
        current_timestamp: str,
    ) -> tuple[list[dict], str]:
        success_rows = self.find_previous_n_success_history_rows(
            history_rows,
            current_timestamp,
            self.average_reference_window,
        )

        if success_rows:
            return success_rows, "ultimas_execucoes_com_sucesso"

        fallback_rows = self.find_previous_n_history_rows(
            history_rows,
            current_timestamp,
            self.average_reference_window,
        )

        if fallback_rows:
            return fallback_rows, "ultimas_execucoes_gerais"

        return [], ""

    def build_execution_comparison(self, current_row: dict, previous_row: dict | None) -> dict:
        comparison = {
            "execucao_atual": current_row.get("timestamp", ""),
            "execucao_anterior": previous_row.get("timestamp", "") if previous_row else "",
            "status_execucao_atual": current_row.get("status", ""),
            "status_execucao_anterior": previous_row.get("status", "") if previous_row else "",
            "comparacoes": {},
        }

        if not previous_row:
            comparison["mensagem"] = "Nenhuma execução anterior encontrada para comparação."
            return comparison

        for field in self.COMPARISON_FIELDS:
            atual = self.to_int_safe(current_row.get(field))
            anterior = self.to_int_safe(previous_row.get(field))
            delta = atual - anterior

            comparison["comparacoes"][field] = {
                "anterior": anterior,
                "atual": atual,
                "delta": delta,
            }

        return comparison

    def build_average_comparison(
        self,
        current_row: dict,
        reference_rows: list[dict],
        reference_criteria: str = "",
    ) -> dict:
        comparison = {
            "execucao_atual": current_row.get("timestamp", ""),
            "janela_referencia": self.average_reference_window,
            "quantidade_execucoes_referencia": len(reference_rows),
            "execucoes_referencia": [row.get("timestamp", "") for row in reference_rows],
            "criterio_referencia": reference_criteria,
            "comparacoes": {},
        }

        if not reference_rows:
            comparison["mensagem"] = "Não há execuções anteriores suficientes para calcular média de referência."
            return comparison

        for field in self.COMPARISON_FIELDS:
            valores = [self.to_int_safe(row.get(field)) for row in reference_rows]
            media = round(sum(valores) / len(valores), 2) if valores else 0
            atual = self.to_int_safe(current_row.get(field))
            delta_vs_media = round(atual - media, 2)

            comparison["comparacoes"][field] = {
                "media_referencia": media,
                "atual": atual,
                "delta_vs_media": delta_vs_media,
            }

        return comparison

    def build_comparison_ui_summary(self, comparison: dict) -> dict:
        if not comparison.get("execucao_anterior"):
            return {
                "Δ Arquivos gerados": "N/D",
                "Δ Consolidados gerados": "N/D",
                "Δ Linhas sem_match": "N/D",
            }

        comp = comparison.get("comparacoes", {}) or {}

        def _delta_text(field: str) -> str:
            delta = comp.get(field, {}).get("delta")
            if delta is None:
                return "N/D"
            if delta > 0:
                return f"+{delta}"
            return str(delta)

        return {
            "Δ Arquivos gerados": _delta_text("arquivos_gerados"),
            "Δ Consolidados gerados": _delta_text("consolidados_gerados"),
            "Δ Linhas sem_match": _delta_text("linhas_sem_match"),
        }

    def build_average_comparison_ui_summary(self, average_comparison: dict) -> dict:
        if average_comparison.get("quantidade_execucoes_referencia", 0) == 0:
            return {
                "Δ vs média - sem_match": "N/D",
                "Δ vs média - arquivos gerados": "N/D",
            }

        comp = average_comparison.get("comparacoes", {}) or {}

        def _delta_text(field: str) -> str:
            delta = comp.get(field, {}).get("delta_vs_media")
            if delta is None:
                return "N/D"

            delta_num = self.to_float_safe(delta)
            if delta_num > 0:
                return f"+{delta_num:.2f}"
            return f"{delta_num:.2f}"

        return {
            "Δ vs média - sem_match": _delta_text("linhas_sem_match"),
            "Δ vs média - arquivos gerados": _delta_text("arquivos_gerados"),
        }

    def build_regression_alerts(self, comparison: dict, average_comparison: dict) -> dict:
        alerts = []

        comp = comparison.get("comparacoes", {}) or {}
        avg_comp = average_comparison.get("comparacoes", {}) or {}

        has_previous = bool(comparison.get("execucao_anterior"))
        has_average_reference = average_comparison.get("quantidade_execucoes_referencia", 0) > 0

        if has_previous:
            delta_sem_match = self.to_int_safe(comp.get("linhas_sem_match", {}).get("delta"))
            delta_arquivos = self.to_int_safe(comp.get("arquivos_gerados", {}).get("delta"))
            delta_consolidados = self.to_int_safe(comp.get("consolidados_gerados", {}).get("delta"))

            if delta_sem_match >= self.SEM_MATCH_DELTA_OBSERVATION_THRESHOLD:
                alerts.append({
                    "tipo": "variacao_sem_match_vs_anterior",
                    "severidade": "acompanhar",
                    "mensagem": (
                        f"Variação relevante de sem_match (+{delta_sem_match}) em relação à execução anterior. "
                        f"Pode refletir mudança natural no volume ou no perfil das bases."
                    ),
                })

            if delta_arquivos <= -self.FILES_DROP_OBSERVATION_THRESHOLD:
                alerts.append({
                    "tipo": "variacao_arquivos_gerados_vs_anterior",
                    "severidade": "revisar",
                    "mensagem": (
                        f"Quantidade de arquivos gerados ficou {abs(delta_arquivos)} abaixo da execução anterior. "
                        f"Recomenda-se apenas conferir se a composição das entradas mudou."
                    ),
                })

            if delta_consolidados <= -self.CONSOLIDATED_DROP_OBSERVATION_THRESHOLD:
                alerts.append({
                    "tipo": "variacao_consolidados_gerados_vs_anterior",
                    "severidade": "acompanhar",
                    "mensagem": (
                        f"Quantidade de consolidados gerados ficou {abs(delta_consolidados)} abaixo da execução anterior."
                    ),
                })

        if has_average_reference:
            delta_sem_match_media = self.to_float_safe(avg_comp.get("linhas_sem_match", {}).get("delta_vs_media"))
            delta_arquivos_media = self.to_float_safe(avg_comp.get("arquivos_gerados", {}).get("delta_vs_media"))

            if delta_sem_match_media >= self.SEM_MATCH_AVG_OBSERVATION_THRESHOLD:
                alerts.append({
                    "tipo": "variacao_sem_match_vs_media",
                    "severidade": "acompanhar",
                    "mensagem": (
                        f"sem_match está {delta_sem_match_media:.2f} acima da média recente. "
                        f"Isso pode representar oscilação normal do insumo e merece apenas acompanhamento."
                    ),
                })

            if delta_arquivos_media <= -self.FILES_DROP_OBSERVATION_THRESHOLD:
                alerts.append({
                    "tipo": "variacao_arquivos_gerados_vs_media",
                    "severidade": "revisar",
                    "mensagem": (
                        f"Arquivos gerados estão {abs(delta_arquivos_media):.2f} abaixo da média recente. "
                        f"Recomenda-se validar se houve mudança no volume ou no tipo das bases recebidas."
                    ),
                })

        if not has_previous and not has_average_reference:
            texto_resumo = "Sem base histórica suficiente para comparação. Execução atual registrada apenas como referência."
        elif alerts:
            texto_resumo = "\n".join(
                f"• [{item['severidade'].upper()}] {item['mensagem']}" for item in alerts
            )
        else:
            texto_resumo = "Sem observações relevantes na comparação histórica."

        contagem_por_severidade = {
            "baixa": 0,
            "media": 0,
            "alta": 0,
            "informativa": len([a for a in alerts if a.get("severidade") == "informativa"]),
            "acompanhar": len([a for a in alerts if a.get("severidade") == "acompanhar"]),
            "revisar": len([a for a in alerts if a.get("severidade") == "revisar"]),
        }

        return {
            "quantidade_alertas": len(alerts),
            "alertas": alerts,
            "texto_resumo": texto_resumo,
            "considera_execucao_anterior": has_previous,
            "considera_media_recente": has_average_reference,
            "contagem_por_severidade": contagem_por_severidade,
        }

    def build_execution_health_summary(
        self,
        comparison_ui: dict,
        average_comparison_ui: dict,
        alerts: dict,
    ) -> dict:
        quantidade_alertas = self.to_int_safe(alerts.get("quantidade_alertas"))
        alertas_revisar = len([a for a in alerts.get("alertas", []) if a.get("severidade") == "revisar"])
        alertas_acompanhar = len([a for a in alerts.get("alertas", []) if a.get("severidade") == "acompanhar"])

        if quantidade_alertas == 0:
            status_execucao = "Execução OK"
            status_operacional = "Sem observações relevantes"
        elif alertas_revisar > 0:
            status_execucao = "Execução OK com revisão recomendada"
            status_operacional = "Revisão recomendada"
        elif alertas_acompanhar > 0:
            status_execucao = "Execução OK com observações"
            status_operacional = "Com variações operacionais"
        else:
            status_execucao = "Execução OK"
            status_operacional = "Com variações operacionais"

        delta_sem_match = comparison_ui.get("Δ Linhas sem_match", "N/D")
        delta_sem_match_media = average_comparison_ui.get("Δ vs média - sem_match", "N/D")

        delta_arquivos = comparison_ui.get("Δ Arquivos gerados", "N/D")
        delta_arquivos_media = average_comparison_ui.get("Δ vs média - arquivos gerados", "N/D")

        def _parse_num(value):
            if str(value).strip().upper() == "N/D":
                return None
            try:
                return float(str(value).replace("+", "").strip())
            except Exception:
                return None

        sem_match_last = _parse_num(delta_sem_match)
        sem_match_avg = _parse_num(delta_sem_match_media)

        arquivos_last = _parse_num(delta_arquivos)
        arquivos_avg = _parse_num(delta_arquivos_media)

        if sem_match_last is None and sem_match_avg is None:
            tendencia_sem_match = "Sem base comparativa"
        elif (sem_match_last is not None and sem_match_last > 0) and (sem_match_avg is not None and sem_match_avg > 0):
            tendencia_sem_match = "Oscilação acima do histórico"
        elif (sem_match_last is not None and sem_match_last <= 0) and (sem_match_avg is not None and sem_match_avg <= 0):
            tendencia_sem_match = "Dentro ou abaixo do histórico"
        else:
            tendencia_sem_match = "Oscilação pontual"

        if arquivos_last is None and arquivos_avg is None:
            tendencia_arquivos = "Sem base comparativa"
        elif (arquivos_last is not None and arquivos_last < 0) and (arquivos_avg is not None and arquivos_avg < 0):
            tendencia_arquivos = "Abaixo do histórico"
        elif (arquivos_last is not None and arquivos_last >= 0) and (arquivos_avg is not None and arquivos_avg >= 0):
            tendencia_arquivos = "Dentro ou acima do histórico"
        else:
            tendencia_arquivos = "Oscilação pontual"

        return {
            "Saúde da execução": status_execucao,
            "Tendência do sem_match": tendencia_sem_match,
            "Tendência dos arquivos gerados": tendencia_arquivos,
            "Nível de atenção": status_operacional,
        }