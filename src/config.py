"""Caminhos, parâmetros e regras de negócio do pipeline."""

from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT_DIR / "data" / "raw"
EXTERNAL_DIR = ROOT_DIR / "data" / "external"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
OUTPUT_DIR = ROOT_DIR / "output"
REPORTS_DIR = OUTPUT_DIR / "reports"
CHARTS_DIR = OUTPUT_DIR / "charts"

ARQUIVOS_RAW = {
    "crm": RAW_DIR / "crm_clientes.csv",
    "app": RAW_DIR / "app_cadastros.jsonl",
    "loja": RAW_DIR / "lojas_cadastros.xlsx",
}
ARQUIVOS_GABARITO = {
    "registros": EXTERNAL_DIR / "gabarito_registros.csv",
    "pessoas": EXTERNAL_DIR / "gabarito_pessoas.csv",
}

DATA_REFERENCIA = pd.Timestamp("2025-12-31")  # data da consolidação
IDADE_MINIMA, IDADE_MAXIMA = 16, 110          # idades fora disso são tratadas como erro

# Deduplicação
SIMILARIDADE_NOME_MINIMA = 0.88  # 0 a 1 (difflib.SequenceMatcher)

# Em empate de data de atualização, qual fonte é mais confiável (menor = melhor)
PRIORIDADE_FONTE = {"crm": 1, "app": 2, "loja": 3}
