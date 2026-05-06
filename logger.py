from __future__ import annotations

import logging
from pathlib import Path
from datetime import datetime
from typing import Any

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def setup_logger(name: str = "matcher") -> logging.Logger:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"{name}_{timestamp}.log"

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


def log_classification_stats(
    logger: logging.Logger,
    df: Any,
    stage: str,
    category_col: str | None = None,
):
    """Log estatísticas de classificação."""
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 ESTATÍSTICAS — {stage}")
    logger.info(f"{'='*60}")
    logger.info(f"   Total de registros: {len(df)}")

    if category_col and category_col in df.columns:
        counts = df[category_col].value_counts(dropna=False)
        logger.info("\n   Classificação por categoria:")
        for cat, count in counts.items():
            pct = (count / len(df) * 100)
            logger.info(f"      • {cat or 'SEM_CATEGORIA'}: {count} ({pct:.1f}%)")

        sem_cat = df[df[category_col].isna()]
        if len(sem_cat) > 0:
            logger.warning(f"\n   ⚠️  {len(sem_cat)} registros SEM CATEGORIA ({len(sem_cat)/len(df)*100:.1f}%)")


def log_matching_results(logger, trab, civel, com_match, total):
    """Loga resultados do matching com proteção para divisão por zero."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("RESULTADOS DO MATCHING")
    logger.info("=" * 60)
    logger.info(f"   Total processado: {total}")

    if total == 0:
        logger.info("   Trabalhista sem match: 0 (0.0%)")
        logger.info("   Civel sem match: 0 (0.0%)")
        logger.info("   COM MATCH: 0 (0.0%)")
        logger.info("   Nenhum registro encontrado nas bases externas.")
        return

    logger.info(f"   Trabalhista sem match: {trab} ({trab/total*100:.1f}%)")
    logger.info(f"   Civel sem match: {civel} ({civel/total*100:.1f}%)")
    logger.info(f"   COM MATCH: {com_match} ({com_match/total*100:.1f}%)")


def log_confidence_distribution(logger: logging.Logger, df, confidence_col: str = "_confidence_civel"):
    """Log distribuição de confiança."""
    if confidence_col not in df.columns:
        return

    logger.info(f"\n{'='*60}")
    logger.info("📈 DISTRIBUIÇÃO DE CONFIANÇA")
    logger.info(f"{'='*60}")

    for bucket in [0, 20, 40, 60, 80, 90, 100]:
        if bucket == 100:
            count = len(df[df[confidence_col] == 100])
        else:
            count = len(df[(df[confidence_col] >= bucket) & (df[confidence_col] < bucket + 20)])
        pct = (count / len(df) * 100) if len(df) > 0 else 0
        logger.info(f"   [{bucket:3d}-{min(bucket+20, 100):3d}]: {count:6d} ({pct:5.1f}%)")