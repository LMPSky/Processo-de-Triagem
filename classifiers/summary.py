from __future__ import annotations

from pathlib import Path
import pandas as pd
from .common import sanitize_sheet_name, rename_output_columns, truncate_text_column, word_frequency

def export_summary_excel(
    summary_path: Path,
    legalone_df: pd.DataFrame,
    legalone_pool: set[str],
    external_df: pd.DataFrame,
    duplicates_df: pd.DataFrame,
    sem_match_trab: pd.DataFrame,
    sem_match_civel: pd.DataFrame,
    com_match: pd.DataFrame,
    decio_df: pd.DataFrame,
    other_categorized: pd.DataFrame,
    no_category: pd.DataFrame,
) -> None:
    xlsx_path = summary_path.with_suffix(".xlsx")
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        overview = pd.DataFrame([
            {"Métrica": "Legal One — linhas", "Valor": len(legalone_df)},
            {"Métrica": "Legal One — identificadores no pool", "Valor": len(legalone_pool)},
            {"Métrica": "Bases externas — linhas totais (antes)", "Valor": len(external_df) + len(duplicates_df)},
            {"Métrica": "Bases externas — duplicatas removidas", "Valor": len(duplicates_df)},
            {"Métrica": "Bases externas — linhas após dedup", "Valor": len(external_df)},
            {"Métrica": "Trabalhista SEM MATCH", "Valor": len(sem_match_trab)},
            {"Métrica": "Cível SEM MATCH", "Valor": len(sem_match_civel)},
            {"Métrica": "COM MATCH (descartados)", "Valor": len(com_match)},
            {"Métrica": "Décio Freire (Prioridade Trabalhista)", "Valor": len(decio_df)},
            {"Métrica": "Outras categorias (Trab.)", "Valor": len(other_categorized)},
            {"Métrica": "Sem categoria (Trab.)", "Valor": len(no_category)},
        ])
        overview.to_excel(writer, sheet_name=sanitize_sheet_name("Visão Geral"), index=False)

        if len(sem_match_civel) > 0:
            civel_export = rename_output_columns(sem_match_civel.copy())
            cols = [c for c in [
                "cnj", "_texto", "_data", "_cliente", "Tribunal", "sistema",
                "macro_categoria_civel", "categoria_civel", "subcategoria_civel",
                "prioridade_civel", "confidence_civel", "motivo_civel",
                "cliente_match", "cliente_group", "excludente_match"
            ] if c in civel_export.columns]
            civel_export[cols].to_excel(writer, sheet_name=sanitize_sheet_name("Cíveis Brutos"), index=False)

            civ_cat = sem_match_civel["_categoria_civel"].fillna("SEM_CATEGORIA").value_counts().reset_index()
            civ_cat.columns = ["Categoria Cível", "Quantidade"]
            civ_cat.to_excel(writer, sheet_name=sanitize_sheet_name("Por Categoria (Cív.)"), index=False)

            if "_macro_categoria_civel" in sem_match_civel.columns:
                macro_cat = sem_match_civel["_macro_categoria_civel"].fillna("SEM_CATEGORIA").value_counts().reset_index()
                macro_cat.columns = ["Macro Categoria", "Quantidade"]
                macro_cat.to_excel(writer, sheet_name=sanitize_sheet_name("Por Macro Categoria"), index=False)

            df_ts = sem_match_civel.copy()
            if "_tribunal" not in df_ts.columns:
                df_ts["_tribunal"] = ""
            if "_sistema" not in df_ts.columns:
                df_ts["_sistema"] = ""

            df_ts["_tribunal"] = df_ts["_tribunal"].fillna("").astype(str)
            df_ts["_sistema"] = df_ts["_sistema"].fillna("").astype(str)

            ts_counts = (
                df_ts.groupby(["_tribunal", "_sistema"], dropna=False)
                .size()
                .reset_index(name="Quantidade")
                .sort_values(["Quantidade"], ascending=False)
            ).rename(columns={"_tribunal": "Tribunal", "_sistema": "sistema"})
            ts_counts.to_excel(writer, sheet_name=sanitize_sheet_name("Por Tribunal_Sistema"), index=False)

            t_counts = (
                df_ts.groupby(["_tribunal"], dropna=False)
                .size()
                .reset_index(name="Quantidade")
                .sort_values(["Quantidade"], ascending=False)
            ).rename(columns={"_tribunal": "Tribunal"})
            t_counts.to_excel(writer, sheet_name=sanitize_sheet_name("Por Tribunal"), index=False)

            s_counts = (
                df_ts.groupby(["_sistema"], dropna=False)
                .size()
                .reset_index(name="Quantidade")
                .sort_values(["Quantidade"], ascending=False)
            ).rename(columns={"_sistema": "sistema"})
            s_counts.to_excel(writer, sheet_name=sanitize_sheet_name("Por Sistema"), index=False)

            nao_classificados = sem_match_civel[sem_match_civel["_categoria_civel"].isna()].copy()
            if len(nao_classificados) > 0:
                nc_export = rename_output_columns(truncate_text_column(nao_classificados.copy()))
                cols_nc = [c for c in [
                    "cnj", "_texto", "_data", "_cliente", "Tribunal", "sistema",
                    "prioridade_civel", "confidence_civel", "motivo_civel"
                ] if c in nc_export.columns]
                nc_export[cols_nc].to_excel(writer, sheet_name=sanitize_sheet_name("Nao Classificados"), index=False)

                word_frequency(nao_classificados["_texto"], top_n=50).to_excel(
                    writer, sheet_name=sanitize_sheet_name("Palavras Frequentes"), index=False
                )

                ranking_cliente = (
                    nao_classificados["_cliente"].fillna("").astype(str)
                    .value_counts()
                    .head(50)
                    .reset_index()
                )
                ranking_cliente.columns = ["Cliente", "Quantidade"]
                ranking_cliente.to_excel(writer, sheet_name=sanitize_sheet_name("Ranking Clientes NC"), index=False)

                if "_tribunal" in nao_classificados.columns:
                    ranking_tribunal = (
                        nao_classificados["_tribunal"].fillna("").astype(str)
                        .value_counts()
                        .head(50)
                        .reset_index()
                    )
                    ranking_tribunal.columns = ["Tribunal", "Quantidade"]
                    ranking_tribunal.to_excel(writer, sheet_name=sanitize_sheet_name("Ranking Tribunal NC"), index=False)

                if "_sistema" in nao_classificados.columns:
                    ranking_sistema = (
                        nao_classificados["_sistema"].fillna("").astype(str)
                        .value_counts()
                        .head(50)
                        .reset_index()
                    )
                    ranking_sistema.columns = ["Sistema", "Quantidade"]
                    ranking_sistema.to_excel(writer, sheet_name=sanitize_sheet_name("Ranking Sistema NC"), index=False)