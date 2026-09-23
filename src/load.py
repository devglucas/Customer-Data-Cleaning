"""Exportação dos resultados para data/processed e output/reports."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import PROCESSED_DIR, REPORTS_DIR, ROOT_DIR
from src.utils import configurar_logger

log = configurar_logger("load")


def salvar_csv(df: pd.DataFrame, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, index=False, encoding="utf-8")


def mascarar_cpf(cpf: pd.Series) -> pd.Series:
    """52998224725 -> ***.982.247-** (só os dígitos do meio ficam visíveis)."""
    return "***." + cpf.str[3:6] + "." + cpf.str[6:9] + "-**"


def base_marketing(golden: pd.DataFrame) -> pd.DataFrame:
    """
    Base para campanhas de e-mail seguindo a LGPD:
    - só clientes com consentimento explícito (opt-in) e e-mail válido
    - minimização: apenas os campos necessários para a campanha
    - CPF mascarado (serve para conferência, não identifica sozinho)
    """
    elegiveis = golden.loc[golden["opt_in_marketing"] & golden["email"].notna()]
    return pd.DataFrame({
        "cliente_id": elegiveis["cliente_id"],
        "primeiro_nome": elegiveis["nome"].str.split(" ").str[0],
        "email": elegiveis["email"],
        "cidade": elegiveis["cidade"],
        "uf": elegiveis["uf"],
        "faixa_etaria": elegiveis["faixa_etaria"],
        "cpf_mascarado": mascarar_cpf(elegiveis["cpf"]),
    })


def exportar_dados(golden: pd.DataFrame, registros: pd.DataFrame, rejeitados: pd.DataFrame) -> pd.DataFrame:
    marketing = base_marketing(golden)
    arquivos = {
        "clientes_unicos.csv": golden,
        "registros_padronizados.csv": registros,
        "mapa_registros_clientes.csv": registros[["origem", "id_origem", "cliente_id"]],
        "clientes_marketing.csv": marketing,
        "rejeitados.csv": rejeitados,
    }
    for nome, df in arquivos.items():
        salvar_csv(df, PROCESSED_DIR / nome)
    log.info("%d arquivos salvos em %s (%d clientes elegíveis para marketing)",
             len(arquivos), PROCESSED_DIR.relative_to(ROOT_DIR), len(marketing))
    return marketing


def exportar_relatorios(tabelas: dict[str, pd.DataFrame]) -> None:
    for nome, df in tabelas.items():
        salvar_csv(df, REPORTS_DIR / f"{nome}.csv")
    log.info("%d relatórios CSV salvos em %s", len(tabelas), REPORTS_DIR.relative_to(ROOT_DIR))
