"""
Validação do cadastro final.

- "critica": interrompe o pipeline (o cadastro não pode ser publicado)
- "alerta":  registrada no relatório (limitação dos dados, não erro do pipeline)
"""

from __future__ import annotations

import pandas as pd

from src.config import IDADE_MAXIMA, IDADE_MINIMA
from src.mappings import UFS_VALIDAS
from src.utils import configurar_logger
from src.validators import cep_valido, cpf_valido, email_valido, telefone_valido

log = configurar_logger("validate")


class ErroDeValidacao(Exception):
    pass


def _regra(resultados: list, tabela: str, regra: str, falhas, severidade: str = "critica") -> None:
    qtd = int(falhas.sum()) if isinstance(falhas, pd.Series) else int(bool(falhas))
    resultados.append({"tabela": tabela, "regra": regra, "severidade": severidade,
                       "registros_com_falha": qtd, "passou": qtd == 0})


def validar(golden: pd.DataFrame, registros: pd.DataFrame) -> pd.DataFrame:
    r: list[dict] = []
    g = golden

    _regra(r, "clientes", "cliente_id único", g["cliente_id"].duplicated())
    _regra(r, "clientes", "CPF único entre clientes", g["cpf"].dropna().duplicated())
    _regra(r, "clientes", "CPF válido quando preenchido", g["cpf"].notna() & ~cpf_valido(g["cpf"]))
    _regra(r, "clientes", "e-mail válido quando preenchido", g["email"].notna() & ~email_valido(g["email"]))
    _regra(r, "clientes", "telefone válido quando preenchido", g["telefone"].notna() & ~telefone_valido(g["telefone"]))
    _regra(r, "clientes", "CEP válido quando preenchido", g["cep"].notna() & ~cep_valido(g["cep"]))
    _regra(r, "clientes", "UF válida quando preenchida", g["uf"].notna() & ~g["uf"].isin(UFS_VALIDAS))
    _regra(r, "clientes", f"idade entre {IDADE_MINIMA} e {IDADE_MAXIMA} anos",
           g["idade"].notna() & ~g["idade"].between(IDADE_MINIMA, IDADE_MAXIMA))
    _regra(r, "clientes", "nome preenchido", g["nome"].isna() | g["nome"].str.len().lt(3))

    _regra(r, "registros", "todo registro pertence a um cliente", ~registros["cliente_id"].isin(g["cliente_id"]))
    _regra(r, "registros", "soma de qtd_registros = total de registros", g["qtd_registros"].sum() != len(registros))
    cpfs_por_cliente = registros.groupby("cliente_id")["cpf"].nunique()
    _regra(r, "registros", "nenhum cliente reúne CPFs diferentes", cpfs_por_cliente > 1)

    _regra(r, "clientes", "cliente com CPF", g["cpf"].isna(), "alerta")
    _regra(r, "clientes", "cliente com e-mail ou telefone", ~g["possui_contato"], "alerta")
    _regra(r, "clientes", "cliente com data de nascimento", g["data_nascimento"].isna(), "alerta")
    _regra(r, "clientes", "cliente com endereço", g["logradouro"].isna(), "alerta")
    return pd.DataFrame(r)


def garantir_qualidade(resultado: pd.DataFrame) -> None:
    for linha in resultado.query("not passou").itertuples():
        nivel = log.error if linha.severidade == "critica" else log.warning
        nivel("[%s] %s: %s -> %d registros", linha.severidade, linha.tabela, linha.regra, linha.registros_com_falha)
    criticas = resultado.query("severidade == 'critica' and not passou")
    if not criticas.empty:
        raise ErroDeValidacao(f"regras críticas falharam: {criticas['regra'].tolist()}")
    log.info("%d regras verificadas: todas as críticas passaram (%d alertas)",
             len(resultado), (~resultado["passou"]).sum())
