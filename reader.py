from __future__ import annotations

from pathlib import Path
import pandas as pd
import re
import unicodedata

from config import SourceConfig, AppConfig
from logger import setup_logger

log = setup_logger(__name__)

def looks_like_process_number(val: str) -> bool:
    """
    Heurística para verificar se um valor parece número de processo/CNJ.
    Aceita CNJ clássico e alguns formatos processuais menos rígidos.
    """
    s = str(val or "").strip()
    if not s:
        return False

    s = re.sub(r"\s+", "", s)

    if re.fullmatch(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}", s):
        return True

    digits = re.sub(r"\D", "", s)
    if len(digits) >= 15:
        return True

    if any(ch in s for ch in ["/", "-", "."]) and len(s) >= 10:
        return True

    return False

def safe_check_process_column(df, col, min_frac=0.3):
    """
    Verifica se a coluna que foi mapeada como CNJ/processo
    realmente parece conter números processuais válidos.
    """
    if col not in df.columns:
        log.warning(f"Coluna esperada '{col}' não encontrada no arquivo!")
        return False

    values = df[col].dropna().astype(str).head(50).tolist()
    values = [v for v in values if str(v).strip()]

    if not values:
        log.warning(f"Coluna '{col}' está vazia nas primeiras linhas.")
        return False

    match_type = [looks_like_process_number(x) for x in values]
    frac = sum(match_type) / len(match_type) if match_type else 0

    if frac < min_frac:
        log.error(
            f"ATENÇÃO: Possível desalinhamento: coluna '{col}' tem poucos valores com cara de processo "
            f"(exemplos: {values[:5]})"
        )
        return False

    return True


def slugcol(txt):
    txt = ''.join(c for c in unicodedata.normalize('NFD', str(txt)) if unicodedata.category(c) != 'Mn')
    txt = txt.lower().replace('_', ' ').replace('-', ' ').replace('.', ' ').strip()
    txt = re.sub(r'\s+', ' ', txt)
    return txt


def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    slugs = {slugcol(col): col for col in df.columns}
    for alias in candidates:
        key = slugcol(alias)
        for slugged, real in slugs.items():
            if key == slugged or key in slugged or slugged in key:
                return real
    return None


def is_valid_date(val) -> bool:
    try:
        pd_timestamp = pd.to_datetime(val, errors="coerce", dayfirst=True)
        return not pd.isnull(pd_timestamp)
    except Exception:
        return False


def safe_check_column(df, col, min_frac=0.7):
    if col not in df.columns:
        log.warning(f"Coluna esperada '{col}' não encontrada no arquivo!")
        return False

    values = df[col].dropna().astype(str).head(20).tolist()

    def looks_like_date(val):
        try:
            if not val.strip():
                return False
            d = pd.to_datetime(val, errors="coerce", dayfirst=True)
            return not pd.isnull(d)
        except Exception:
            return False

    match_type = [looks_like_date(x) for x in values if x.strip()]
    frac = sum(match_type) / len(match_type) if match_type else 0
    if frac < min_frac:
        log.error(
            f"ATENÇÃO: Possível desalinhamento: coluna '{col}' tem muitos valores não-data "
            f"(exemplos: {values[:5]})"
        )
        return False
    return True


def _detect_separator(sample: str, default_sep: str = ";") -> str:
    candidates = [";", ",", "\t", "|"]
    counts = {sep: sample.count(sep) for sep in candidates}
    best = max(counts, key=lambda sep: counts[sep])
    return best if counts[best] > 0 else default_sep


def _read_csv_auto_encoding(path: Path, sep: str, cnj_candidates: list[str], filename: str) -> tuple[pd.DataFrame, str | None]:
    encodings = [
        "utf-8-sig",
        "utf-8",
        "cp1252",
        "latin-1",
        "iso-8859-1",
    ]
    last_error = ""

    raw_sample = None
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc, errors="replace") as f:
                raw_sample = f.read(5000)
            break
        except Exception:
            continue

    seps_to_try = [sep]
    if raw_sample:
        detected_sep = _detect_separator(raw_sample, default_sep=sep)
        if detected_sep not in seps_to_try:
            seps_to_try.append(detected_sep)
        for extra in [";", ",", "\t", "|"]:
            if extra not in seps_to_try:
                seps_to_try.append(extra)

    for enc in encodings:
        for current_sep in seps_to_try:
            for skip in range(0, 6):
                try:
                    df = pd.read_csv(
                        path,
                        sep=current_sep,
                        dtype=str,
                        encoding=enc,
                        skiprows=skip,
                        on_bad_lines="skip",
                        engine="python",
                    )

                    if df is None or len(df.columns) == 0:
                        continue

                    df.columns = [str(c).strip() for c in df.columns]
                    df = df.loc[:, [str(c).strip() != "" for c in df.columns]]

                    if len(df.columns) == 0:
                        continue

                    log.info(
                        f"CSV '{filename}' lido com encoding={enc}, sep='{current_sep}', skiprows={skip}"
                    )
                    log.info(f"Colunas lidas do arquivo '{filename}': {df.columns.tolist()}")
                    log.info(f"Primeiras 3 linhas de '{filename}':\n{df.head(3).to_string()}")

                    col_cnj = find_column(df, cnj_candidates)
                    if col_cnj:
                        if skip > 0:
                            log.info(f"Pulou {skip} linha(s) de cabeçalho extra no CSV '{filename}'")
                        log.info(f"Coluna CNJ mapeada: '{col_cnj}'")
                        return df, col_cnj

                except Exception as e:
                    last_error = str(e)
                    continue

    raise ValueError(
        f"Não foi possível ler {path} com nenhum encoding/separador. Último erro: {last_error}"
    )


def _read_excel_auto_skip(path: Path, cnj_candidates: list[str], filename: str) -> tuple[pd.DataFrame | None, str | None]:
    for skip in range(0, 11):
        try:
            df = pd.read_excel(path, dtype=str, engine="openpyxl", skiprows=skip)

            if df is None or len(df.columns) == 0:
                continue

            df.columns = [str(c).strip() for c in df.columns]
            log.info(f"Colunas lidas do arquivo '{filename}': {df.columns.tolist()}")
            log.info(f"Primeiras 3 linhas de '{filename}':\n{df.head(3).to_string()}")

            col_cnj = find_column(df, cnj_candidates)
            if col_cnj:
                if skip > 0:
                    log.info("Pulou %d linha(s) de cabeçalho extra", skip)
                log.info(f"Coluna CNJ mapeada: '{col_cnj}'")
                return df, col_cnj
        except Exception:
            continue

    return None, None


def force_column_case_insensitive(df: pd.DataFrame, colname: str) -> str | None:
    for c in df.columns:
        if slugcol(c) == slugcol(colname):
            return c
    return None


def _clean_str(val) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() == "nan":
        return ""
    return s


def _normalize_tribunal(raw: str) -> str:
    s = _clean_str(raw).upper()
    if not s:
        return ""

    s = s.replace("º", "ª")
    s = re.sub(r"\s+", " ", s).strip()

    m = re.search(r"\bTRT[\s\-]?(\d{1,2})\b", s)
    if m:
        return f"TRT{int(m.group(1))}"

    m = re.search(r"TRIBUNAL REGIONAL DO TRABALHO DA (\d{1,2})[ªA] REGIAO", slugcol(s).upper().replace("Ã", "A"))
    if m:
        return f"TRT{int(m.group(1))}"

    slug = slugcol(s).upper()
    m = re.search(r"TRIBUNAL REGIONAL DO TRABALHO DA (\d{1,2})A REGIAO", slug)
    if m:
        return f"TRT{int(m.group(1))}"

    m = re.search(r"\b(TJ[A-Z]{2})\b", s)
    if m:
        return m.group(1)

    m = re.search(r"\b(TRF[\s\-]?(\d))\b", s)
    if m:
        return f"TRF{m.group(2)}"

    m = re.search(r"\b(STJ|STF|TST|TRE[\s\-]?\d{1,2}|TJM[A-Z]{0,2}|TRT[\s\-]?\d{1,2})\b", s)
    if m:
        return m.group(1).replace(" ", "").replace("-", "")

    return s.strip()


def _normalize_sistema(raw: str) -> str:
    s = _clean_str(raw).upper()
    if not s:
        return ""

    for token in ["PJE", "ESAJ", "DJEN", "EPROC", "PROJUDI", "EPROCJUD", "CRETA", "SAJ", "SEEU"]:
        if token in s:
            return token

    return s.strip()


def _extract_dw_tribunal_sistema(raw: str) -> tuple[str, str]:
    s = _clean_str(raw)
    if not s:
        return "", ""

    parts = [p.strip() for p in s.split("-") if p.strip()]
    tribunal = _normalize_tribunal(parts[0]) if len(parts) >= 1 else ""
    sistema = _normalize_sistema(parts[1]) if len(parts) >= 2 else ""
    return tribunal, sistema


def _extract_webjur_tribunal_sistema(diario_oficial: str) -> tuple[str, str]:
    tribunal = _normalize_tribunal(diario_oficial)
    sistema = "DJEN"
    return tribunal, sistema


def _extract_painel_tribunal_sistema(raw: str) -> tuple[str, str]:
    s = _clean_str(raw).upper()
    if not s:
        return "", ""

    if "/" in s:
        parts = [p.strip() for p in s.split("/") if p.strip()]
    elif " - " in s:
        parts = [p.strip() for p in s.split(" - ") if p.strip()]
    elif "-" in s:
        parts = [p.strip() for p in s.split("-") if p.strip()]
    else:
        parts = re.split(r"\s+", s)

    tribunal = _normalize_tribunal(parts[0]) if len(parts) >= 1 else ""
    sistema = _normalize_sistema(parts[1]) if len(parts) >= 2 else ""

    return tribunal, sistema


def _extract_tribunal_sistema_by_source(
    df: pd.DataFrame,
    filename: str,
    source_tag: str,
) -> tuple[pd.Series, pd.Series]:
    filename_lower = filename.lower()
    source_tag_lower = (source_tag or "").lower()

    tribunal_series = pd.Series([""] * len(df), index=df.index, dtype="object")
    sistema_series = pd.Series([""] * len(df), index=df.index, dtype="object")

    if "webjur" in filename_lower or "webjur" in source_tag_lower:
        col_diario = force_column_case_insensitive(df, "Diário Oficial")
        if not col_diario:
            col_diario = force_column_case_insensitive(df, "Diario Oficial")

        if col_diario:
            extracted = df[col_diario].apply(_extract_webjur_tribunal_sistema)
            tribunal_series = extracted.apply(lambda x: x[0])
            sistema_series = extracted.apply(lambda x: x[1])
        else:
            sistema_series = pd.Series(["DJEN"] * len(df), index=df.index, dtype="object")

    elif "dw" in filename_lower or "dw" in source_tag_lower:
        col_origem = force_column_case_insensitive(df, "Sistema")
        if not col_origem:
            col_origem = find_column(df, ["Sistema", "Origem", "Tribunal/Sistema"])

        if col_origem:
            extracted = df[col_origem].apply(_extract_dw_tribunal_sistema)
            tribunal_series = extracted.apply(lambda x: x[0])
            sistema_series = extracted.apply(lambda x: x[1])

    elif "painel" in filename_lower or "painel" in source_tag_lower:
        col_painel = force_column_case_insensitive(df, "Status")
        if not col_painel and len(df.columns) > 0:
            col_painel = df.columns[0]

        if col_painel:
            extracted = df[col_painel].apply(_extract_painel_tribunal_sistema)
            tribunal_series = extracted.apply(lambda x: x[0])
            sistema_series = extracted.apply(lambda x: x[1])

    elif "modolegaloneintimacoes" in filename_lower or "modo_legalone_intimacoes" in source_tag_lower:
        sistema_series = pd.Series(["LEGALONE"] * len(df), index=df.index, dtype="object")

    tribunal_series = tribunal_series.fillna("").astype(str)
    sistema_series = sistema_series.fillna("").astype(str)

    return tribunal_series, sistema_series


def _resolve_source_dates(
    df: pd.DataFrame,
    filename: str,
    source_tag: str,
) -> tuple[str | None, str | None]:
    """
    Resolve:
    - col_publicacao: data real do processo/publicação
    - col_captura: data de leitura/acesso/captura, quando existir
    """
    filename_lower = filename.lower()
    source_tag_lower = (source_tag or "").lower()

    col_publicacao = None
    col_captura = None

    if "dw" in filename_lower or "dw" in source_tag_lower:
        publication_candidates = [
            "Disponibilização",
            "Disponibilizacao",
        ]
        capture_candidates = [
            "Data da leitura",
            "Data leitura",
        ]

        col_publicacao = find_column(df, publication_candidates)
        col_captura = find_column(df, capture_candidates)

    elif "painel" in filename_lower or "painel" in source_tag_lower:
        publication_candidates = [
            "DATA INTIMAÇÃO",
            "DATA DA INTIMAÇÃO",
            "Data Intimação",
            "Data da Intimação",
            "DATA INTIMACAO",
            "DATA DA INTIMACAO",
            "Data Intimacao",
            "Data da Intimacao",
        ]
        capture_candidates = [
            "DATA ACESSO PAINEL",
            "Data Acesso Painel",
            "Data de acesso ao painel",
        ]

        col_publicacao = find_column(df, publication_candidates)
        col_captura = find_column(df, capture_candidates)

    elif "webjur" in filename_lower or "webjur" in source_tag_lower:
        publication_candidates = [
            "Data da Publicação",
            "Data da Publicacao",
            "Data Publicação",
            "Data Publicacao",
            "Data da P",
        ]

        col_publicacao = find_column(df, publication_candidates)
        col_captura = None

    elif "modolegaloneintimacoes" in filename_lower or "modo_legalone_intimacoes" in source_tag_lower:
        publication_candidates = [
            "DATA DA INTIMAÇÃO",
            "DATA INTIMAÇÃO",
            "Data da Publicação",
            "Disponibilização",
            "Data de publicação",
            "Data Publicacao",
        ]
        col_publicacao = find_column(df, publication_candidates)
        col_captura = None

    else:
        publication_candidates = [
            "DATA DA INTIMAÇÃO",
            "DATA INTIMAÇÃO",
            "Data da Publicação",
            "Disponibilização",
            "Data de publicação",
            "Data Publicacao",
        ]
        col_publicacao = find_column(df, publication_candidates)
        col_captura = None

    return col_publicacao, col_captura


def _build_date_series(df: pd.DataFrame, col_name: str | None) -> pd.Series:
    if not col_name or col_name not in df.columns:
        return pd.Series([""] * len(df), index=df.index, dtype="object")

    raw_values = df[col_name]
    return raw_values.apply(lambda v: v if is_valid_date(v) else "")


def read_source(source: SourceConfig, input_dir: str) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    for filename in source.files:
        original_path = Path(input_dir) / filename
        path = original_path

        if getattr(source, "prefer_sanitized", False) and original_path.suffix.lower() == ".csv":
            sanitized_candidate = original_path.with_name(f"{original_path.stem}_SANITIZADO.csv")

            if sanitized_candidate.exists():
                log.info("Arquivo bruto detectado: %s", original_path)
                log.info("Arquivo sanitizado detectado: %s", sanitized_candidate)
                log.info("Usando sanitizado no lugar do bruto.")
                path = sanitized_candidate
            else:
                log.info("Sanitizado não encontrado; usando bruto: %s", original_path)

        if not path.exists():
            log.warning("Arquivo não encontrado, pulando: %s", path)
            continue

        log.info("Lendo: %s", path)
        log.info("Arquivo efetivamente lido para '%s': %s", filename, path.name)

        cnj_candidates = [
            source.cnj_column,
            "Processo",
            "Número do Processo",
            "Número CNJ",
            "Número de CNJ",
            "numero de cnj",
            "número",
            "n Processo",
            "Número d",
            "Processo CNJ",
            "Process d.",
            "PROCESSO ",
        ]

        if source.file_type == "xlsx":
            df, col_cnj = _read_excel_auto_skip(path, cnj_candidates, filename)
            if df is None or col_cnj is None:
                log.warning(f"Coluna CNJ não encontrada em {filename} mesmo pulando até 10 linhas.")
                continue
        elif source.file_type == "csv":
            sep = source.separator or ";"
            df, col_cnj = _read_csv_auto_encoding(path, sep, cnj_candidates, filename)
            if not col_cnj:
                log.warning(f"Coluna CNJ não encontrada em {filename} (CSV). Colunas: {df.columns.tolist()}")
                continue
        else:
            raise ValueError(f"Tipo não suportado: {source.file_type}")

        for c in df.columns:
            df[c] = df[c].astype(str).replace("nan", "", regex=False).fillna("")

        print(f"Headers lidos no arquivo {filename}: {list(df.columns)}")

        if "Publicação" in df.columns:
            col_texto = "Publicação"
        else:
            publish_candidates = ["Publicação", "Publicacao", "Texto", "Publicação targetID", "Texto publicado"]
            text_candidates = [source.text_column] if source.text_column else []
            text_candidates += publish_candidates
            col_texto = find_column(df, text_candidates)

        part_candidates = ["Termo Localizado", "Cliente", "Advogado", "Parte", "Advogados", "Advogado do processo"]
        col_cliente = find_column(df, part_candidates)

        raw_tag = getattr(source, "tag", "")
        source_tag = str(raw_tag).lower() if raw_tag else ""

        if "webjur" in filename.lower() or "webjur" in source_tag:
            if col_cnj and not safe_check_process_column(df, col_cnj):
                log.warning(
                    f"WebJur possivelmente desalinhado em '{filename}'. "
                    f"A coluna '{col_cnj}' não parece conter números de processo válidos. "
                    f"Este arquivo será IGNORADO para evitar contaminar o matching."
                )
                continue

        col_data_publicacao, col_data_captura = _resolve_source_dates(
            df=df,
            filename=filename,
            source_tag=source_tag,
        )

        if col_data_publicacao and not safe_check_column(df, col_data_publicacao):
            log.warning(
                f"Coluna de data de publicação '{col_data_publicacao}' em '{filename}' "
                f"não parece conter datas válidas. O arquivo será processado sem preencher data_publicacao."
            )
            col_data_publicacao = None

        if col_data_captura and not safe_check_column(df, col_data_captura):
            log.warning(
                f"Coluna de data de captura '{col_data_captura}' em '{filename}' "
                f"não parece conter datas válidas. O arquivo será processado sem preencher data_captura."
            )
            col_data_captura = None

        serie_tribunal, serie_sistema = _extract_tribunal_sistema_by_source(
            df=df,
            filename=filename,
            source_tag=source_tag,
        )

        extracted = pd.DataFrame()
        extracted["cnj"] = df[col_cnj] if col_cnj else ""

        total_linhas_fonte = len(df)
        cnj_preenchido_mask = extracted["cnj"].fillna("").astype(str).str.strip() != ""
        qtd_cnj_preenchido = int(cnj_preenchido_mask.sum())
        qtd_cnj_vazio = total_linhas_fonte - qtd_cnj_preenchido

        log.info(
            f"{filename}: total de linhas lidas={total_linhas_fonte} | "
            f"CNJ preenchido={qtd_cnj_preenchido} | CNJ vazio={qtd_cnj_vazio}"
        )

        if qtd_cnj_vazio > 0:
            exemplos_vazios = df.loc[~cnj_preenchido_mask].head(5).to_dict(orient="records")
            log.warning(f"{filename}: exemplos de linhas com CNJ vazio: {exemplos_vazios}")

        serie_data_publicacao = _build_date_series(df, col_data_publicacao)
        serie_data_captura = _build_date_series(df, col_data_captura)

        log.info(
            f"Colunas mapeadas: CNJ='{col_cnj}', DataPublicacao='{col_data_publicacao}', "
            f"DataCaptura='{col_data_captura}', Texto='{col_texto}', Cliente='{col_cliente}', "
            f"Tribunal/Sistema extraídos por fonte"
        )

        extracted["_data"] = serie_data_publicacao
        extracted["_data_publicacao"] = serie_data_publicacao
        extracted["_data_captura"] = serie_data_captura
        extracted["_texto"] = df[col_texto] if col_texto else ""
        extracted["_cliente"] = df[col_cliente] if col_cliente else ""
        extracted["_tribunal"] = serie_tribunal
        extracted["_sistema"] = serie_sistema
        extracted["_origem_arquivo"] = path.name
        frames.append(extracted)

    if not frames:
        log.warning("Nenhum arquivo encontrado para esta fonte.")
        return pd.DataFrame(columns=[
            "cnj",
            "_data",
            "_data_publicacao",
            "_data_captura",
            "_texto",
            "_cliente",
            "_tribunal",
            "_sistema",
            "_origem_arquivo",
        ])

    result = pd.concat(frames, ignore_index=True, sort=False)
    for col in [
        "_texto",
        "_data",
        "_data_publicacao",
        "_data_captura",
        "_cliente",
        "_tribunal",
        "_sistema",
    ]:
        if col not in result.columns:
            result[col] = ""
        result[col] = result[col].fillna("").astype(str)
    return result


def read_all_external(config: AppConfig) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for name, source in [
        ("painel", config.painel),
        ("dw", config.dw),
        ("webjur", config.webjur),
        ("modo_legalone_intimacoes", config.modo_legalone_intimacoes),
    ]:
        log.info("📂 Lendo fonte: %s", name.upper())
        df = read_source(source, config.input_dir)
        df["_fonte"] = name
        parts.append(df)

    combined = pd.concat(parts, ignore_index=True, sort=False)
    for col in [
        "_texto",
        "_data",
        "_data_publicacao",
        "_data_captura",
        "_cliente",
        "_tribunal",
        "_sistema",
    ]:
        if col not in combined.columns:
            combined[col] = ""
        combined[col] = combined[col].fillna("")

    before = len(combined)
    total_before_filter = len(combined)
    cnj_nonempty_mask = combined["cnj"].fillna("").astype(str).str.strip() != ""
    total_nonempty = int(cnj_nonempty_mask.sum())
    total_empty = total_before_filter - total_nonempty

    log.info(
        f"read_all_external: antes do filtro CNJ vazio={total_before_filter} | "
        f"com CNJ={total_nonempty} | sem CNJ={total_empty}"
    )

    if total_empty > 0:
        exemplos_sem_cnj = combined.loc[~cnj_nonempty_mask].head(5).to_dict(orient="records")
        log.warning(f"read_all_external: exemplos sem CNJ: {exemplos_sem_cnj}")

    combined = combined[combined["cnj"] != ""].copy()
    removed = before - len(combined)
    if removed:
        log.warning("Removidas %d linhas com CNJ vazio das bases externas.", removed)

    return combined