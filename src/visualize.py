"""
Visualizações: cada gráfico responde a uma pergunta sobre a qualidade dos dados
ou sobre o resultado da consolidação.

Paleta categórica com ordem fixa (validada para daltonismo); cada fonte tem
sempre a mesma cor em todos os gráficos.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from src.config import CHARTS_DIR, ROOT_DIR  # noqa: E402
from src.utils import configurar_logger, formatar_br  # noqa: E402

log = configurar_logger("visualize")

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
CINZA = "#b5b3ab"
TINTA, TINTA_2, TINTA_3 = "#0b0b0b", "#52514e", "#898781"
GRADE, EIXO, SUPERFICIE = "#e1e0d9", "#c3c2b7", "#fcfcfb"
RAMPA_AZUL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

FONTES = {"crm": ("CRM (legado)", SERIES[0]), "app": ("App", SERIES[1]), "loja": ("Lojas (Excel)", SERIES[2])}

plt.rcParams.update({
    "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE, "savefig.facecolor": SUPERFICIE,
    "axes.edgecolor": EIXO, "axes.labelcolor": TINTA_2, "axes.titlecolor": TINTA,
    "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlepad": 24,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRADE, "grid.linewidth": 0.6,
    "xtick.color": TINTA_3, "ytick.color": TINTA_3, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "text.color": TINTA, "legend.frameon": False, "legend.fontsize": 9, "font.family": "sans-serif",
})

pct = FuncFormatter(lambda v, _: f"{v:.0f}%")


def _subtitulo(ax, texto: str) -> None:
    ax.text(0, 1.02, texto, transform=ax.transAxes, fontsize=9, color=TINTA_2, va="bottom")


def _salvar(fig, nome: str) -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / nome, dpi=150)
    plt.close(fig)


def _barras_horizontais(ax) -> None:
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)


# --------------------------------------------------------------------------- #
def grafico_qualidade_por_fonte(qualidade: pd.DataFrame) -> None:
    matriz = qualidade.set_index("campo")[list(FONTES)]
    fig, ax = plt.subplots(figsize=(8, 5))
    mapa = LinearSegmentedColormap.from_list("azul", RAMPA_AZUL)
    mapa.set_bad("#f0efec")  # campo que a fonte não coleta: cinza neutro, fora da escala
    valores = np.ma.masked_equal(matriz.to_numpy(), 0)
    ax.imshow(valores, aspect="auto", cmap=mapa, vmin=50, vmax=100)
    for (i, j), valor in np.ndenumerate(matriz.to_numpy()):
        ax.text(j, i, f"{valor:.0f}%" if valor > 0 else "não coleta", ha="center", va="center", fontsize=9,
                color="white" if valor >= 75 else TINTA_2)
    ax.set_xticks(range(len(FONTES)), [FONTES[f][0] for f in matriz.columns])
    ax.set_yticks(range(len(matriz)), matriz.index)
    ax.tick_params(length=0)
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("Registros com valor válido, por fonte")
    _subtitulo(ax, "Após a padronização; ausente ou irrecuperável = inválido · cores de 50% a 100%")
    _salvar(fig, "01_qualidade_por_fonte.png")


def grafico_correcoes(correcoes: pd.DataFrame) -> None:
    rotulos = {
        "nome_reacentuado": "Acentos restaurados no nome", "telefone_nono_digito": "9º dígito no celular",
        "telefone_ddd_inferido": "DDD inferido pela cidade", "email_dominio": "Domínio de e-mail corrigido",
        "cep_zero_restaurado": "Zero à esquerda no CEP", "cidade_apelido": "Apelido de cidade (BH, Sampa)",
        "cpf_zeros_restaurados": "Zeros à esquerda no CPF", "nome_mojibake": "Mojibake no nome (JoÃ£o)",
        "nascimento_implausivel": "Nascimento implausível anulado",
    }
    dados = correcoes.iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 5))
    base = np.zeros(len(dados))
    for fonte, (rotulo, cor) in FONTES.items():
        ax.barh(dados["correcao"].map(rotulos), dados[fonte], left=base, color=cor, label=rotulo,
                height=0.65, edgecolor=SUPERFICIE, linewidth=1, zorder=2)
        base += dados[fonte].to_numpy()
    for y, total in enumerate(dados["total"]):
        ax.text(total, y, f"  {formatar_br(int(total))}", va="center", fontsize=8.5, color=TINTA_2)
    ax.set_xlim(0, dados["total"].max() * 1.12)
    _barras_horizontais(ax)
    ax.set_title("Correções automáticas aplicadas")
    _subtitulo(ax, "Quantidade de registros corrigidos, por fonte")
    ax.legend(loc="lower right")
    _salvar(fig, "02_correcoes_por_fonte.png")


def grafico_estrategias(avaliacao: pd.DataFrame) -> None:
    rotulos = ["Só CPF", "+ e-mail\ne nome", "+ telefone\ne nome", "+ nascimento\ne nome"]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    barras = ax.bar(rotulos[:len(avaliacao)], avaliacao["recall_pct"], color=SERIES[0], width=0.6, zorder=2)
    for barra, (_, linha) in zip(barras, avaliacao.iterrows()):
        ax.text(barra.get_x() + barra.get_width() / 2, barra.get_height() + 1,
                f"{formatar_br(linha['recall_pct'], 1)}%\n{formatar_br(int(linha['clientes_encontrados']))} clientes",
                ha="center", va="bottom", fontsize=8.5, color=TINTA_2)
    ax.set_ylim(0, 115)
    ax.set_yticks(range(0, 101, 20))
    ax.yaxis.set_major_formatter(pct)
    ax.set_title("Recall da deduplicação por estratégia")
    _subtitulo(ax, f"Precisão de {formatar_br(avaliacao['precisao_pct'].min(), 1)}% em todas · "
                   f"{formatar_br(int(avaliacao['pessoas_reais'].iat[0]))} pessoas reais no gabarito")
    _salvar(fig, "03_estrategias_deduplicacao.png")


def grafico_sobreposicao(sobreposicao: pd.DataFrame) -> None:
    nomes = {f: FONTES[f][0].split(" ")[0] for f in FONTES}
    dados = sobreposicao.iloc[::-1].assign(
        rotulo=lambda d: d["fontes"].str.split(", ").map(lambda fs: " + ".join(nomes[f] for f in fs)))
    fig, ax = plt.subplots(figsize=(8, 4.3))
    barras = ax.barh(dados["rotulo"], dados["clientes"], color=SERIES[0], height=0.6, zorder=2)
    for barra, (_, linha) in zip(barras, dados.iterrows()):
        ax.text(barra.get_width(), barra.get_y() + barra.get_height() / 2,
                f"  {formatar_br(int(linha['clientes']))} ({formatar_br(linha['pct'], 1)}%)",
                va="center", fontsize=8.5, color=TINTA_2)
    ax.set_xlim(0, dados["clientes"].max() * 1.25)
    _barras_horizontais(ax)
    ax.set_title("Em quais fontes cada cliente aparece")
    _subtitulo(ax, "Clientes únicos após a deduplicação")
    _salvar(fig, "04_sobreposicao_fontes.png")


def grafico_ganho_sobrevivencia(ganho: pd.DataFrame) -> None:
    dados = ganho.iloc[::-1]
    y = np.arange(len(dados))
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.barh(y + 0.19, dados["cadastro_final_pct"], height=0.36, color=SERIES[0], label="Cadastro final (golden record)", zorder=2)
    ax.barh(y - 0.19, dados["so_registro_mais_recente_pct"], height=0.36, color=CINZA,
            label="Só o registro mais recente", zorder=2)
    for yi, (_, linha) in zip(y, dados.iterrows()):
        ax.text(linha["cadastro_final_pct"], yi + 0.19, f"  +{formatar_br(linha['ganho_pp'], 1)} p.p.",
                va="center", fontsize=8.5, color=TINTA_2)
    ax.set_yticks(y, dados["campo"])
    ax.set_xlim(0, 112)
    ax.xaxis.set_major_formatter(pct)
    _barras_horizontais(ax)
    ax.set_title("Completude do cadastro: ganho das regras de sobrevivência")
    _subtitulo(ax, "% de clientes com o campo preenchido")
    ax.legend(loc="lower left", ncol=2, bbox_to_anchor=(0, -0.2))
    _salvar(fig, "05_ganho_sobrevivencia.png")


def grafico_perfil(perfil: pd.DataFrame) -> None:
    grupos = [("F", "Feminino", SERIES[0]), ("M", "Masculino", SERIES[1]), ("Não informado", "Não informado", CINZA)]
    x = np.arange(len(perfil))
    largura = 0.27
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for i, (coluna, rotulo, cor) in enumerate(grupos):
        ax.bar(x + (i - 1) * largura, perfil[coluna], width=largura, color=cor, label=rotulo, zorder=2)
    ax.set_xticks(x, perfil["faixa_etaria"].astype(str))
    ax.set_xlabel("Faixa etária")
    ax.set_title("Clientes por faixa etária e gênero")
    ax.legend(loc="upper right", ncol=3)
    _salvar(fig, "06_perfil_clientes.png")


def gerar_graficos(analises: dict[str, pd.DataFrame], avaliacao: dict[str, pd.DataFrame] | None) -> None:
    grafico_qualidade_por_fonte(analises["qualidade_por_fonte"])
    grafico_correcoes(analises["correcoes_por_fonte"])
    if avaliacao is not None:
        grafico_estrategias(avaliacao["avaliacao_deduplicacao"])
    grafico_sobreposicao(analises["sobreposicao_fontes"])
    grafico_ganho_sobrevivencia(analises["ganho_sobrevivencia"])
    grafico_perfil(analises["perfil_faixa_genero"])
    log.info("gráficos salvos em %s", CHARTS_DIR.relative_to(ROOT_DIR))
