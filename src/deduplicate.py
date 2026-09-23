"""
Deduplicação (entity resolution): descobre quais registros são a mesma pessoa.

1. Blocking: só comparamos registros que compartilham uma chave (CPF, e-mail,
   telefone ou data de nascimento). Um self-merge do Pandas por chave gera os
   pares candidatos sem comparar todos contra todos (~38 milhões de pares).
2. Regras de match: cada bloco tem sua exigência extra (ex.: e-mail igual E
   nome parecido, porque famílias compartilham e-mail).
3. Restrições "não pode ligar": CPFs válidos diferentes, ou datas de nascimento
   diferentes, nunca são a mesma pessoa.
4. Agrupamento: os pares viram grupos com union-find (componentes conexos).
   Se A=B e B=C, então A, B e C são o mesmo cliente.
"""

from __future__ import annotations

from difflib import SequenceMatcher

import pandas as pd

from src.config import SIMILARIDADE_NOME_MINIMA
from src.utils import configurar_logger

log = configurar_logger("deduplicate")

# regra -> (coluna de bloqueio, exige nome parecido?)
REGRAS = {
    "cpf": ("cpf", False),
    "email_e_nome": ("email", True),
    "telefone_e_nome": ("telefone", True),
    "nascimento_e_nome": ("data_nascimento", True),
}


def similaridade_nome(a: str, b: str) -> float:
    """
    Razão de similaridade (0 a 1) entre dois nomes normalizados.

    Nomes com o mesmo primeiro e último nome ganham um piso de 0,90: cobre
    abreviações ("maria s oliveira" x "maria silva oliveira").
    """
    razao = SequenceMatcher(None, a, b).ratio()
    pa, pb = a.split(), b.split()
    if pa and pb and pa[0] == pb[0] and pa[-1] == pb[-1]:
        razao = max(razao, 0.90)
    return razao


def gerar_pares(df: pd.DataFrame, regra: str) -> pd.DataFrame:
    chave, exige_nome = REGRAS[regra]
    base = df.loc[df[chave].notna(), ["registro_id", "chave_nome", "cpf", "data_nascimento", "cidade"]]
    base = base.assign(bloco=df[chave])
    pares = base.merge(base, on="bloco", suffixes=("_a", "_b")).query("registro_id_a < registro_id_b")

    def diferentes(coluna: str) -> pd.Series:
        a, b = pares[f"{coluna}_a"], pares[f"{coluna}_b"]
        return (a.notna() & b.notna() & (a != b)).fillna(False)

    # restrições "não pode ligar": CPFs válidos ou nascimentos diferentes = pessoas diferentes.
    # No bloco por nascimento (sem contato em comum) exigimos também a mesma cidade.
    conflito = diferentes("cpf") | diferentes("data_nascimento")
    if chave == "data_nascimento":
        conflito |= diferentes("cidade")
    pares = pares.loc[~conflito]

    pares = pares.assign(
        similaridade=[similaridade_nome(a, b) for a, b in zip(pares["chave_nome_a"], pares["chave_nome_b"])],
        regra=regra,
    )
    if exige_nome:
        pares = pares.loc[pares["similaridade"] >= SIMILARIDADE_NOME_MINIMA]
    return pares[["registro_id_a", "registro_id_b", "regra", "similaridade"]]


def agrupar(ids: pd.Series, pares: pd.DataFrame) -> pd.Series:
    """Union-find: devolve, para cada registro, o menor registro_id do seu grupo."""
    pai = {i: i for i in ids}

    def raiz(x):
        while pai[x] != x:
            pai[x] = pai[pai[x]]  # compressão de caminho
            x = pai[x]
        return x

    for a, b in zip(pares["registro_id_a"], pares["registro_id_b"]):
        ra, rb = raiz(a), raiz(b)
        if ra != rb:
            pai[max(ra, rb)] = min(ra, rb)
    return ids.map(raiz)


def deduplicar(registros: pd.DataFrame, regras: list[str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Atribui `cliente_id` a cada registro. Devolve (registros, pares encontrados)."""
    regras = regras or list(REGRAS)
    df = registros.assign(registro_id=range(len(registros)))
    pares = pd.concat([gerar_pares(df, regra) for regra in regras], ignore_index=True)

    grupo = agrupar(df["registro_id"], pares)
    df["cliente_id"] = "CLI-" + pd.Series(pd.factorize(grupo)[0] + 1, index=df.index).astype(str).str.zfill(5)

    tamanho = df.groupby("cliente_id")["registro_id"].transform("size")
    log.info("regras %s: %d pares -> %d registros viraram %d clientes (%d grupos com duplicidade)",
             "+".join(regras), len(pares), len(df), df["cliente_id"].nunique(),
             df.loc[tamanho > 1, "cliente_id"].nunique())
    return df, pares
