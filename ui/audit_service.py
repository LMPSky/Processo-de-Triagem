"""
Serviço de auditoria, escrita de artefatos e consolidação de saídas.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import pandas as pd


class AuditService:
    def __init__(
        self,
        output_keywords: list[str] | None = None,
        consolidated_audit_groups: list[str] | None = None,
        average_reference_window: int = 5,
    ):
        self.output_keywords = output_keywords or [
            "sem_match",
            "numero_puro",
            "outro",
            "civel",
            "trabalhista",
            "match",
        ]
        self.consolidated_audit_groups = consolidated_audit_groups or [
            "sem_match",
            "numero_puro",
            "outro",
        ]
        self.average_reference_window = average_reference_window

    def safe_write_json(self, path: Path, data: dict | list):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def safe_write_csv(self, path: Path, rows: list[dict], fieldnames: list[str]):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def build_output_index(self, output_dir: Path, output_files: list[Path]) -> list[dict]:
        rows = []

        for file_path in sorted(output_files):
            try:
                stat = file_path.stat()
                relative = file_path.relative_to(output_dir)
                parts = relative.parts
                top_folder = parts[0] if len(parts) > 1 else "(raiz)"

                rows.append({
                    "arquivo": file_path.name,
                    "caminho_absoluto": str(file_path),
                    "caminho_relativo": str(relative),
                    "pasta_topo": top_folder,
                    "tamanho_bytes": stat.st_size,
                    "modificado_em": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                })
            except Exception:
                rows.append({
                    "arquivo": file_path.name,
                    "caminho_absoluto": str(file_path),
                    "caminho_relativo": str(file_path),
                    "pasta_topo": "(desconhecida)",
                    "tamanho_bytes": "",
                    "modificado_em": "",
                })

        return rows

    def build_output_summary(self, index_rows: list[dict], new_files: list[Path], output_dir: Path) -> dict:
        by_top_folder: dict[str, int] = {}
        by_keyword: dict[str, int] = {keyword: 0 for keyword in self.output_keywords}

        for row in index_rows:
            top_folder = row["pasta_topo"]
            by_top_folder[top_folder] = by_top_folder.get(top_folder, 0) + 1

            filename_lower = str(row["arquivo"]).lower()
            relative_lower = str(row["caminho_relativo"]).lower()
            haystack = f"{filename_lower} {relative_lower}"

            for keyword in self.output_keywords:
                if keyword in haystack:
                    by_keyword[keyword] += 1

        new_files_relative = []
        for p in new_files:
            try:
                new_files_relative.append(str(p.relative_to(output_dir)))
            except Exception:
                new_files_relative.append(str(p))

        return {
            "total_xlsx_output": len(index_rows),
            "total_novos_xlsx": len(new_files),
            "contagem_por_pasta_topo": by_top_folder,
            "contagem_por_palavra_chave": by_keyword,
            "novos_arquivos_relativos": new_files_relative,
        }

    def write_output_audit_files(
        self,
        audit_dir: Path,
        output_dir: Path,
        output_files: list[Path],
        new_files: list[Path],
    ):
        index_rows = self.build_output_index(output_dir, output_files)
        output_summary = self.build_output_summary(index_rows, new_files, output_dir)

        self.safe_write_json(audit_dir / "auditoria_arquivos_gerados.json", index_rows)
        self.safe_write_json(audit_dir / "auditoria_resumo_output.json", output_summary)
        self.safe_write_csv(
            audit_dir / "auditoria_xlsx_index.csv",
            index_rows,
            fieldnames=[
                "arquivo",
                "caminho_absoluto",
                "caminho_relativo",
                "pasta_topo",
                "tamanho_bytes",
                "modificado_em",
            ],
        )

    def group_output_files_by_keyword(self, output_dir: Path, output_files: list[Path]) -> dict[str, list[Path]]:
        grouped: dict[str, list[Path]] = {key: [] for key in self.consolidated_audit_groups}

        for file_path in output_files:
            try:
                relative = file_path.relative_to(output_dir)
                haystack = f"{file_path.name.lower()} {str(relative).lower()}"
            except Exception:
                haystack = file_path.name.lower()

            for keyword in self.consolidated_audit_groups:
                if keyword in haystack:
                    grouped[keyword].append(file_path)

        return grouped

    def build_consolidated_audit_excel(
        self,
        audit_dir: Path,
        output_dir: Path,
        group_name: str,
        files: list[Path],
        safe_log=None,
        log_file=None,
    ) -> dict:
        metadata = {
            "grupo": group_name,
            "arquivos_origem": 0,
            "linhas_consolidadas": 0,
            "arquivos": [],
            "colunas": [],
            "linhas_por_arquivo": {},
            "arquivo_saida": "",
        }

        if not files:
            if safe_log:
                safe_log(f"[AUDITORIA] Grupo '{group_name}' sem arquivos para consolidar.", "info", log_file)
            return metadata

        frames: list[pd.DataFrame] = []

        for file_path in files:
            try:
                df = pd.read_excel(file_path, dtype=str, engine="openpyxl")
                df = df.fillna("")

                try:
                    relative_path = file_path.relative_to(output_dir)
                except Exception:
                    relative_path = file_path

                df["_arquivo_origem"] = file_path.name
                df["_caminho_relativo_origem"] = str(relative_path)
                df["_grupo_auditoria"] = group_name

                frames.append(df)
                metadata["arquivos"].append(file_path.name)
                metadata["linhas_por_arquivo"][file_path.name] = len(df)

                if safe_log:
                    safe_log(
                        f"[AUDITORIA] Lido para consolidado '{group_name}': {file_path.name} ({len(df)} linhas)",
                        "info",
                        log_file,
                    )

            except Exception as e:
                if safe_log:
                    safe_log(
                        f"[AUDITORIA] ⚠️ Falha ao ler '{file_path.name}' para o grupo '{group_name}': {e}",
                        "warning",
                        log_file,
                    )

        if not frames:
            if safe_log:
                safe_log(
                    f"[AUDITORIA] Nenhum dataframe válido foi obtido para o grupo '{group_name}'.",
                    "warning",
                    log_file,
                )
            return metadata

        try:
            consolidated = pd.concat(frames, ignore_index=True, sort=False)
            output_path = audit_dir / f"auditoria_consolidado_{group_name}.xlsx"
            consolidated.to_excel(output_path, index=False, engine="openpyxl")

            metadata["arquivos_origem"] = len(metadata["arquivos"])
            metadata["linhas_consolidadas"] = len(consolidated)
            metadata["colunas"] = list(consolidated.columns)
            metadata["arquivo_saida"] = str(output_path)

            if safe_log:
                safe_log(
                    f"[AUDITORIA] ✓ Consolidado '{group_name}' gerado: {output_path.name} ({len(consolidated)} linhas)",
                    "success",
                    log_file,
                )
        except Exception as e:
            if safe_log:
                safe_log(
                    f"[AUDITORIA] ❌ Erro ao salvar consolidado '{group_name}': {e}",
                    "error",
                    log_file,
                )

        return metadata

    def write_consolidated_summary_excel(self, audit_dir: Path, summary: dict, safe_log=None, log_file=None):
        try:
            resumo_rows = []
            arquivos_rows = []
            colunas_rows = []

            for group_name, meta in summary.items():
                resumo_rows.append({
                    "grupo": group_name,
                    "arquivos_origem": meta.get("arquivos_origem", 0),
                    "linhas_consolidadas": meta.get("linhas_consolidadas", 0),
                    "arquivo_saida": meta.get("arquivo_saida", ""),
                })

                for arquivo, linhas in (meta.get("linhas_por_arquivo", {}) or {}).items():
                    arquivos_rows.append({
                        "grupo": group_name,
                        "arquivo_origem": arquivo,
                        "linhas": linhas,
                    })

                for coluna in (meta.get("colunas", []) or []):
                    colunas_rows.append({
                        "grupo": group_name,
                        "coluna": coluna,
                    })

            resumo_df = pd.DataFrame(resumo_rows)
            arquivos_df = pd.DataFrame(arquivos_rows)
            colunas_df = pd.DataFrame(colunas_rows)

            output_path = audit_dir / "auditoria_resumo_consolidados.xlsx"

            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                resumo_df.to_excel(writer, sheet_name="resumo", index=False)
                arquivos_df.to_excel(writer, sheet_name="arquivos_origem", index=False)
                colunas_df.to_excel(writer, sheet_name="colunas", index=False)

            if safe_log:
                safe_log(
                    f"[AUDITORIA] ✓ Resumo Excel dos consolidados gerado: {output_path.name}",
                    "success",
                    log_file,
                )
        except Exception as e:
            if safe_log:
                safe_log(
                    f"[AUDITORIA] ❌ Erro ao gerar auditoria_resumo_consolidados.xlsx: {e}",
                    "error",
                    log_file,
                )

    def write_consolidated_output_audits(
        self,
        audit_dir: Path,
        output_dir: Path,
        output_files: list[Path],
        safe_log=None,
        log_file=None,
    ) -> dict:
        grouped = self.group_output_files_by_keyword(output_dir, output_files)
        summary = {}

        for group_name, files in grouped.items():
            metadata = self.build_consolidated_audit_excel(
                audit_dir=audit_dir,
                output_dir=output_dir,
                group_name=group_name,
                files=files,
                safe_log=safe_log,
                log_file=log_file,
            )
            summary[group_name] = metadata

        self.safe_write_json(audit_dir / "auditoria_resumo_consolidados.json", summary)
        self.write_consolidated_summary_excel(audit_dir, summary, safe_log=safe_log, log_file=log_file)
        return summary

    def build_consolidated_ui_summary(self, consolidated_summary: dict) -> dict:
        generated_count = 0
        result = {
            "Consolidados gerados": 0,
            "Linhas consolidadas - sem_match": 0,
            "Linhas consolidadas - numero_puro": 0,
            "Linhas consolidadas - outro": 0,
        }

        for group_name in self.consolidated_audit_groups:
            meta = consolidated_summary.get(group_name, {}) or {}
            linhas = int(meta.get("linhas_consolidadas", 0) or 0)
            arquivo_saida = meta.get("arquivo_saida", "")

            if arquivo_saida:
                generated_count += 1

            result[f"Linhas consolidadas - {group_name}"] = linhas

        result["Consolidados gerados"] = generated_count
        return result

    def write_execution_comparison(self, audit_dir: Path, comparison: dict):
        output_path = audit_dir / "comparativo_execucao_anterior.json"
        self.safe_write_json(output_path, comparison)
        return output_path

    def write_average_comparison(self, audit_dir: Path, comparison: dict):
        output_path = audit_dir / "comparativo_media_ultimas_execucoes.json"
        self.safe_write_json(output_path, comparison)
        return output_path

    def write_regression_alerts(self, audit_dir: Path, alerts: dict):
        output_path = audit_dir / "alertas_execucao.json"
        self.safe_write_json(output_path, alerts)
        return output_path

    def write_execution_markdown_summary(self, audit_dir: Path, result_summary: dict):
        output_path = audit_dir / "resumo_execucao.md"

        lines = [
            "# Resumo da Execução",
            "",
            "## Identificação",
            f"- **Status:** {result_summary.get('Status', '-')}",
            f"- **Modo diagnóstico:** {result_summary.get('Modo diagnóstico', '-')}",
            "",
            "## Visão executiva",
            f"- **Saúde da execução:** {result_summary.get('Saúde da execução', '-')}",
            f"- **Nível de atenção:** {result_summary.get('Nível de atenção', '-')}",
            f"- **Quantidade de alertas:** {result_summary.get('Quantidade de alertas', '-')}",
            f"- **Alertas alta severidade:** {result_summary.get('Alertas alta severidade', '-')}",
            f"- **Alertas média severidade:** {result_summary.get('Alertas média severidade', '-')}",
            f"- **Alertas baixa severidade:** {result_summary.get('Alertas baixa severidade', '-')}",
            f"- **Critério da média recente:** {result_summary.get('Critério da média recente', '-')}",
            "",
            "## Comparativos",
            f"- **Δ Arquivos gerados:** {result_summary.get('Δ Arquivos gerados', '-')}",
            f"- **Δ Consolidados gerados:** {result_summary.get('Δ Consolidados gerados', '-')}",
            f"- **Δ Linhas sem_match:** {result_summary.get('Δ Linhas sem_match', '-')}",
            f"- **Δ vs média - sem_match:** {result_summary.get('Δ vs média - sem_match', '-')}",
            f"- **Δ vs média - arquivos gerados:** {result_summary.get('Δ vs média - arquivos gerados', '-')}",
            "",
            "## Volumetria",
            f"- **Fontes com arquivos preparados:** {result_summary.get('Fontes com arquivos preparados', '-')}",
            f"- **Arquivos selecionados:** {result_summary.get('Arquivos selecionados', '-')}",
            f"- **Arquivos preparados:** {result_summary.get('Arquivos preparados', '-')}",
            f"- **Arquivos gerados:** {result_summary.get('Arquivos gerados', '-')}",
            f"- **Novos arquivos:** {result_summary.get('Novos arquivos', '-')}",
            f"- **Consolidados gerados:** {result_summary.get('Consolidados gerados', '-')}",
            "",
            "## Fontes",
            f"- **Fontes informadas:** {result_summary.get('Fontes informadas', '-')}",
            f"- **Fontes ausentes:** {result_summary.get('Fontes ausentes', '-')}",
            "",
            "### Resumo por fonte",
            "",
            str(result_summary.get("Resumo por fonte", "-")),
            "",
            "## Consolidados",
            f"- **Linhas consolidadas - sem_match:** {result_summary.get('Linhas consolidadas - sem_match', '-')}",
            f"- **Linhas consolidadas - numero_puro:** {result_summary.get('Linhas consolidadas - numero_puro', '-')}",
            f"- **Linhas consolidadas - outro:** {result_summary.get('Linhas consolidadas - outro', '-')}",
            "",
            "## Alertas",
            "",
            str(result_summary.get("Alertas de regressão", "Nenhum alerta")),
            "",
            "## Caminhos",
            f"- **Localização:** {result_summary.get('Localização', '-')}",
            f"- **Pasta da auditoria:** {result_summary.get('Pasta da auditoria', '-')}",
            f"- **Log da execução:** {result_summary.get('Log da execução', '-')}",
            "",
        ]

        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path