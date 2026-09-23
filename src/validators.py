"""
Validadores de documentos e contatos brasileiros, vetorizados com Pandas/NumPy.

Todos recebem uma Series já normalizada (só dígitos / minúsculas) e devolvem
uma Series booleana. Nulos são sempre inválidos.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

REGEX_EMAIL = r"[a-z0-9._%+-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}"

DDDS_VALIDOS = {
    "11", "12", "13", "14", "15", "16", "17", "18", "19", "21", "22", "24", "27", "28",
    "31", "32", "33", "34", "35", "37", "38", "41", "42", "43", "44", "45", "46", "47", "48", "49",
    "51", "53", "54", "55", "61", "62", "63", "64", "65", "66", "67", "68", "69",
    "71", "73", "74", "75", "77", "79", "81", "82", "83", "84", "85", "86", "87", "88", "89",
    "91", "92", "93", "94", "95", "96", "97", "98", "99",
}


def cpf_valido(cpfs: pd.Series) -> pd.Series:
    """
    CPF com 11 dígitos, não repetidos (111.111.111-11) e dígitos verificadores corretos.

    DV1 = (soma dos 9 primeiros dígitos x pesos 10..2) * 10 % 11 % 10
    DV2 = (soma dos 10 primeiros dígitos x pesos 11..2) * 10 % 11 % 10
    """
    texto = cpfs.astype("string")
    # Dígitos todos iguais: compara com o 1º dígito repetido 11 vezes. (Não dá para usar
    # a regex (\d)\1{10}: strings do pandas 3 usam o motor RE2 do PyArrow, sem backreferences.)
    repetido = texto == texto.str[0].str.repeat(11)
    candidato = texto.str.fullmatch(r"\d{11}", na=False) & ~repetido.fillna(False)
    resultado = pd.Series(False, index=cpfs.index)
    if candidato.any():
        digitos = np.array([list(cpf) for cpf in texto[candidato]], dtype=int)
        dv1 = digitos[:, :9] @ np.arange(10, 1, -1) * 10 % 11 % 10
        dv2 = digitos[:, :10] @ np.arange(11, 1, -1) * 10 % 11 % 10
        resultado[candidato] = (dv1 == digitos[:, 9]) & (dv2 == digitos[:, 10])
    return resultado


def email_valido(emails: pd.Series) -> pd.Series:
    return emails.astype("string").str.fullmatch(REGEX_EMAIL, na=False)


def telefone_valido(telefones: pd.Series) -> pd.Series:
    """Celular: DDD + 9 + 8 dígitos. Fixo: DDD + [2-5] + 7 dígitos."""
    texto = telefones.astype("string")
    ddd_ok = texto.str[:2].isin(DDDS_VALIDOS)
    celular = texto.str.fullmatch(r"\d{2}9\d{8}", na=False)
    fixo = texto.str.fullmatch(r"\d{2}[2-5]\d{7}", na=False)
    return ddd_ok & (celular | fixo)


def cep_valido(ceps: pd.Series) -> pd.Series:
    texto = ceps.astype("string")
    return texto.str.fullmatch(r"\d{8}", na=False) & ~texto.str.fullmatch(r"0{8}", na=False)
