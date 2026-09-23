import pandas as pd

from src.validators import cep_valido, cpf_valido, email_valido, telefone_valido


def test_cpf_valido_confere_digitos_verificadores():
    cpfs = pd.Series(["52998224725", "52998224726", "11111111111", "5299822472", None, "abc"])
    assert cpf_valido(cpfs).tolist() == [True, False, False, False, False, False]


def test_cpf_valido_com_zero_a_esquerda():
    # 01234567890 é um CPF válido que começa com zero
    assert cpf_valido(pd.Series(["01234567890"])).all()


def test_email_valido():
    emails = pd.Series(["ana.silva@gmail.com", "ana@empresa.com.br", "ana@@gmail.com", "ana@gmail", "anagmail.com", None])
    assert email_valido(emails).tolist() == [True, True, False, False, False, False]


def test_telefone_valido_celular_e_fixo():
    telefones = pd.Series(["11987654321", "1133334444", "11887654321", "00987654321", "987654321", None])
    assert telefone_valido(telefones).tolist() == [True, True, False, False, False, False]


def test_cep_valido():
    assert cep_valido(pd.Series(["01310100", "00000000", "1310100", None])).tolist() == [True, False, False, False]
