"""
Dicionários de padronização (de-para).

As chaves estão no formato de `utils.chave_texto` (minúsculas, sem acento,
sem espaços extras). Valores fora dos mapas viram nulos e aparecem nos
relatórios, o que ajuda a descobrir variações novas.
"""

# Erros de digitação comuns em domínios de e-mail
DOMINIOS_CORRIGIDOS = {
    "gmial.com": "gmail.com", "gmail.con": "gmail.com", "gmai.com": "gmail.com", "gmail.com.br": "gmail.com",
    "hotmial.com": "hotmail.com", "hotmail.con": "hotmail.com", "hotmal.com": "hotmail.com",
    "outlok.com": "outlook.com", "outlook.con": "outlook.com",
    "yahoo.com.bt": "yahoo.com.br", "yaho.com.br": "yahoo.com.br",
    "uol.com": "uol.com.br", "uol.combr": "uol.com.br",
    "bol.com": "bol.com.br", "bol.con.br": "bol.com.br",
}

# E-mails "genéricos" digitados para passar pela obrigatoriedade do campo
EMAILS_PLACEHOLDER = {"naotem@naotem.com", "sem@email.com", "teste@teste.com", "nao@tem.com"}

# Nomes que indicam registro de teste ou cliente genérico (não é uma pessoa)
REGEX_NOME_INVALIDO = r"^(teste( sistema)?|cliente balcao|consumidor final|nao informado|x+)$"

REGEX_TITULO = r"(?i)^(sr|sra|srta|dr|dra)\.?\s+"

GENEROS = {"m": "M", "masculino": "M", "f": "F", "feminino": "F"}

BOOLEANOS = {
    "s": True, "sim": True, "true": True, "1": True, "y": True,
    "n": False, "nao": False, "false": False, "0": False,
}

UFS_VALIDAS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}
UF_POR_NOME = {
    "sao paulo": "SP", "rio de janeiro": "RJ", "minas gerais": "MG", "parana": "PR",
    "santa catarina": "SC", "rio grande do sul": "RS", "bahia": "BA", "pernambuco": "PE",
    "goias": "GO", "distrito federal": "DF", "espirito santo": "ES", "ceara": "CE",
} | {uf.lower(): uf for uf in UFS_VALIDAS}

# Apelidos e siglas usados no campo cidade. "SP" e "RJ" no campo CIDADE foram
# interpretados como as capitais (decisão documentada no README).
CIDADES_ABREVIADAS = {
    "s. paulo": "São Paulo", "sp": "São Paulo", "sampa": "São Paulo",
    "bh": "Belo Horizonte", "b. horizonte": "Belo Horizonte",
    "rio": "Rio de Janeiro", "rj": "Rio de Janeiro",
    "poa": "Porto Alegre", "p. alegre": "Porto Alegre",
}

TIPOS_LOGRADOURO = {
    "r": "Rua", "r.": "Rua", "rua": "Rua",
    "av": "Avenida", "av.": "Avenida", "avenida": "Avenida",
    "tv.": "Travessa", "trav.": "Travessa", "travessa": "Travessa",
    "al": "Alameda", "al.": "Alameda", "alameda": "Alameda",
    "pc.": "Praça", "pca": "Praça", "praca": "Praça",
}
