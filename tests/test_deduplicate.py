import pandas as pd

from src.deduplicate import deduplicar, similaridade_nome


def _registros(linhas: list[dict]) -> pd.DataFrame:
    colunas = ["chave_nome", "cpf", "email", "telefone", "data_nascimento", "cidade"]
    df = pd.DataFrame(linhas).reindex(columns=colunas)
    df["data_nascimento"] = pd.to_datetime(df["data_nascimento"])
    return df


def test_similaridade_nome():
    assert similaridade_nome("maria silva oliveira", "maria silva oliveira") == 1.0
    assert similaridade_nome("maria s oliveira", "maria silva oliveira") >= 0.9  # abreviação
    assert similaridade_nome("henrique araujo nunes", "henrique aarujo nunes") >= 0.88  # typo
    assert similaridade_nome("joao souza", "ana lima") < 0.5


def test_mesmo_cpf_e_transitividade():
    df = _registros([
        {"chave_nome": "ana lima", "cpf": "52998224725"},
        {"chave_nome": "ana lima", "cpf": "52998224725", "email": "ana@gmail.com"},
        {"chave_nome": "ana p lima", "email": "ana@gmail.com"},  # liga ao 2º pelo e-mail -> ao 1º também
    ])
    resultado, _ = deduplicar(df)
    assert resultado["cliente_id"].nunique() == 1


def test_familia_com_mesmo_email_nao_e_unida():
    df = _registros([
        {"chave_nome": "joao souza", "email": "familia@gmail.com", "data_nascimento": "1970-01-01"},
        {"chave_nome": "maria souza", "email": "familia@gmail.com", "data_nascimento": "1972-05-05"},
    ])
    resultado, _ = deduplicar(df)
    assert resultado["cliente_id"].nunique() == 2


def test_cpfs_validos_diferentes_nunca_sao_unidos():
    df = _registros([
        {"chave_nome": "carlos dias", "cpf": "52998224725", "telefone": "11987654321"},
        {"chave_nome": "carlos dias", "cpf": "01234567890", "telefone": "11987654321"},
    ])
    resultado, _ = deduplicar(df)
    assert resultado["cliente_id"].nunique() == 2


def test_nascimento_e_nome_exige_mesma_cidade():
    df = _registros([
        {"chave_nome": "paulo rocha", "data_nascimento": "1980-03-03", "cidade": "Recife"},
        {"chave_nome": "paulo rocha", "data_nascimento": "1980-03-03", "cidade": "Recife"},
        {"chave_nome": "paulo rocha", "data_nascimento": "1980-03-03", "cidade": "Curitiba"},
    ])
    resultado, _ = deduplicar(df)
    assert resultado["cliente_id"].tolist()[0] == resultado["cliente_id"].tolist()[1]
    assert resultado["cliente_id"].nunique() == 2
