"""Leitor multi-fonte (Excel/CSV) com detecção automática de encoding e busca case-insensitive de colunas."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from config import SourceConfig

def _read_csv_auto_encoding(path: Path, sep: str, cnj_column: str) -> pd.DataFrame:
    """Tenta ler CSV com vários encodings até funcionar (case-insensitive)."""
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252", "iso-8859-1"]
    last_error = None

    for enc in encodings:
        try:
            df = pd.read_csv(path, sep=sep, dtype=str, encoding=enc)
            df.columns = [c.strip() for c in df.columns]

            # Busca case-insensitive
            col_map = {c.lower(): c for c in df.columns}
            if cnj_column.lower() in col_map:
                real_name = col_map[cnj_column.lower()]
                if real_name != cnj_column:
                    print(f"    (coluna '{real_name}' mapeada para '{cnj_column}')")
                    df = df.rename(columns={real_name: cnj_column})
                print(f"    (encoding detectado: {enc})")
                return df
        except (UnicodeDecodeError, UnicodeError) as e:
            last_error = e
            continue
        except Exception as e:
            last_error = e
            continue

    raise ValueError(
        f"Não foi possível ler {path} com nenhum encoding. "
        f"Último erro: {last_error}"
    )

def _read_excel_auto_skip(path: Path, required_column: str) -> pd.DataFrame:
    """Tenta ler Excel pulando linhas até achar a coluna desejada (case-insensitive)."""
    for skip in range(0, 11):
        try:
            candidate = pd.read_excel(path, dtype=str, engine="openpyxl", skiprows=skip)
            candidate.columns = [c.strip() for c in candidate.columns]

            # Busca case-insensitive
            col_map = {c.lower(): c for c in candidate.columns}
            if required_column.lower() in col_map:
                real_name = col_map[required_column.lower()]
                if real_name != required_column:
                    print(f"    (coluna '{real_name}' mapeada para '{required_column}')")
                    candidate = candidate.rename(columns={real_name: required_column})
                if skip > 0:
                    print(f"    (pulou {skip} linha(s) de cabeçalho extra)")
                return candidate
        except Exception:
            continue

    raise ValueError(
        f"Coluna '{required_column}' não encontrada em {path} "
        f"mesmo pulando até 10 linhas."
    )

def read_source(source: SourceConfig, input_dir: str) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for filename in source.files:
        path = Path(input_dir) / filename
        if not path.exists():
            print(f"  [AVISO] Arquivo não encontrado, pulando: {path}")
            continue
        print(f"  Lendo: {path}")
        if source.file_type == "xlsx":
            df = _read_excel_auto_skip(path, source.cnj_column)
        elif source.file_type == "csv":
            sep = source.separator or ","
            df = _read_csv_auto_encoding(path, sep, source.cnj_column)
            if source.cnj_column not in df.columns:
                raise ValueError(
                    f"Coluna '{source.cnj_column}' não encontrada em {path}. "
                    f"Colunas: {list(df.columns)}"
                )
        else:
            raise ValueError(f"Tipo não suportado: {source.file_type}")

        cols_to_keep = [source.cnj_column]
        for extra_col in source.extra_match_columns:
            if extra_col in df.columns:
                cols_to_keep.append(extra_col)
        if source.text_column and source.text_column in df.columns:
            cols_to_keep.append(source.text_column)
        elif source.text_column and source.text_column not in df.columns:
            # Tenta case-insensitive para text_column também
            col_map = {c.lower(): c for c in df.columns}
            if source.text_column.lower() in col_map:
                real_name = col_map[source.text_column.lower()]
                print(f"    (coluna de texto '{real_name}' mapeada para '{source.text_column}')")
                df = df.rename(columns={real_name: source.text_column})
                cols_to_keep.append(source.text_column)
            else:
                print(f"    [AVISO] Coluna de texto '{source.text_column}' não encontrada em {path}")

        extracted = df[cols_to_keep].copy()
        extracted = extracted.rename(columns={source.cnj_column: "cnj"})
        extracted["cnj"] = extracted["cnj"].fillna("").str.strip()
        if source.text_column and source.text_column in extracted.columns:
            extracted = extracted.rename(columns={source.text_column: "_texto"})
            extracted["_texto"] = extracted["_texto"].fillna("").str.strip()
        for extra_col in source.extra_match_columns:
            if extra_col in extracted.columns:
                extracted[extra_col] = extracted[extra_col].fillna("").str.strip()
        extracted["_origem_arquivo"] = filename
        frames.append(extracted)

    if not frames:
        print(f"  [AVISO] Nenhum arquivo encontrado para esta fonte.")
        cols = ["cnj", "_origem_arquivo", "_texto"] + source.extra_match_columns
        return pd.DataFrame(columns=cols)

    result = pd.concat(frames, ignore_index=True)
    if "_texto" not in result.columns:
        result["_texto"] = ""
    return result

def read_all_external(config) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for name, source in [("painel", config.painel), ("dw", config.dw), ("webjur", config.webjur)]:
        print(f"\n📂 Lendo fonte: {name.upper()}")
        df = read_source(source, config.input_dir)
        df["_fonte"] = name
        parts.append(df)

    combined = pd.concat(parts, ignore_index=True)
    if "_texto" not in combined.columns:
        combined["_texto"] = ""
    combined["_texto"] = combined["_texto"].fillna("")

    before = len(combined)
    combined = combined[combined["cnj"] != ""].copy()
    removed = before - len(combined)
    if removed:
        print(f"\n⚠️  Removidas {removed} linhas com CNJ vazio das bases externas.")
    return combined