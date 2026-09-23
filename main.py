"""
Orquestrador: consolida os cadastros de clientes das três fontes.

    extração -> padronização -> deduplicação -> golden record
             -> validação -> avaliação -> exportação -> relatório e gráficos

Uso:
    python main.py
"""

from __future__ import annotations

import time

from src.analyze import gerar_analises
from src.deduplicate import deduplicar
from src.evaluate import avaliar
from src.extract import extrair_registros
from src.golden_record import montar_golden_record
from src.load import exportar_dados, exportar_relatorios
from src.report import gerar_relatorio
from src.standardize import padronizar_registros
from src.utils import configurar_logger
from src.validate import garantir_qualidade, validar
from src.visualize import gerar_graficos

log = configurar_logger("pipeline")


def executar_pipeline(exportar: bool = True) -> dict:
    inicio = time.perf_counter()

    log.info("1/7 Extração")
    brutos = extrair_registros()

    log.info("2/7 Padronização")
    padronizados, rejeitados = padronizar_registros(brutos)

    log.info("3/7 Deduplicação")
    registros, pares = deduplicar(padronizados)

    log.info("4/7 Golden record")
    golden = montar_golden_record(registros)

    log.info("5/7 Validação")
    validacoes = validar(golden, registros)
    garantir_qualidade(validacoes)  # interrompe aqui se alguma regra crítica falhar

    log.info("6/7 Avaliação contra o gabarito e métricas")
    avaliacao = avaliar(padronizados, registros, golden)
    analises = gerar_analises(brutos, registros, pares, golden)

    if exportar:
        log.info("7/7 Exportação, relatório e gráficos")
        marketing = exportar_dados(golden, registros, rejeitados)
        exportar_relatorios({**analises, **(avaliacao or {}), "validacoes": validacoes})
        gerar_relatorio(brutos, rejeitados, golden, marketing, analises, validacoes, avaliacao)
        gerar_graficos(analises, avaliacao)

    log.info("Pipeline concluído em %.1fs", time.perf_counter() - inicio)
    return {"registros": registros, "golden": golden, "rejeitados": rejeitados, "pares": pares,
            "validacoes": validacoes, "avaliacao": avaliacao, "analises": analises}


if __name__ == "__main__":
    executar_pipeline()
