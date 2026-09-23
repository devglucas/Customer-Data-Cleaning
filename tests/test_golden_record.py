import pandas as pd

from src.golden_record import montar_golden_record

COLUNAS = ["registro_id", "cliente_id", "origem", "nome", "cpf", "data_nascimento", "genero", "email",
           "telefone", "tipo_telefone", "logradouro", "numero", "complemento", "bairro", "cep",
           "cidade", "uf", "opt_in_marketing", "data_atualizacao"]


def _registros(linhas):
    df = pd.DataFrame(linhas).reindex(columns=COLUNAS)
    df["registro_id"] = range(len(df))
    df["cliente_id"] = "CLI-00001"
    for coluna in ["data_nascimento", "data_atualizacao"]:
        df[coluna] = pd.to_datetime(df[coluna])
    df["opt_in_marketing"] = df["opt_in_marketing"].astype("boolean")
    return df


def test_regras_de_sobrevivencia():
    golden = montar_golden_record(_registros([
        {"origem": "crm", "nome": "Joao S. Lima", "cpf": "52998224725", "data_nascimento": "1980-05-10",
         "email": "joao.antigo@gmail.com", "logradouro": "Rua A", "numero": "10", "cep": "01000000",
         "cidade": "São Paulo", "uf": "SP", "data_atualizacao": "2020-01-01"},
        {"origem": "app", "nome": "João Silva Lima", "data_nascimento": "1980-05-10",
         "email": "joao.novo@gmail.com", "logradouro": "Rua B", "numero": "20",  # sem CEP
         "cidade": "São Paulo", "uf": "SP", "data_atualizacao": "2024-01-01"},
        {"origem": "loja", "nome": "Joao Silva Lima", "data_nascimento": "1980-10-05",  # dia/mês trocados
         "cidade": "Campinas", "data_atualizacao": "2022-01-01"},
    ]))
    cliente = golden.iloc[0]
    assert len(golden) == 1 and cliente["qtd_registros"] == 3
    assert cliente["nome"] == "João Silva Lima"                           # sem abreviação e com acento
    assert cliente["cpf"] == "52998224725"                                # único CPF do grupo
    assert cliente["email"] == "joao.novo@gmail.com"                      # mais recente
    assert cliente["data_nascimento"] == pd.Timestamp("1980-05-10")       # mais frequente
    assert cliente["logradouro"] == "Rua B" and pd.isna(cliente["cep"])  # bloco do mesmo registro
    assert cliente["cidade"] == "São Paulo"
    assert not cliente["opt_in_marketing"]                                # sem resposta = sem consentimento
    assert cliente["fontes"] == "app, crm, loja"
