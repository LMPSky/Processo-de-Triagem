from __future__ import annotations

import csv
import sys
import re
from pathlib import Path

import pandas as pd


EXPECTED_HEADER = [
    "Codigo",
    "Número do Processo",
    "Data da Publicação",
    "Termo Localizado",
    "Diário Oficial",
    "Página",
    "Juizo",
    "Publicação",
    "targetID",
]

csv.field_size_limit(sys.maxsize)


def looks_like_date(val) -> bool:
    v = str(val).strip()
    if not v or v.lower() in ("nan", "none", "-", " "):
        return False

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return True
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", v):
        return True
    if re.fullmatch(r"\d{8}", v):
        return True

    try:
        d = pd.to_datetime(v, errors="coerce", dayfirst=True)
        return pd.notnull(d)
    except Exception:
        return False


def sanitize_webjur_file(input_path: str | Path, output_path: str | Path) -> dict:
    """
    Sanitiza um CSV do WebJur usando a lógica validada:
    - detecta a coluna real de data
    - move essa coluna para 'Data da Publicação'
    - remove linhas com data inválida
    - salva o CSV sanitizado
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    with open(input_path, encoding="latin-1", errors="replace", newline="") as f:
        reader = csv.reader(f, delimiter=";")
        linhas = [linha for linha in reader if any(str(c).strip() for c in linha)]

    if len(linhas) < 2:
        raise ValueError("Arquivo vazio ou só cabeçalho.")

    header = linhas[0]
    dados = linhas[1:]

    num_cols = len(EXPECTED_HEADER)
    col_data_idx = -1
    max_datas = 0
    metricas_colunas = []

    for idx in range(num_cols):
        n_datas = sum(looks_like_date(linha[idx]) for linha in dados if len(linha) > idx)
        col_name = header[idx] if idx < len(header) else str(idx)

        metricas_colunas.append(
            {
                "indice": idx,
                "coluna": col_name,
                "datas_detectadas": n_datas,
            }
        )

        if n_datas > max_datas:
            max_datas = n_datas
            col_data_idx = idx

    if col_data_idx == -1:
        raise ValueError("Não foi possível detectar a coluna real de data.")

    dados_realign = []
    for linha in dados:
        nova = [""] * num_cols

        for i in range(num_cols):
            if i < len(linha):
                nova[i] = linha[i]

        if col_data_idx != 2 and len(linha) > col_data_idx:
            nova[2] = linha[col_data_idx]

        dados_realign.append(nova)

    df = pd.DataFrame(dados_realign, columns=EXPECTED_HEADER)

    mask_validas = df["Data da Publicação"].apply(looks_like_date)
    ruins = df[~mask_validas].copy()
    final = df[mask_validas].reset_index(drop=True)

    final.to_csv(output_path, sep=";", index=False, encoding="latin-1")

    ruins_path = None
    if not ruins.empty:
        ruins_path = output_path.with_name(output_path.stem + "_RUINS.csv")
        ruins.to_csv(ruins_path, sep=";", index=False, encoding="latin-1")

    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "ruins_path": str(ruins_path) if ruins_path else None,
        "header_original": header,
        "col_data_idx": col_data_idx,
        "col_data_nome": header[col_data_idx] if col_data_idx < len(header) else str(col_data_idx),
        "linhas_totais": len(dados),
        "linhas_validas": len(final),
        "linhas_ruins": len(ruins),
        "metricas_colunas": metricas_colunas,
    }