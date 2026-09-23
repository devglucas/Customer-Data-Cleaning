import datetime as dt

import pandas as pd

from src.standardize import (
    padronizar_cep,
    padronizar_cidade_uf,
    padronizar_cpf,
    padronizar_email,
    padronizar_logradouro,
    padronizar_nascimento,
    padronizar_nome,
    padronizar_telefone,
    reacentuar,
    separar_endereco,
)


def test_nome_remove_titulo_corrige_mojibake_e_caixa():
    nome, chave, mojibake, _ = padronizar_nome(pd.Series(["SRA. MARIA  DA SILVA ", "JoÃ£o Souza", "ASSUNÇÃO LIMA"]))
    assert nome.tolist() == ["Maria da Silva", "João Souza", "Assunção Lima"]
    assert chave.tolist() == ["maria da silva", "joao souza", "assuncao lima"]
    assert mojibake.tolist() == [False, True, False]


def test_reacentuar_usa_vocabulario_da_propria_base():
    nomes = pd.Series(["Joao Brandao", "João Lima", "João Dias", "João Souza", "Ana Brandão", "Caio Conceicao"])
    resultado, alterado = reacentuar(nomes)
    # "João" aparece 3x com acento -> vocabulário; "Brandão" só 1x -> não é confiável ainda
    assert resultado.tolist() == ["João Brandao", "João Lima", "João Dias", "João Souza", "Ana Brandão", "Caio Conceicao"]
    assert alterado.tolist() == [True, False, False, False, False, False]


def test_cpf_formatos_e_status():
    entrada = pd.Series(["529.982.247-25", "1234567890", "5,29982E+10", "529.982.247-26", None])
    cpf, status, restaurado = padronizar_cpf(entrada)
    assert cpf.iat[0] == "52998224725"
    assert cpf.iat[1] == "01234567890" and restaurado.iat[1]  # zero à esquerda restaurado
    assert status.tolist() == ["valido", "valido", "ilegivel", "invalido", "ausente"]


def test_email_corrige_dominio_e_descarta_placeholder():
    email, corrigido = padronizar_email(pd.Series([" ANA@GMIAL.COM ", "sem@email.com", "ana@@gmail.com", "bia@uol.com.br"]))
    assert email.iat[0] == "ana@gmail.com" and corrigido.iat[0]
    assert email.iloc[1:3].isna().all()
    assert email.iat[3] == "bia@uol.com.br"


def test_telefone_ddi_nono_digito_e_ddd_inferido():
    telefones = pd.Series(["+55 (11) 98765-4321", "(21) 8765-4321", "98765-4321", "011987654321", "123"])
    ddd_cidade = pd.Series(["11", "21", "31", "11", "11"], dtype="string")
    tel, ddd_inferido, nono = padronizar_telefone(telefones, ddd_cidade)
    assert tel.iloc[:4].tolist() == ["11987654321", "21987654321", "31987654321", "11987654321"]
    assert nono.tolist() == [False, True, False, False, False]
    assert ddd_inferido.tolist() == [False, False, True, False, False]
    assert pd.isna(tel.iat[4])


def test_cep_restaura_zero():
    cep, restaurado = padronizar_cep(pd.Series(["01310-100", "1310100", "00000-000"]))
    assert cep.iloc[:2].tolist() == ["01310100", "01310100"]
    assert restaurado.tolist() == [False, True, False]
    assert pd.isna(cep.iat[2])


def test_cidade_com_uf_embutida_e_apelido():
    cidade = pd.Series(["Campinas - SP", "BH", "São Paulo", "SAO PAULO", "São Paulo"])
    uf = pd.Series([None, "minas gerais", "sp", None, "São Paulo"])
    cidade_limpa, uf_limpa, apelido = padronizar_cidade_uf(cidade, uf)
    assert cidade_limpa.tolist() == ["Campinas", "Belo Horizonte", "São Paulo", "São Paulo", "São Paulo"]
    assert uf_limpa.tolist() == ["SP", "MG", "SP", "SP", "SP"]  # 4º inferida pela cidade
    assert apelido.tolist() == [False, True, False, False, False]


def test_endereco_do_crm_e_logradouro():
    partes = separar_endereco(pd.Series(["R. DAS FLORES, Nº 123 - APTO 12", "AV DOM PEDRO II, 45", "PRACA BRASIL, S/N"]))
    assert partes["numero"].tolist() == ["123", "45", "S/N"]
    assert padronizar_logradouro(partes["logradouro"]).tolist() == ["Rua das Flores", "Avenida Dom Pedro II", "Praça Brasil"]


def test_nascimento_formatos_mistos_do_excel():
    entrada = pd.Series([dt.datetime(1985, 4, 12), 31149, "12/04/85", "01/01/1900", "12/04/2015"], dtype=object)
    nascimento, implausivel = padronizar_nascimento(entrada)
    assert (nascimento.iloc[:3] == pd.Timestamp("1985-04-12")).all()  # célula, serial e ano de 2 dígitos
    assert nascimento.iloc[3:].isna().all()  # 1900 é placeholder; 2015 = 10 anos
    assert implausivel.tolist() == [False, False, False, True, True]
