"""Relatório em Markdown gerado a cada execução (output/relatorio.md)."""

from __future__ import annotations

import pandas as pd

from src.config import OUTPUT_DIR
from src.utils import configurar_logger, df_para_markdown, formatar_br

log = configurar_logger("report")


def _fluxo(brutos: pd.DataFrame, rejeitados: pd.DataFrame, golden: pd.DataFrame, marketing: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([
        ("Registros brutos (CRM + App + Lojas)", len(brutos)),
        ("Registros rejeitados (teste / sem identificação)", len(rejeitados)),
        ("Registros padronizados", len(brutos) - len(rejeitados)),
        ("Clientes únicos (golden record)", len(golden)),
        ("Registros duplicados eliminados", len(brutos) - len(rejeitados) - len(golden)),
        ("Clientes elegíveis para marketing (opt-in + e-mail)", len(marketing)),
    ], columns=["Etapa", "Quantidade"])


def gerar_relatorio(brutos, rejeitados, golden, marketing, analises, validacoes, avaliacao) -> None:
    contagem_fontes = brutos["origem"].value_counts().reindex(["crm", "app", "loja"])
    partes = [
        "# Relatório de consolidação de clientes\n",
        "_Gerado automaticamente por `python main.py`._\n",
        "## 1. Visão geral\n",
        f"Fontes: CRM {formatar_br(int(contagem_fontes['crm']))} · App {formatar_br(int(contagem_fontes['app']))}"
        f" · Lojas {formatar_br(int(contagem_fontes['loja']))} registros.\n",
        df_para_markdown(_fluxo(brutos, rejeitados, golden, marketing)) + "\n",
        "## 2. Qualidade das fontes\n",
        "### Preenchimento bruto (antes da limpeza)\n",
        df_para_markdown(analises["completude_bruta_por_fonte"], casas=1) + "\n",
        "### Valores válidos após a padronização\n",
        "![Qualidade por fonte](charts/01_qualidade_por_fonte.png)\n",
        df_para_markdown(analises["qualidade_por_fonte"], casas=1) + "\n",
        "### Situação do CPF\n",
        df_para_markdown(analises["status_cpf_por_fonte"]) + "\n",
        "## 3. Correções automáticas\n",
        "![Correções](charts/02_correcoes_por_fonte.png)\n",
        df_para_markdown(analises["correcoes_por_fonte"]) + "\n",
        "## 4. Deduplicação\n",
        "### Pares encontrados por regra\n",
        df_para_markdown(analises["pares_por_regra"], casas=3) + "\n",
    ]
    if avaliacao is not None:
        partes += [
            "### Avaliação contra o gabarito\n",
            "![Estratégias](charts/03_estrategias_deduplicacao.png)\n",
            df_para_markdown(avaliacao["avaliacao_deduplicacao"]) + "\n",
        ]
    partes += [
        "### Sobreposição entre fontes\n",
        "![Sobreposição](charts/04_sobreposicao_fontes.png)\n",
        df_para_markdown(analises["sobreposicao_fontes"], casas=1) + "\n",
        df_para_markdown(analises["tamanho_grupos"]) + "\n",
        "## 5. Golden record\n",
        "![Ganho de sobrevivência](charts/05_ganho_sobrevivencia.png)\n",
        df_para_markdown(analises["ganho_sobrevivencia"], casas=1) + "\n",
    ]
    if avaliacao is not None:
        partes += ["### Acurácia por campo (versus dado real atual)\n",
                   df_para_markdown(avaliacao["avaliacao_golden_record"]) + "\n"]
    partes += [
        "## 6. Validações\n",
        f"**{int(validacoes['passou'].sum())} de {len(validacoes)} regras passaram**; "
        f"todas as falhas restantes são alertas.\n" if validacoes.query("severidade == 'critica'")["passou"].all()
        else "**Há regras críticas com falha.**\n",
        df_para_markdown(validacoes) + "\n",
        "## 7. Perfil da base consolidada\n",
        "![Perfil](charts/06_perfil_clientes.png)\n",
        df_para_markdown(analises["perfil_faixa_genero"], casas=1) + "\n",
        df_para_markdown(analises["clientes_por_uf"], casas=1) + "\n",
    ]
    caminho = OUTPUT_DIR / "relatorio.md"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text("\n".join(partes), encoding="utf-8")
    log.info("relatório salvo em output/%s", caminho.name)
