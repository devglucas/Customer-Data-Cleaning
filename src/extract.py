"""
Extração: lê as três fontes e as coloca em um ESQUEMA COMUM, sem limpar nada.

Cada fonte tem nome de coluna, formato e codificação próprios. Aqui só
renomeamos e acrescentamos a origem; a limpeza é responsabilidade de
`standardize.py`. Separar as duas coisas facilita incluir uma quarta fonte.
"""

from __future__ import annotations

import pandas as pd

from src.config import ARQUIVOS_RAW
from src.utils import configurar_logger

log = configurar_logger("extract")

ESQUEMA = [
    "origem", "id_origem", "nome", "cpf", "data_nascimento", "genero", "email", "telefone",
    "endereco", "logradouro", "numero", "complemento", "bairro", "cidade", "uf", "cep",
    "opt_in_marketing", "data_atualizacao",
]


def ler_crm(caminho) -> pd.DataFrame:
    """Sistema legado: separador ';' e codificação latin-1 (não UTF-8)."""
    df = pd.read_csv(caminho, sep=";", encoding="latin-1", dtype="string")
    return df.rename(columns={
        "COD_CLIENTE": "id_origem", "NOME_CLIENTE": "nome", "CPF": "cpf", "DT_NASC": "data_nascimento",
        "SEXO": "genero", "EMAIL": "email", "FONE": "telefone", "ENDERECO": "endereco",
        "BAIRRO": "bairro", "CIDADE": "cidade", "UF": "uf", "CEP": "cep",
        "ACEITA_MKT": "opt_in_marketing", "DT_ATUALIZACAO": "data_atualizacao",
    }).assign(origem="crm")


def ler_app(caminho) -> pd.DataFrame:
    """JSON Lines: um objeto por linha, com o endereço aninhado (às vezes nulo)."""
    df = pd.read_json(caminho, lines=True, dtype=False, convert_dates=False)
    enderecos = pd.json_normalize(df["endereco"].map(lambda e: e if isinstance(e, dict) else {}).tolist())
    return (
        df.drop(columns="endereco")
        .join(enderecos)
        .rename(columns={"id": "id_origem", "celular": "telefone", "nascimento": "data_nascimento",
                         "marketing_opt_in": "opt_in_marketing", "atualizado_em": "data_atualizacao"})
        .assign(origem="app")
    )


def ler_lojas(caminho) -> pd.DataFrame:
    """
    Excel com uma aba por loja. O cabeçalho está na 3ª linha (há um título acima).
    `sheet_name=None` lê todas as abas em um dicionário {nome_da_aba: DataFrame}.
    Lemos como `object` para preservar o tipo de cada célula (data, número ou texto).
    """
    abas = pd.read_excel(caminho, sheet_name=None, header=2, dtype=object)
    df = pd.concat(abas, names=["loja", None]).reset_index(level=0).reset_index(drop=True)
    df["id_origem"] = df["loja"] + "#" + df["Cód."].astype(str)
    return df.rename(columns={
        "Nome": "nome", "CPF": "cpf", "Telefone": "telefone", "Data Nascimento": "data_nascimento",
        "E-mail": "email", "Cidade": "cidade", "Aceita receber ofertas?": "opt_in_marketing",
        "Data Cadastro": "data_atualizacao",
    }).assign(origem="loja")


def extrair_registros() -> pd.DataFrame:
    fontes = [ler_crm(ARQUIVOS_RAW["crm"]), ler_app(ARQUIVOS_RAW["app"]), ler_lojas(ARQUIVOS_RAW["loja"])]
    for fonte in fontes:
        log.info("%-5s %5d registros | %2d colunas originais", fonte["origem"].iat[0], len(fonte), fonte.shape[1])
    # reindex garante o mesmo esquema: colunas que a fonte não tem viram nulas
    registros = pd.concat([f.reindex(columns=ESQUEMA) for f in fontes], ignore_index=True)
    registros["id_origem"] = registros["id_origem"].astype("string")
    log.info("total %5d registros no esquema comum", len(registros))
    return registros
