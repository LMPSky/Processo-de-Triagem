"""
Serviço específico para preparação e sanitização de arquivos WebJur.
"""
from __future__ import annotations

from pathlib import Path

from sanitizers.webjur_sanitizer import sanitize_webjur_file


class WebjurService:
    def remove_previous_derivatives(self, path: Path, safe_log=None, log_file=None):
        sanitized = path.with_name(f"{path.stem}_SANITIZADO.csv")
        ruins = path.with_name(f"{path.stem}_SANITIZADO_RUINS.csv")

        for derived in [sanitized, ruins]:
            try:
                if derived.exists():
                    derived.unlink()
                    if safe_log:
                        safe_log(f"[INPUT] Removendo derivado anterior: {derived.name}", "info", log_file)
            except Exception as e:
                if safe_log:
                    safe_log(f"[INPUT] ⚠️ Não foi possível remover {derived.name}: {e}", "warning", log_file)

    def sanitize_csv(self, path: Path, safe_log=None, log_file=None) -> bool:
        try:
            sanitized_path = path.with_name(f"{path.stem}_SANITIZADO.csv")
            ruins_path = path.with_name(f"{path.stem}_SANITIZADO_RUINS.csv")

            for old_file in [sanitized_path, ruins_path]:
                try:
                    if old_file.exists():
                        old_file.unlink()
                        if safe_log:
                            safe_log(f"[WEBJUR] Removendo derivado antigo: {old_file.name}", "info", log_file)
                except Exception as e:
                    if safe_log:
                        safe_log(f"[WEBJUR] ⚠️ Não foi possível remover {old_file.name}: {e}", "warning", log_file)

            if safe_log:
                safe_log(f"[WEBJUR] Sanitizando arquivo com sanitizador validado: {path.name}", "info", log_file)

            result = sanitize_webjur_file(path, sanitized_path)

            if safe_log:
                for item in result["metricas_colunas"]:
                    safe_log(
                        f"[WEBJUR] Coluna '{item['coluna']}': {item['datas_detectadas']} de {result['linhas_totais']} parecem ser data",
                        "info",
                        log_file,
                    )

                safe_log(
                    f"[WEBJUR] 🟢 Coluna real de data: posição {result['col_data_idx'] + 1} ('{result['col_data_nome']}')",
                    "success",
                    log_file,
                )

                safe_log(
                    f"[WEBJUR] Sanitizado: {result['linhas_validas']} linhas válidas | "
                    f"{result['linhas_ruins']} linhas removidas por data inválida",
                    "info",
                    log_file,
                )

                safe_log(f"[WEBJUR] ✓ Bruto preservado em: {path.name}", "info", log_file)
                safe_log(f"[WEBJUR] ✓ Sanitizado gerado em: {sanitized_path.name}", "success", log_file)
                safe_log("[WEBJUR] ✓ Pipeline deverá consumir o sanitizado, não o bruto.", "info", log_file)

                if result["ruins_path"]:
                    safe_log(
                        f"[WEBJUR] ⚠️ Linhas inválidas salvas em: {Path(result['ruins_path']).name}",
                        "warning",
                        log_file,
                    )

            return True

        except Exception as e:
            if safe_log:
                safe_log(f"[WEBJUR] ⚠️ Falha ao sanitizar {path.name}: {e}", "warning", log_file)
            return False