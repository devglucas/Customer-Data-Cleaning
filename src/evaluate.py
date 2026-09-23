"""
Avaliação contra o gabarito (data/external).

Em um projeto real não existe gabarito; o equivalente é revisar manualmente
uma amostra de pares. Aqui, como os dados são sintéticos, sabemos qual pessoa
está por trás de cada registro e podemos MEDIR a qualidade do pipeline:

- deduplicação, avaliada por pares de registros:
    precisão = pares unidos corretamente / pares que o pipeline uniu
    recall   = pares unidos corretamente / pares que deveriam ser unidos
- contribuição de cada regra de match (estratégias acumuladas)
- acurácia de cada campo do golden record versus o dado verdadeiro atual
"""

from __future__ import annotations

import pandas as pd

from src.config import ARQUIVOS_GABARITO
from src.deduplicate import REGRAS, deduplicar
from src.utils import configurar_logger

log = configurar_logger("evaluate")

CAMPOS_AVALIADOS = ["nome", "cpf", "data_nascimento", "genero", "email", "telefone", "cidade", "uf", "cep",
                    "opt_in_marketing"]


def carregar_gabarito() -> tuple[pd.DataFrame, pd.DataFrame] | None:
    if not all(caminho.exists() for caminho in ARQUIVOS_GABARITO.values()):
        log.warning("gabarito não encontrado: avaliação ignorada")
        return None
    registros = pd.read_csv(ARQUIVOS_GABARITO["registros"], dtype="string")
    pessoas = pd.read_csv(ARQUIVOS_GABARITO["pessoas"], dtype="string").assign(
        data_nascimento=lambda d: pd.to_datetime(d["data_nascimento"]),
        opt_in_marketing=lambda d: d["opt_in"].map({"True": True, "False": False}),
    )
    return registros, pessoas


def _combinacoes_2(tamanhos: pd.Series) -> int:
    return int((tamanhos * (tamanhos - 1) // 2).sum())


def metricas_deduplicacao(registros: pd.DataFrame, gabarito_registros: pd.DataFrame) -> dict:
    m = registros.merge(gabarito_registros, on=["origem", "id_origem"], how="left", validate="one_to_one")
    previstos = _combinacoes_2(m.groupby("cliente_id").size())
    reais = _combinacoes_2(m.groupby("pessoa_id").size())
    corretos = _combinacoes_2(m.groupby(["cliente_id", "pessoa_id"]).size())
    precisao = corretos / previstos if previstos else 1.0
    recall = corretos / reais if reais else 1.0
    return {
        "pares_previstos": previstos, "pares_reais": reais, "pares_corretos": corretos,
        "precisao_pct": round(precisao * 100, 2), "recall_pct": round(recall * 100, 2),
        "f1_pct": round(2 * precisao * recall / (precisao + recall) * 100, 2),
        "clientes_encontrados": m["cliente_id"].nunique(), "pessoas_reais": m["pessoa_id"].nunique(),
        "pessoas_divididas_em_2_ou_mais_clientes": int((m.groupby("pessoa_id")["cliente_id"].nunique() > 1).sum()),
        "clientes_misturando_pessoas": int((m.groupby("cliente_id")["pessoa_id"].nunique() > 1).sum()),
    }


def comparar_estrategias(padronizados: pd.DataFrame, gabarito_registros: pd.DataFrame) -> pd.DataFrame:
    """Quanto cada regra acrescenta: roda a deduplicação com as regras acumuladas."""
    nomes = list(REGRAS)
    linhas = []
    for i in range(1, len(nomes) + 1):
        dedup, _ = deduplicar(padronizados, nomes[:i])
        linhas.append({"estrategia": " + ".join(nomes[:i]), **metricas_deduplicacao(dedup, gabarito_registros)})
    return pd.DataFrame(linhas)


def acuracia_golden(golden: pd.DataFrame, registros: pd.DataFrame,
                    gabarito_registros: pd.DataFrame, pessoas: pd.DataFrame) -> pd.DataFrame:
    # cada cliente é associado à pessoa real predominante no seu grupo
    pessoa_do_cliente = (
        registros.merge(gabarito_registros, on=["origem", "id_origem"])
        .groupby("cliente_id")["pessoa_id"].agg(lambda s: s.mode().iat[0])
    )
    comparacao = golden.assign(pessoa_id=golden["cliente_id"].map(pessoa_do_cliente)).merge(
        pessoas, on="pessoa_id", suffixes=("", "_real"))
    linhas = []
    for campo in CAMPOS_AVALIADOS:
        preenchido = comparacao[campo].notna()
        correto = (comparacao[campo].astype("string") == comparacao[f"{campo}_real"].astype("string")).fillna(False)
        linhas.append({
            "campo": campo,
            "preenchido_pct": round(preenchido.mean() * 100, 2),
            "correto_quando_preenchido_pct": round(correto[preenchido].mean() * 100, 2),
        })
    return pd.DataFrame(linhas)


def avaliar(padronizados: pd.DataFrame, registros: pd.DataFrame, golden: pd.DataFrame) -> dict[str, pd.DataFrame] | None:
    gabarito = carregar_gabarito()
    if gabarito is None:
        return None
    gabarito_registros, pessoas = gabarito
    estrategias = comparar_estrategias(padronizados, gabarito_registros)
    final = estrategias.iloc[-1]
    log.info("deduplicação: precisão %.2f%% | recall %.2f%% | F1 %.2f%%",
             final["precisao_pct"], final["recall_pct"], final["f1_pct"])
    return {
        "avaliacao_deduplicacao": estrategias,
        "avaliacao_golden_record": acuracia_golden(golden, registros, gabarito_registros, pessoas),
    }
