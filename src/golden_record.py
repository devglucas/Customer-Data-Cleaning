"""
Golden record: um registro por cliente, montado a partir de todos os registros
do grupo com regras de sobrevivência ("survivorship") por campo.

| Campo(s)                     | Regra                                                         |
|------------------------------|---------------------------------------------------------------|
| CPF                          | o CPF válido do grupo (a deduplicação garante que é único)    |
| data de nascimento           | valor mais frequente (protege contra erro de digitação)       |
| nome                         | sem abreviação > com acentos > mais recente                   |
| e-mail, telefone, gênero     | valor não nulo mais recente                                   |
| endereço (logradouro...CEP)  | todos do MESMO registro: o mais recente que tem endereço      |
| cidade/UF                    | do registro mais recente que tem cidade                       |
| opt-in de marketing          | resposta explícita mais recente; sem resposta = sem consentimento (LGPD) |

Empates de data são decididos pela confiabilidade da fonte (CRM > App > Loja).
"""

from __future__ import annotations

import pandas as pd

from src.config import DATA_REFERENCIA, PRIORIDADE_FONTE
from src.utils import configurar_logger, remover_acentos

log = configurar_logger("golden")

CAMPOS_ENDERECO = ["logradouro", "numero", "complemento", "bairro", "cep"]
CAMPOS_COMPLETUDE = ["cpf", "data_nascimento", "genero", "email", "telefone", "logradouro", "cep", "cidade"]
FAIXAS_ETARIAS = ([16, 25, 35, 45, 55, 65, 120], ["16-24", "25-34", "35-44", "45-54", "55-64", "65+"])


def _mais_recente_primeiro(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.assign(_prioridade=df["origem"].map(PRIORIDADE_FONTE))
        .sort_values(["cliente_id", "data_atualizacao", "_prioridade"], ascending=[True, False, True])
    )


def escolher_nome(df: pd.DataFrame) -> pd.Series:
    nomes = df.assign(
        _abreviado=df["nome"].str.contains(r"\b\w\.", regex=True, na=False),
        _acentuado=df["nome"] != remover_acentos(df["nome"]),
    ).sort_values(["cliente_id", "_abreviado", "_acentuado", "data_atualizacao"],
                  ascending=[True, True, False, False])
    return nomes.groupby("cliente_id")["nome"].first()


def valor_mais_frequente(df: pd.DataFrame, coluna: str) -> pd.Series:
    """Moda por cliente; em empate, o valor do registro mais recente (a ordem já vem assim)."""
    validos = df.dropna(subset=[coluna])
    contagem = validos.groupby(["cliente_id", coluna], sort=False).size().rename("n").reset_index()
    return contagem.sort_values("n", ascending=False, kind="stable").groupby("cliente_id")[coluna].first()


def montar_golden_record(registros: pd.DataFrame) -> pd.DataFrame:
    ordenado = _mais_recente_primeiro(registros)
    por_cliente = ordenado.groupby("cliente_id")

    # groupby().first() pega o primeiro valor NÃO NULO de cada coluna: como os registros
    # estão do mais recente para o mais antigo, é exatamente "o valor mais recente".
    recentes = por_cliente[["cpf", "email", "telefone", "tipo_telefone", "genero", "opt_in_marketing"]].first()

    # Endereço é um bloco: groupby().first() misturaria a rua de um registro com o CEP
    # de outro. drop_duplicates mantém a LINHA inteira do registro mais recente.
    endereco =ordenado.dropna(subset=["logradouro"]).drop_duplicates("cliente_id").set_index("cliente_id")[CAMPOS_ENDERECO]
    localidade = ordenado.dropna(subset=["cidade"]).drop_duplicates("cliente_id").set_index("cliente_id")[["cidade", "uf"]]

    metadados = por_cliente.agg(
        qtd_registros=("registro_id", "count"),
        fontes=("origem", lambda s: ", ".join(sorted(s.unique()))),
        primeiro_registro=("data_atualizacao", "min"),
        ultima_atualizacao=("data_atualizacao", "max"),
    )

    golden = (
        pd.DataFrame({"nome": escolher_nome(ordenado)})
        .join(recentes)
        .join(valor_mais_frequente(ordenado, "data_nascimento"))
        .join(endereco)
        .join(localidade)
        .join(metadados)
    )
    golden["opt_in_marketing"] = golden["opt_in_marketing"].fillna(False).astype(bool)
    golden["idade"] = ((DATA_REFERENCIA - golden["data_nascimento"]).dt.days // 365.25).astype("Int64")
    golden["faixa_etaria"] = pd.cut(golden["idade"], bins=FAIXAS_ETARIAS[0], labels=FAIXAS_ETARIAS[1], right=False)
    golden["possui_contato"] = golden["email"].notna() | golden["telefone"].notna()
    golden["completude_pct"] = golden[CAMPOS_COMPLETUDE].notna().mean(axis=1).mul(100).round(1)

    colunas = ["nome", "cpf", "data_nascimento", "idade", "faixa_etaria", "genero", "email", "telefone",
               "tipo_telefone", *CAMPOS_ENDERECO[:-1], "cidade", "uf", "cep", "opt_in_marketing",
               "possui_contato", "completude_pct", "qtd_registros", "fontes", "primeiro_registro",
               "ultima_atualizacao"]
    golden = golden[colunas].reset_index()
    log.info("%d clientes únicos | completude média %.1f%%", len(golden), golden["completude_pct"].mean())
    return golden
