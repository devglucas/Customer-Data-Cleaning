"""Métricas de qualidade por fonte, da deduplicação e perfil da base consolidada."""

from __future__ import annotations

import pandas as pd

# campo exibido -> coluna nos registros padronizados / golden record
CAMPOS = {
    "CPF": "cpf", "Data de nascimento": "data_nascimento", "Gênero": "genero", "E-mail": "email",
    "Telefone": "telefone", "Endereço": "logradouro", "CEP": "cep", "Cidade": "cidade",
}
ORDEM_FONTES = ["crm", "app", "loja"]


def completude_bruta(brutos: pd.DataFrame) -> pd.DataFrame:
    """% de preenchimento de cada coluna ANTES da limpeza (vazio ≠ válido)."""
    colunas = [c for c in brutos.columns if c not in ("origem", "id_origem")]
    return (
        brutos.groupby("origem")[colunas].agg(lambda s: s.notna().mean() * 100)
        .T.reindex(columns=ORDEM_FONTES).round(1).rename_axis("coluna").reset_index()
    )


def qualidade_por_fonte(padronizados: pd.DataFrame) -> pd.DataFrame:
    """% de registros com valor VÁLIDO após a padronização, por campo e fonte."""
    tabela = padronizados[list(CAMPOS.values())].notna().groupby(padronizados["origem"]).mean() * 100
    return (
        tabela.T.rename(index={v: k for k, v in CAMPOS.items()}).reindex(columns=ORDEM_FONTES)
        .round(1).rename_axis("campo").rename_axis(columns=None).reset_index()
    )


def status_cpf(padronizados: pd.DataFrame) -> pd.DataFrame:
    return (
        pd.crosstab(padronizados["cpf_status"], padronizados["origem"], margins=True, margins_name="total")
        .reindex(columns=[*ORDEM_FONTES, "total"]).rename_axis(columns=None).reset_index()
    )


def correcoes_por_fonte(padronizados: pd.DataFrame) -> pd.DataFrame:
    correcoes = padronizados.filter(like="corr_").groupby(padronizados["origem"]).sum().T
    correcoes = correcoes.reindex(columns=ORDEM_FONTES).fillna(0).astype(int)
    correcoes["total"] = correcoes.sum(axis=1)
    correcoes.index = correcoes.index.str.removeprefix("corr_")
    return correcoes.sort_values("total", ascending=False).rename_axis("correcao").rename_axis(columns=None).reset_index()


def pares_por_regra(pares: pd.DataFrame) -> pd.DataFrame:
    return (
        pares.groupby("regra", sort=False)
        .agg(pares=("regra", "size"), similaridade_media=("similaridade", "mean"),
             similaridade_minima=("similaridade", "min"))
        .round(3).reset_index()
    )


def sobreposicao_fontes(golden: pd.DataFrame) -> pd.DataFrame:
    contagem = golden["fontes"].value_counts().rename_axis("fontes").reset_index(name="clientes")
    contagem["pct"] = (contagem["clientes"] / contagem["clientes"].sum() * 100).round(1)
    return contagem


def tamanho_grupos(golden: pd.DataFrame) -> pd.DataFrame:
    return golden["qtd_registros"].value_counts().sort_index().rename_axis("registros_por_cliente") \
        .reset_index(name="clientes")


def ganho_sobrevivencia(registros: pd.DataFrame, golden: pd.DataFrame) -> pd.DataFrame:
    """
    Completude do cadastro final x "ficar só com o registro mais recente de cada
    cliente" (a deduplicação ingênua). A diferença é o ganho das regras de sobrevivência.
    """
    mais_recente = registros.sort_values("data_atualizacao", ascending=False).drop_duplicates("cliente_id")
    return pd.DataFrame({
        "campo": list(CAMPOS),
        "so_registro_mais_recente_pct": [round(mais_recente[c].notna().mean() * 100, 1) for c in CAMPOS.values()],
        "cadastro_final_pct": [round(golden[c].notna().mean() * 100, 1) for c in CAMPOS.values()],
    }).assign(ganho_pp=lambda d: (d["cadastro_final_pct"] - d["so_registro_mais_recente_pct"]).round(1))


def perfil_faixa_genero(golden: pd.DataFrame) -> pd.DataFrame:
    tabela = golden.assign(genero=golden["genero"].fillna("Não informado")).pivot_table(
        index="faixa_etaria", columns="genero", values="cliente_id", aggfunc="count", observed=False, fill_value=0)
    tabela["opt_in_pct"] = golden.groupby("faixa_etaria", observed=False)["opt_in_marketing"].mean().mul(100).round(1)
    return tabela.rename_axis(columns=None).reset_index()


def clientes_por_uf(golden: pd.DataFrame) -> pd.DataFrame:
    return (
        golden.assign(uf=golden["uf"].fillna("ND"))
        .groupby("uf").agg(clientes=("cliente_id", "count"), opt_in_pct=("opt_in_marketing", "mean"),
                           completude_media_pct=("completude_pct", "mean"))
        .assign(opt_in_pct=lambda d: (d["opt_in_pct"] * 100).round(1),
                completude_media_pct=lambda d: d["completude_media_pct"].round(1))
        .sort_values("clientes", ascending=False).reset_index()
    )


def gerar_analises(brutos, padronizados, pares, golden) -> dict[str, pd.DataFrame]:
    return {
        "completude_bruta_por_fonte": completude_bruta(brutos),
        "qualidade_por_fonte": qualidade_por_fonte(padronizados),
        "status_cpf_por_fonte": status_cpf(padronizados),
        "correcoes_por_fonte": correcoes_por_fonte(padronizados),
        "pares_por_regra": pares_por_regra(pares),
        "sobreposicao_fontes": sobreposicao_fontes(golden),
        "tamanho_grupos": tamanho_grupos(golden),
        "ganho_sobrevivencia": ganho_sobrevivencia(padronizados, golden),
        "perfil_faixa_genero": perfil_faixa_genero(golden),
        "clientes_por_uf": clientes_por_uf(golden),
    }
