"""Funções genéricas de texto, datas, rejeição de registros e formatação."""

from __future__ import annotations

import datetime as dt
import logging

import numpy as np
import pandas as pd

PREPOSICOES = r"\b(Da|De|Do|Das|Dos|E)\b"


def configurar_logger(nome: str = "pipeline") -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger(nome)


# --------------------------------------------------------------------------- #
# Texto
# --------------------------------------------------------------------------- #
def normalizar_espacos(serie: pd.Series) -> pd.Series:
    return serie.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)


def remover_acentos(serie: pd.Series) -> pd.Series:
    return (
        serie.astype("string").str.normalize("NFKD")
        .str.encode("ascii", "ignore").str.decode("ascii").astype("string")
    )


def chave_texto(serie: pd.Series) -> pd.Series:
    """Forma canônica para comparar textos: minúsculo, sem acento, sem espaços extras."""
    return remover_acentos(normalizar_espacos(serie).str.lower())


def mapear(serie: pd.Series, mapa: dict) -> pd.Series:
    """De-para sobre a chave normalizada. Valores fora do mapa viram NA."""
    return chave_texto(serie).map(mapa)


def titulo_pt(serie: pd.Series) -> pd.Series:
    """Title case respeitando preposições do português ("Maria da Silva")."""
    return (
        normalizar_espacos(serie).str.title()
        .str.replace(PREPOSICOES, lambda m: m.group(0).lower(), regex=True)
    )


def grafia_mais_frequente(serie: pd.Series) -> pd.Series:
    """Unifica variações ("São Paulo", "SAO PAULO") pela grafia mais comum da mesma chave."""
    limpa = normalizar_espacos(serie)
    return limpa.groupby(chave_texto(limpa)).transform(lambda s: s.mode().iat[0])


# --------------------------------------------------------------------------- #
# Datas
# --------------------------------------------------------------------------- #
def parse_datas(serie: pd.Series, formatos: list[str]) -> pd.Series:
    """Tenta cada formato conhecido em sequência (sem adivinhar dia/mês)."""
    texto = serie.astype("string").str.strip()
    resultado = pd.to_datetime(texto, format=formatos[0], errors="coerce")
    for formato in formatos[1:]:
        resultado = resultado.fillna(pd.to_datetime(texto, format=formato, errors="coerce"))
    return resultado


def parse_data_mista(serie: pd.Series, formatos: list[str], formatos_ano_2_digitos: list[str] = ()) -> pd.Series:
    """
    Converte colunas que misturam, célula a célula:
    - objetos de data (células de data do Excel)
    - números seriais do Excel (dias desde 30/12/1899)
    - textos em formatos conhecidos
    - textos com ano de 2 dígitos: o século é escolhido para a data não ficar no futuro
    """
    eh_data = serie.map(lambda v: isinstance(v, (dt.date, pd.Timestamp)))
    eh_numero = serie.map(lambda v: isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool))
    eh_texto = serie.map(lambda v: isinstance(v, str))

    datas = pd.to_datetime(serie.where(eh_data), errors="coerce")
    seriais = pd.to_datetime(pd.to_numeric(serie.where(eh_numero), errors="coerce"),
                             unit="D", origin="1899-12-30", errors="coerce")
    textos = parse_datas(serie.where(eh_texto), formatos)
    if formatos_ano_2_digitos:
        curtas = parse_datas(serie.where(eh_texto & textos.isna()), list(formatos_ano_2_digitos))
        # %y interpreta 00-68 como 2000-2068: "05/03/55" viraria 2055
        curtas = curtas.mask(curtas > pd.Timestamp.now(), curtas - pd.DateOffset(years=100))
        textos = textos.fillna(curtas)
    return datas.fillna(seriais).fillna(textos).astype("datetime64[ns]")


# --------------------------------------------------------------------------- #
# Rejeição de registros
# --------------------------------------------------------------------------- #
def separar_rejeitados(df: pd.DataFrame, invalido: pd.Series, motivo: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    invalido = invalido.fillna(False).astype(bool)
    return df.loc[~invalido], df.loc[invalido].assign(motivo_rejeicao=motivo)


# --------------------------------------------------------------------------- #
# Formatação para relatórios
# --------------------------------------------------------------------------- #
def formatar_br(valor, casas: int = 2) -> str:
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return ""
    if isinstance(valor, (bool, np.bool_)):
        return "sim" if valor else "não"
    if isinstance(valor, (int, np.integer)):
        return f"{valor:,}".replace(",", ".")
    if isinstance(valor, (float, np.floating)):
        return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return str(valor)


def df_para_markdown(df: pd.DataFrame, casas: int = 2) -> str:
    cabecalho = "| " + " | ".join(map(str, df.columns)) + " |"
    separador = "|" + "|".join("---" for _ in df.columns) + "|"
    linhas = [
        "| " + " | ".join("" if pd.isna(v) else formatar_br(v, casas) for v in linha) + " |"
        for linha in df.itertuples(index=False)
    ]
    return "\n".join([cabecalho, separador, *linhas])
