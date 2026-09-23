"""
Padronização: transforma os registros do esquema comum em registros limpos e
comparáveis, campo a campo.

Toda correção automática gera uma coluna `corr_*` (True/False). Isso permite
contar, por fonte, quantos valores foram consertados e auditar cada caso.
Valores sem conserto seguro viram nulos, nunca são "inventados".
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import DATA_REFERENCIA, IDADE_MAXIMA, IDADE_MINIMA
from src.mappings import (
    BOOLEANOS,
    CIDADES_ABREVIADAS,
    DOMINIOS_CORRIGIDOS,
    EMAILS_PLACEHOLDER,
    GENEROS,
    REGEX_NOME_INVALIDO,
    REGEX_TITULO,
    TIPOS_LOGRADOURO,
    UF_POR_NOME,
)
from src.utils import (
    chave_texto,
    configurar_logger,
    grafia_mais_frequente,
    mapear,
    normalizar_espacos,
    parse_data_mista,
    remover_acentos,
    separar_rejeitados,
    titulo_pt,
)
from src.validators import cep_valido, cpf_valido, email_valido, telefone_valido

log = configurar_logger("standardize")

FORMATOS_DATA = ["%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]


def _digitos(serie: pd.Series) -> pd.Series:
    return serie.astype("string").str.replace(r"\D", "", regex=True).replace("", pd.NA)


# --------------------------------------------------------------------------- #
# Nome
# --------------------------------------------------------------------------- #
def corrigir_mojibake(serie: pd.Series) -> tuple[pd.Series, pd.Series]:
    """'JoÃ£o' (UTF-8 lido como latin-1) -> 'João', desfazendo a decodificação errada."""
    def reverter(texto: str) -> str:
        try:
            return texto.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return texto

    # "ASSUNÇÃO" também contém "Ã", mas não é mojibake: a reversão falha e o texto
    # fica igual. Só conta como correção quando o texto realmente mudou.
    suspeito = serie.str.contains("Ã|Â", na=False)
    corrigido = serie.mask(suspeito, serie[suspeito].map(reverter))
    return corrigido, (corrigido != serie).fillna(False)


def reacentuar(nomes: pd.Series, minimo_ocorrencias: int = 3) -> tuple[pd.Series, pd.Series]:
    """
    Restaura acentos perdidos pelo sistema legado ("Brandao" -> "Brandão") usando um
    vocabulário aprendido da própria base: para cada palavra sem acento, a grafia
    acentuada mais frequente, desde que apareça pelo menos `minimo_ocorrencias` vezes.
    Acento não aparece por acaso, então basta ele existir em outras fontes.
    """
    palavras = nomes.str.split(" ").explode().rename("palavra").reset_index()
    palavras["chave"] = remover_acentos(palavras["palavra"]).str.lower()
    acentuadas = palavras[palavras["palavra"] != remover_acentos(palavras["palavra"])]
    contagem = acentuadas.groupby("chave")["palavra"].agg(["size", lambda s: s.mode().iat[0]])
    vocabulario = contagem.loc[contagem["size"] >= minimo_ocorrencias].iloc[:, 1]

    palavras["palavra"] = palavras["chave"].map(vocabulario).fillna(palavras["palavra"])
    reacentuado = palavras.groupby("index")["palavra"].agg(" ".join).reindex(nomes.index)
    reacentuado = reacentuado.fillna(nomes).astype("string")
    return reacentuado, (reacentuado != nomes).fillna(False)


def padronizar_nome(serie: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    nome, mojibake = corrigir_mojibake(normalizar_espacos(serie))
    nome = titulo_pt(nome.str.replace(REGEX_TITULO, "", regex=True))
    nome, reacentuado = reacentuar(nome)
    chave = chave_texto(nome).str.replace(".", "", regex=False)
    return nome, chave, mojibake, reacentuado


# --------------------------------------------------------------------------- #
# CPF
# --------------------------------------------------------------------------- #
def padronizar_cpf(serie: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Devolve (cpf válido ou NA, status, zeros_restaurados).

    - notação científica (1,23457E+10) perdeu dígitos: irrecuperável -> 'ilegivel'
    - 9 ou 10 dígitos: CPF salvo como número perdeu zeros à esquerda -> zfill(11).
      Se o palpite estiver errado, os dígitos verificadores reprovam o resultado.
    """
    texto = serie.astype("string").str.strip()
    cientifico = texto.str.upper().str.contains("E+", regex=False, na=False)
    digitos = _digitos(texto).mask(cientifico)
    restaurado = digitos.str.len().between(9, 10).fillna(False)
    digitos = digitos.mask(restaurado, digitos.str.zfill(11))
    valido = cpf_valido(digitos)
    status = np.select(
        [digitos.isna() & ~cientifico, cientifico, valido],
        ["ausente", "ilegivel", "valido"], default="invalido",
    )
    return digitos.where(valido), pd.Series(status, index=serie.index), restaurado & valido


# --------------------------------------------------------------------------- #
# Contatos
# --------------------------------------------------------------------------- #
def padronizar_email(serie: pd.Series) -> tuple[pd.Series, pd.Series]:
    email = normalizar_espacos(serie).str.lower().str.replace(" ", "", regex=False)
    email = email.mask(email.isin(EMAILS_PLACEHOLDER))
    dominio_correto = email.str.split("@").str[-1].map(DOMINIOS_CORRIGIDOS)
    corrigir = dominio_correto.notna() & email.str.count("@").eq(1)
    email = email.mask(corrigir, email.str.replace(r"@.*$", "@", regex=True) + dominio_correto)
    return email.where(email_valido(email)), corrigir.fillna(False)


def normalizar_digitos_telefone(serie: pd.Series) -> pd.Series:
    """Só dígitos, sem DDI (55) e sem o 0 de longa distância (0 + DDD)."""
    d = _digitos(serie)
    d = d.mask(d.str.len().isin([12, 13]) & d.str.startswith("55"), d.str[2:])
    return d.mask(d.str.len().isin([11, 12]) & d.str.startswith("0"), d.str[1:])


def padronizar_telefone(serie: pd.Series, ddd_provavel: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    - sem DDD (8 ou 9 dígitos): usa o DDD mais comum da cidade do cliente
    - celular antigo com 8 dígitos (DDD + [6-9] + 7): acrescenta o 9 (regra da Anatel)
    """
    d = normalizar_digitos_telefone(serie)
    sem_ddd = d.str.len().isin([8, 9]).fillna(False) & ddd_provavel.notna()
    d = d.mask(sem_ddd, ddd_provavel + d)
    sem_nono = (d.str.len().eq(10) & d.str[2].isin(list("6789"))).fillna(False)
    d = d.mask(sem_nono, d.str[:2] + "9" + d.str[2:])
    valido = telefone_valido(d)
    return d.where(valido), sem_ddd & valido, sem_nono & valido


def padronizar_cep(serie: pd.Series) -> tuple[pd.Series, pd.Series]:
    d = _digitos(serie)
    restaurado = d.str.len().eq(7).fillna(False)  # salvo como número: perdeu o zero à esquerda
    d = d.mask(restaurado, d.str.zfill(8))
    valido = cep_valido(d)
    return d.where(valido), restaurado & valido


# --------------------------------------------------------------------------- #
# Localização e endereço
# --------------------------------------------------------------------------- #
def padronizar_cidade_uf(cidade: pd.Series, uf: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    texto = normalizar_espacos(cidade)
    # "Campinas - SP": separa a UF que veio grudada na cidade
    partes = texto.str.extract(r"^(?P<cidade>.+?)\s*-\s*(?P<uf>[A-Za-z]{2})$")
    texto = partes["cidade"].fillna(texto)
    abreviada = mapear(texto, CIDADES_ABREVIADAS)
    cidade_limpa = grafia_mais_frequente(titulo_pt(abreviada.fillna(texto)))

    uf_limpa = mapear(uf, UF_POR_NOME).fillna(partes["uf"].str.upper())
    # UF ausente: a UF mais comum daquela cidade na própria base
    uf_da_cidade = (
        pd.DataFrame({"cidade": cidade_limpa, "uf": uf_limpa}).dropna()
        .groupby("cidade")["uf"].agg(lambda s: s.mode().iat[0])
    )
    uf_limpa = uf_limpa.fillna(cidade_limpa.map(uf_da_cidade))
    return cidade_limpa, uf_limpa, abreviada.notna()


def separar_endereco(endereco: pd.Series) -> pd.DataFrame:
    """'R. das Flores, nº 123 - Apto 12' -> logradouro, numero, complemento."""
    return normalizar_espacos(endereco).str.extract(
        r"(?i)^(?P<logradouro>[^,]+),\s*(?:(?:nº|n°|no|n\.)\s*)?(?P<numero>\d+|s/?n)?\s*(?:-\s*(?P<complemento>.+))?$"
    )


def padronizar_logradouro(serie: pd.Series) -> pd.Series:
    """Expande o tipo abreviado (R., Av, Pç.) e corrige a caixa do nome da via."""
    texto = titulo_pt(serie).str.replace(r"\b(Ii|Iii|Iv|Xv)\b", lambda m: m.group(0).upper(), regex=True)
    tipo = mapear(texto.str.extract(r"^(\S+)\s", expand=False), TIPOS_LOGRADOURO)
    resto = texto.str.replace(r"^\S+\s+", "", regex=True)
    return (tipo + " " + resto).fillna(texto)


def padronizar_numero(serie: pd.Series) -> pd.Series:
    numero = normalizar_espacos(serie).str.upper()
    return numero.mask(numero.isin(["SN", "S/N", "S N"]), "S/N")


# --------------------------------------------------------------------------- #
# Datas
# --------------------------------------------------------------------------- #
def padronizar_nascimento(serie: pd.Series) -> tuple[pd.Series, pd.Series]:
    nascimento = parse_data_mista(serie, FORMATOS_DATA, formatos_ano_2_digitos=["%d/%m/%y"])
    idade = (DATA_REFERENCIA - nascimento).dt.days / 365.25
    implausivel = nascimento.notna() & ~idade.between(IDADE_MINIMA, IDADE_MAXIMA)  # inclui 01/01/1900
    return nascimento.mask(implausivel), implausivel


# --------------------------------------------------------------------------- #
def padronizar_registros(registros: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aplica todas as regras e devolve (registros_padronizados, rejeitados)."""
    df = registros.copy()

    df["nome"], df["chave_nome"], df["corr_nome_mojibake"], df["corr_nome_reacentuado"] = padronizar_nome(df["nome"])
    df["cpf"], df["cpf_status"], df["corr_cpf_zeros_restaurados"] = padronizar_cpf(df["cpf"])
    df["email"], df["corr_email_dominio"] = padronizar_email(df["email"])
    df["data_nascimento"], df["corr_nascimento_implausivel"] = padronizar_nascimento(df["data_nascimento"])
    df["data_atualizacao"] = parse_data_mista(df["data_atualizacao"], FORMATOS_DATA)
    df["genero"] = mapear(df["genero"], GENEROS)
    df["opt_in_marketing"] = mapear(df["opt_in_marketing"], BOOLEANOS).astype("boolean")

    df["cidade"], df["uf"], df["corr_cidade_apelido"] = padronizar_cidade_uf(df["cidade"], df["uf"])
    df["cep"], df["corr_cep_zero_restaurado"] = padronizar_cep(df["cep"])

    # O CRM guarda o endereço em um único texto; o app já separa os campos.
    partes = separar_endereco(df["endereco"])
    df["logradouro"] = padronizar_logradouro(df["logradouro"].fillna(partes["logradouro"]))
    df["numero"] = padronizar_numero(df["numero"].fillna(partes["numero"]))
    df["complemento"] = titulo_pt(df["complemento"].fillna(partes["complemento"]))
    df["bairro"] = titulo_pt(df["bairro"])

    # DDD provável = DDD mais comum entre os telefones completos da mesma cidade
    completos = normalizar_digitos_telefone(df["telefone"])
    ddd_da_cidade = (
        pd.DataFrame({"cidade": df["cidade"], "ddd": completos.where(completos.str.len() >= 10).str[:2]})
        .dropna().groupby("cidade")["ddd"].agg(lambda s: s.mode().iat[0])
    )
    df["telefone"], df["corr_telefone_ddd_inferido"], df["corr_telefone_nono_digito"] = padronizar_telefone(
        df["telefone"], df["cidade"].map(ddd_da_cidade).astype("string")
    )
    df["tipo_telefone"] = np.where(df["telefone"].str[2].eq("9").fillna(False), "celular",
                                   np.where(df["telefone"].notna(), "fixo", None))

    df = df.drop(columns="endereco")
    df, rej_teste = separar_rejeitados(
        df, df["chave_nome"].str.fullmatch(REGEX_NOME_INVALIDO, na=True), "registro_de_teste_ou_generico"
    )
    sem_identificacao = df[["cpf", "email", "telefone", "data_nascimento"]].isna().all(axis=1)
    df, rej_sem_id = separar_rejeitados(df, sem_identificacao, "sem_dados_de_identificacao")

    rejeitados = pd.concat([rej_teste, rej_sem_id])
    log.info("%d registros padronizados | %d rejeitados", len(df), len(rejeitados))
    for coluna in df.filter(like="corr_").columns:
        log.info("  %-32s %5d correções", coluna, df[coluna].sum())
    return df.reset_index(drop=True), rejeitados
