"""
Gerador de dados sintéticos da rede "Farmácias Bem Viver".

Cenário: a rede (sistema CRM legado) comprou a concorrente "Drogaria Popular"
(aplicativo próprio) e ainda tem lojas que cadastram clientes em planilhas Excel.
Uma mesma pessoa pode aparecer nas três fontes, e até duas vezes na mesma fonte,
escrita de formas diferentes e com dados desatualizados.

Arquivos gerados:
    data/raw/crm_clientes.csv        CSV ; em latin-1 (sistema legado)
    data/raw/app_cadastros.jsonl     JSON Lines com endereço aninhado
    data/raw/lojas_cadastros.xlsx    Excel, uma aba por loja, com título antes do cabeçalho

    data/external/gabarito_registros.csv   qual pessoa real está por trás de cada registro
    data/external/gabarito_pessoas.csv     dados verdadeiros e atuais de cada pessoa

O gabarito NÃO é usado pela limpeza: serve apenas para medir a qualidade da
deduplicação (precisão/recall) e do cadastro final. CPFs, nomes e contatos são
gerados aleatoriamente e não pertencem a pessoas reais.

Uso:
    python scripts/generate_data.py
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 7
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
EXTERNAL_DIR = ROOT / "data" / "external"

N_PESSOAS = 6000
HOJE = pd.Timestamp("2025-12-31")

# --------------------------------------------------------------------------- #
# Dados de referência
# --------------------------------------------------------------------------- #
NOMES_F = ["Ana", "Beatriz", "Camila", "Débora", "Fernanda", "Gabriela", "Helena", "Isabela", "Júlia",
           "Larissa", "Letícia", "Mariana", "Natália", "Patrícia", "Renata", "Sônia", "Tânia", "Vitória",
           "Aline", "Cecília", "Luíza", "Márcia", "Cláudia", "Lúcia", "Raquel", "Simone", "Priscila", "Joana"]
NOMES_M = ["André", "Bruno", "Caio", "Daniel", "Eduardo", "Fábio", "Gustavo", "Henrique", "João",
           "Lucas", "Márcio", "Mateus", "Otávio", "Paulo", "Rafael", "Sérgio", "Thiago", "Vinícius",
           "Antônio", "César", "Fernando", "José", "Luís", "Marcelo", "Rodrigo", "Wagner", "Leonardo", "Hélio"]
SOBRENOMES = ["Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira", "Alves", "Pereira", "Lima",
              "Gomes", "Costa", "Ribeiro", "Martins", "Carvalho", "Araújo", "Melo", "Barbosa", "Cardoso",
              "Rocha", "Dias", "Nascimento", "Andrade", "Moreira", "Nunes", "Marques", "Machado", "Mendes",
              "Freitas", "Conceição", "Guimarães", "Brandão", "Magalhães", "Assunção", "Peixoto"]
DOMINIOS = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.com.br", "uol.com.br", "bol.com.br"]
TYPOS_DOMINIO = {
    "gmail.com": ["gmial.com", "gmail.con", "gmai.com", "gmail.com.br"],
    "hotmail.com": ["hotmial.com", "hotmail.con", "hotmal.com"],
    "outlook.com": ["outlok.com", "outlook.con"],
    "yahoo.com.br": ["yahoo.com.bt", "yaho.com.br"],
    "uol.com.br": ["uol.com", "uol.combr"],
    "bol.com.br": ["bol.com", "bol.con.br"],
}
# cidade, UF, DDD, 1º dígito do CEP, peso
CIDADES = [
    ("São Paulo", "SP", "11", "0", 30), ("Guarulhos", "SP", "11", "0", 5), ("Campinas", "SP", "19", "1", 6),
    ("Santo André", "SP", "11", "0", 4), ("Ribeirão Preto", "SP", "16", "1", 3),
    ("Rio de Janeiro", "RJ", "21", "2", 12), ("Niterói", "RJ", "21", "2", 3),
    ("Belo Horizonte", "MG", "31", "3", 8), ("Juiz de Fora", "MG", "32", "3", 2),
    ("Curitiba", "PR", "41", "8", 6), ("Florianópolis", "SC", "48", "8", 3),
    ("Porto Alegre", "RS", "51", "9", 5), ("Salvador", "BA", "71", "4", 4),
    ("Recife", "PE", "81", "5", 3), ("Goiânia", "GO", "62", "7", 3), ("Brasília", "DF", "61", "7", 4),
]
ABREVIACOES_CIDADE = {"São Paulo": ["S. Paulo", "SP", "Sampa"], "Belo Horizonte": ["BH", "B. Horizonte"],
                      "Rio de Janeiro": ["Rio", "RJ"], "Porto Alegre": ["P. Alegre", "POA"]}
NOMES_UF = {"SP": "São Paulo", "RJ": "Rio de Janeiro", "MG": "Minas Gerais", "PR": "Paraná",
            "SC": "Santa Catarina", "RS": "Rio Grande do Sul", "BA": "Bahia", "PE": "Pernambuco",
            "GO": "Goiás", "DF": "Distrito Federal"}
TIPOS_LOGRADOURO = {"Rua": ["R.", "R", "RUA"], "Avenida": ["Av.", "AV", "Av"], "Travessa": ["Tv.", "Trav."],
                    "Alameda": ["Al.", "AL"], "Praça": ["Pç.", "Pca", "PRACA"]}
NOMES_RUA = ["das Flores", "Sete de Setembro", "Brasil", "São João", "XV de Novembro", "dos Andradas",
             "Santos Dumont", "Tiradentes", "Getúlio Vargas", "das Palmeiras", "Rio Branco", "Paulista",
             "Dom Pedro II", "da Liberdade", "Marechal Deodoro", "Presidente Vargas", "dos Ipês", "Castro Alves"]
BAIRROS = ["Centro", "Jardim América", "Vila Nova", "Boa Vista", "Santa Cecília", "Liberdade", "Bela Vista",
           "Jardim das Flores", "Vila Mariana", "Santo Antônio", "São José", "Parque Industrial"]
LOJAS = ["Loja Centro", "Loja Shopping", "Loja Bairro"]


def sem_acentos(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


def escolher(rng, opcoes):
    return opcoes[rng.integers(len(opcoes))]


# --------------------------------------------------------------------------- #
# Verdade
# --------------------------------------------------------------------------- #
def gerar_cpf(rng) -> str:
    base = rng.integers(0, 10, 9)
    dv1 = (base @ np.arange(10, 1, -1)) * 10 % 11 % 10
    dv2 = (np.append(base, dv1) @ np.arange(11, 1, -1)) * 10 % 11 % 10
    return "".join(map(str, [*base, dv1, dv2]))


def gerar_telefone(rng, ddd: str) -> str:
    return f"{ddd}9{rng.integers(6000, 9999)}{rng.integers(1000, 9999)}"


def gerar_email(rng, nome: str) -> str:
    partes = sem_acentos(nome).lower().split()
    usuario = escolher(rng, [f"{partes[0]}.{partes[-1]}", f"{partes[0]}{partes[-1]}", f"{partes[0]}_{partes[-1][:3]}"])
    return f"{usuario}{rng.integers(1, 999)}@{escolher(rng, DOMINIOS)}"


def gerar_endereco(rng, cep_digito: str) -> dict:
    tipo = str(rng.choice(list(TIPOS_LOGRADOURO), p=[0.62, 0.25, 0.04, 0.05, 0.04]))
    return {
        "tipo": tipo, "nome_rua": escolher(rng, NOMES_RUA),
        "numero": str(rng.integers(1, 3000)) if rng.random() > 0.03 else "S/N",
        "complemento": escolher(rng, ["Apto 12", "Apto 31", "Casa 2", "Bloco B Apto 104", "Fundos"]) if rng.random() < 0.3 else "",
        "bairro": escolher(rng, BAIRROS),
        "cep": f"{cep_digito}{rng.integers(1000000, 9999999)}",
    }


def gerar_pessoas(rng) -> pd.DataFrame:
    pesos = np.array([c[4] for c in CIDADES], dtype=float)
    cpfs = set()
    pessoas = []
    for i in range(N_PESSOAS):
        genero = "F" if rng.random() < 0.56 else "M"  # farmácia: público majoritariamente feminino
        primeiro = escolher(rng, NOMES_F if genero == "F" else NOMES_M)
        sobrenomes = [escolher(rng, SOBRENOMES) for _ in range(rng.choice([1, 2, 3], p=[0.3, 0.55, 0.15]))]
        nome = " ".join([primeiro, *sobrenomes])
        cidade, uf, ddd, cep_digito, _ = CIDADES[rng.choice(len(CIDADES), p=pesos / pesos.sum())]
        while (cpf := gerar_cpf(rng)) in cpfs:
            pass
        cpfs.add(cpf)
        idade_anos = min(18 + rng.gamma(shape=3.2, scale=8.5), 92)  # média ~45 anos, cauda longa
        idade_dias = int(idade_anos * 365.25)
        pessoas.append({
            "pessoa_id": f"PES-{i + 1:05d}", "nome": nome, "cpf": cpf, "genero": genero,
            "data_nascimento": (HOJE - pd.Timedelta(days=idade_dias)).normalize(),
            "email": gerar_email(rng, nome), "telefone": gerar_telefone(rng, ddd),
            "cidade": cidade, "uf": uf, "ddd": ddd, "cep_digito": cep_digito,
            **gerar_endereco(rng, cep_digito),
            "opt_in": bool(rng.random() < 0.55),
        })
    df = pd.DataFrame(pessoas)
    # famílias que compartilham o mesmo e-mail (armadilha para a deduplicação por e-mail)
    for a, b in rng.choice(len(df), size=(40, 2), replace=False):
        df.at[b, "email"] = df.at[a, "email"]
    return df


# --------------------------------------------------------------------------- #
# Registros: cada fonte registra a pessoa do seu jeito
# --------------------------------------------------------------------------- #
def planejar_registros(rng, pessoas: pd.DataFrame) -> pd.DataFrame:
    """Decide em quais fontes (e quantas vezes) cada pessoa aparece."""
    linhas = []
    for idx in range(len(pessoas)):
        fontes = [f for f, p in [("crm", 0.55), ("app", 0.45), ("loja", 0.20)] if rng.random() < p] or ["crm"]
        for fonte in fontes:
            repeticoes = 1 + int(rng.random() < {"crm": 0.05, "app": 0.03, "loja": 0.06}[fonte])
            linhas += [{"idx": idx, "fonte": fonte} for _ in range(repeticoes)]
    plano = pd.DataFrame(linhas)
    plano["atualizado_em"] = pd.Timestamp("2019-01-01") + pd.to_timedelta(
        rng.integers(0, (HOJE - pd.Timestamp("2019-01-01")).days, len(plano)), unit="D")
    # o registro mais recente de cada pessoa tem os dados atuais; os antigos podem estar desatualizados
    plano["mais_recente"] = plano.groupby("idx")["atualizado_em"].rank(method="first", ascending=False).eq(1)
    return plano


def sujar_nome(rng, nome: str) -> str:
    r = rng.random()
    if r < 0.05:  # erro de digitação: troca duas letras vizinhas
        i = rng.integers(1, len(nome) - 2)
        if nome[i] != " " and nome[i + 1] != " ":
            nome = nome[:i] + nome[i + 1] + nome[i] + nome[i + 2:]
    elif r < 0.09:  # abrevia um sobrenome do meio
        partes = nome.split()
        if len(partes) > 2:
            partes[1] = partes[1][0] + "."
            nome = " ".join(partes)
    elif r < 0.12:
        nome = escolher(rng, ["Sr. ", "Sra. ", "Dr. ", "Dra. "]) + nome
    if rng.random() < 0.08:
        nome = nome.replace(" ", "  ", 1) + " "
    return nome


def sujar_email(rng, email: str, desatualizado: bool) -> str | None:
    if desatualizado and rng.random() < 0.25:
        usuario, dominio = email.split("@")
        email = f"{usuario}{rng.integers(1, 99)}@{escolher(rng, DOMINIOS)}"
    r = rng.random()
    if r < 0.05:
        return None
    usuario, dominio = email.split("@")
    if r < 0.10:
        return f"{usuario}@{escolher(rng, TYPOS_DOMINIO[dominio])}"
    if r < 0.12:
        return escolher(rng, [email.replace("@", ""), email.replace("@", "@@"), f"{usuario}@"])
    if r < 0.20:
        return f" {email.upper()} "
    return email


def telefone_atual_ou_antigo(rng, pessoa, desatualizado: bool) -> str:
    if desatualizado and rng.random() < 0.25:
        return gerar_telefone(rng, pessoa["ddd"])
    return pessoa["telefone"]


def formatar_telefone(rng, tel: str, estilo_fonte: str) -> str | None:
    if rng.random() < 0.05:
        return None
    ddd, numero = tel[:2], tel[2:]
    if estilo_fonte == "crm" and rng.random() < 0.18:  # cadastro antigo: celular com 8 dígitos
        numero = numero[1:]
    if rng.random() < 0.06:  # sem DDD
        return numero if len(numero) == 8 else f"{numero[:5]}-{numero[5:]}"
    estilos = {
        "crm": [f"({ddd}) {numero[:-4]}-{numero[-4:]}", f"{ddd} {numero}", f"{ddd}{numero}"],
        "app": [f"+55{ddd}{numero}", f"+55 ({ddd}) {numero[:-4]}-{numero[-4:]}"],
        "loja": [f"{ddd} {numero[:-4]}-{numero[-4:]}", f"({ddd}){numero}", f"0{ddd}{numero}"],
    }[estilo_fonte]
    return escolher(rng, estilos)


def sujar_cidade(rng, cidade: str, uf: str) -> str:
    r = rng.random()
    if r < 0.10:
        return sem_acentos(cidade).upper()
    if r < 0.15 and cidade in ABREVIACOES_CIDADE:
        return escolher(rng, ABREVIACOES_CIDADE[cidade])
    if r < 0.20:
        return f"{cidade} - {uf}"
    if r < 0.25:
        return cidade.lower() + " "
    return cidade


def texto_logradouro(rng, end: dict) -> str:
    tipo = escolher(rng, [end["tipo"], *TIPOS_LOGRADOURO[end["tipo"]]]) if rng.random() < 0.6 else end["tipo"]
    return f"{tipo} {end['nome_rua']}"


def mojibake(texto: str) -> str:
    """Texto UTF-8 lido como latin-1 por uma integração antiga: 'João' -> 'JoÃ£o'."""
    return texto.encode("utf-8").decode("latin-1")


# ----------------------------- CRM (legado) -------------------------------- #
def registro_crm(rng, pessoa, desatualizado: bool, cod: int, atualizado_em) -> dict:
    nome = sujar_nome(rng, pessoa["nome"])
    nome = sem_acentos(nome).upper() if rng.random() < 0.7 else nome.upper()  # sistema antigo: CAIXA ALTA
    cpf = pessoa["cpf"]
    r = rng.random()
    if r < 0.40:
        cpf = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    elif r < 0.55:
        cpf = str(int(cpf))  # exportado como número: perde zeros à esquerda
    elif r < 0.57:
        cpf = f"{int(cpf):.5E}".replace(".", ",")  # passou pelo Excel: notação científica
    elif r < 0.59:
        cpf = cpf[:5] + str((int(cpf[5]) + 3) % 10) + cpf[6:]  # dígito digitado errado
    end = pessoa if not (desatualizado and rng.random() < 0.15) else {**pessoa, **gerar_endereco(rng, pessoa["cep_digito"])}
    numero = end["numero"]
    endereco = f"{texto_logradouro(rng, end)}, {escolher(rng, ['', 'nº ', 'N. '])}{numero}"
    if end["complemento"]:
        endereco += f" - {end['complemento']}"
    cep = end["cep"] if rng.random() < 0.5 else f"{end['cep'][:5]}-{end['cep'][5:]}"
    if rng.random() < 0.15:
        cep = str(int(end["cep"]))  # perde zero à esquerda
    nasc = pessoa["data_nascimento"].strftime("%d/%m/%Y") if rng.random() > 0.01 else "01/01/1900"
    return {
        "COD_CLIENTE": cod, "NOME_CLIENTE": nome, "CPF": cpf, "DT_NASC": nasc,
        "SEXO": pessoa["genero"] if rng.random() < 0.93 else escolher(rng, ["", "I", None]),
        "EMAIL": sujar_email(rng, pessoa["email"], desatualizado),
        "FONE": formatar_telefone(rng, telefone_atual_ou_antigo(rng, pessoa, desatualizado), "crm"),
        "ENDERECO": endereco.upper() if rng.random() < 0.5 else endereco,
        "BAIRRO": end["bairro"].upper(), "CIDADE": sujar_cidade(rng, pessoa["cidade"], pessoa["uf"]),
        "UF": escolher(rng, [pessoa["uf"], pessoa["uf"], pessoa["uf"].lower(), NOMES_UF[pessoa["uf"]]])
        if rng.random() > 0.03 else None,
        "CEP": cep, "ACEITA_MKT": ("S" if pessoa["opt_in"] else "N") if rng.random() > 0.1 else None,
        "DT_ATUALIZACAO": atualizado_em.strftime("%d/%m/%Y"),
    }


# ----------------------------- App (JSON Lines) ---------------------------- #
def registro_app(rng, pessoa, desatualizado: bool, atualizado_em) -> dict:
    nome = sujar_nome(rng, pessoa["nome"])
    r = rng.random()
    if r < 0.03:
        nome = mojibake(nome)
    elif r < 0.10:
        nome = nome.lower()
    end = pessoa if not (desatualizado and rng.random() < 0.15) else {**pessoa, **gerar_endereco(rng, pessoa["cep_digito"])}
    return {
        "id": f"usr_{rng.integers(0, 16 ** 8):08x}",
        "nome": nome,
        "cpf": pessoa["cpf"] if rng.random() > 0.12 else None,  # CPF era opcional no app
        "email": sujar_email(rng, pessoa["email"], desatualizado),
        "celular": formatar_telefone(rng, telefone_atual_ou_antigo(rng, pessoa, desatualizado), "app"),
        "nascimento": pessoa["data_nascimento"].strftime("%Y-%m-%d") if rng.random() > 0.08 else None,
        "genero": {"F": escolher(rng, ["feminino", "Feminino", "F"]),
                   "M": escolher(rng, ["masculino", "Masculino", "M"])}[pessoa["genero"]]
        if rng.random() > 0.1 else escolher(rng, ["prefiro não informar", None]),
        "endereco": {
            "logradouro": texto_logradouro(rng, end), "numero": end["numero"],
            "complemento": end["complemento"] or None, "bairro": end["bairro"],
            "cidade": sujar_cidade(rng, pessoa["cidade"], pessoa["uf"]),
            "uf": pessoa["uf"], "cep": end["cep"] if rng.random() < 0.7 else f"{end['cep'][:5]}-{end['cep'][5:]}",
        } if rng.random() > 0.15 else None,
        "marketing_opt_in": bool(pessoa["opt_in"]),
        "atualizado_em": atualizado_em.strftime("%Y-%m-%dT%H:%M:%S"),
    }


# ----------------------------- Lojas (Excel) ------------------------------- #
def registro_loja(rng, pessoa, desatualizado: bool, cod: int, atualizado_em) -> dict:
    nasc = pessoa["data_nascimento"]
    r = rng.random()
    if r < 0.60:
        nascimento = nasc.to_pydatetime()  # célula de data de verdade
    elif r < 0.80:
        nascimento = (nasc - pd.Timestamp("1899-12-30")).days  # número serial do Excel
    elif r < 0.95:
        nascimento = nasc.strftime("%d/%m/%y")  # texto com ano de 2 dígitos
    else:
        nascimento = None
    cpf = pessoa["cpf"]
    email = sujar_email(rng, pessoa["email"], desatualizado)
    if rng.random() < 0.08:
        email = escolher(rng, ["naotem@naotem.com", "sem@email.com", "nao possui", "-"])
    return {
        "Cód.": cod,
        "Nome": sujar_nome(rng, pessoa["nome"]),
        # CPF digitado como número na planilha: zeros à esquerda somem
        "CPF": int(cpf) if rng.random() < 0.7 else (f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if rng.random() < 0.85 else None),
        "Telefone": formatar_telefone(rng, telefone_atual_ou_antigo(rng, pessoa, desatualizado), "loja"),
        "Data Nascimento": nascimento,
        "E-mail": email,
        "Cidade": sujar_cidade(rng, pessoa["cidade"], pessoa["uf"]),
        "Aceita receber ofertas?": ("Sim" if pessoa["opt_in"] else "Não") if rng.random() > 0.25 else None,
        "Data Cadastro": atualizado_em.to_pydatetime(),
    }


def registros_invalidos_crm(rng, cod_inicial: int) -> list[dict]:
    """Registros de teste e 'clientes genéricos' que existem em todo sistema legado."""
    nomes = ["TESTE", "TESTE SISTEMA", "CLIENTE BALCAO", "CONSUMIDOR FINAL", "XXXXX", "NAO INFORMADO"]
    return [{
        "COD_CLIENTE": cod_inicial + i, "NOME_CLIENTE": escolher(rng, nomes),
        "CPF": escolher(rng, ["000.000.000-00", "111.111.111-11", "", "123.456.789-00"]),
        "DT_NASC": "01/01/1900", "SEXO": None, "EMAIL": escolher(rng, ["teste@teste.com", None]),
        "FONE": "(11) 0000-0000", "ENDERECO": "RUA TESTE, 0", "BAIRRO": "CENTRO", "CIDADE": "SAO PAULO",
        "UF": "SP", "CEP": "00000-000", "ACEITA_MKT": "N", "DT_ATUALIZACAO": "15/03/2019",
    } for i in range(14)]


# --------------------------------------------------------------------------- #
def main() -> None:
    rng = np.random.default_rng(SEED)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)

    pessoas = gerar_pessoas(rng)
    plano = planejar_registros(rng, pessoas).sample(frac=1, random_state=SEED).reset_index(drop=True)

    crm, app, lojas, gabarito = [], [], {loja: [] for loja in LOJAS}, []
    cod_crm = 100001
    for linha in plano.itertuples():
        pessoa = pessoas.iloc[linha.idx]
        desatualizado = not linha.mais_recente
        if linha.fonte == "crm":
            crm.append(registro_crm(rng, pessoa, desatualizado, cod_crm, linha.atualizado_em))
            gabarito.append(("crm", str(cod_crm), pessoa["pessoa_id"]))
            cod_crm += 1
        elif linha.fonte == "app":
            registro = registro_app(rng, pessoa, desatualizado, linha.atualizado_em)
            app.append(registro)
            gabarito.append(("app", registro["id"], pessoa["pessoa_id"]))
        else:
            loja = escolher(rng, LOJAS)
            cod = len(lojas[loja]) + 1
            lojas[loja].append(registro_loja(rng, pessoa, desatualizado, cod, linha.atualizado_em))
            gabarito.append(("loja", f"{loja}#{cod}", pessoa["pessoa_id"]))

    crm += registros_invalidos_crm(rng, cod_crm)
    pd.DataFrame(crm).sort_values("COD_CLIENTE").to_csv(
        RAW_DIR / "crm_clientes.csv", sep=";", index=False, encoding="latin-1")

    with open(RAW_DIR / "app_cadastros.jsonl", "w", encoding="utf-8") as f:
        for registro in sorted(app, key=lambda r: r["atualizado_em"]):
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")

    with pd.ExcelWriter(RAW_DIR / "lojas_cadastros.xlsx", engine="openpyxl") as writer:
        for loja, registros in lojas.items():
            df = pd.DataFrame(registros)
            df.to_excel(writer, sheet_name=loja, index=False, startrow=2)
            writer.sheets[loja]["A1"] = f"Cadastro de Clientes - {loja} (planilha mantida pela gerência)"

    pd.DataFrame(gabarito, columns=["origem", "id_origem", "pessoa_id"]).to_csv(
        EXTERNAL_DIR / "gabarito_registros.csv", index=False)
    colunas = ["pessoa_id", "nome", "cpf", "genero", "data_nascimento", "email", "telefone",
               "cidade", "uf", "cep", "opt_in"]
    pessoas[colunas].to_csv(EXTERNAL_DIR / "gabarito_pessoas.csv", index=False)

    print(f"Pessoas reais: {len(pessoas)} | registros: CRM {len(crm)}, App {len(app)}, "
          f"Lojas {sum(map(len, lojas.values()))}")
    for arquivo in sorted([*RAW_DIR.iterdir(), *EXTERNAL_DIR.iterdir()]):
        print(f"  {arquivo.relative_to(ROOT)!s:<40} {arquivo.stat().st_size / 1024:>8.1f} KB")


if __name__ == "__main__":
    main()
