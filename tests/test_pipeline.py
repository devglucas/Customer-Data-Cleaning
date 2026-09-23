"""Testes de ponta a ponta sobre os dados de data/raw (sem gravar arquivos)."""

import pytest

from main import executar_pipeline
from src.load import base_marketing
from src.validators import cpf_valido, email_valido


@pytest.fixture(scope="module")
def resultado():
    return executar_pipeline(exportar=False)


def test_nenhuma_regra_critica_falha(resultado):
    assert resultado["validacoes"].query("severidade == 'critica'")["passou"].all()


def test_todo_registro_tem_exatamente_um_cliente(resultado):
    registros, golden = resultado["registros"], resultado["golden"]
    assert registros["cliente_id"].notna().all()
    assert set(registros["cliente_id"]) == set(golden["cliente_id"])
    assert golden["qtd_registros"].sum() == len(registros)


def test_cadastro_final_tem_documentos_e_contatos_validos(resultado):
    golden = resultado["golden"]
    assert cpf_valido(golden["cpf"].dropna()).all()
    assert golden["cpf"].dropna().is_unique
    assert email_valido(golden["email"].dropna()).all()


def test_registros_de_teste_foram_rejeitados(resultado):
    nomes = resultado["golden"]["nome"].str.lower()
    assert not nomes.str.contains("teste|consumidor final|cliente balcao").any()
    assert (resultado["rejeitados"]["motivo_rejeicao"] == "registro_de_teste_ou_generico").sum() > 0


def test_deduplicacao_contra_gabarito(resultado):
    final = resultado["avaliacao"]["avaliacao_deduplicacao"].iloc[-1]
    assert final["precisao_pct"] >= 99.5
    assert final["recall_pct"] >= 99.0


def test_base_de_marketing_respeita_consentimento(resultado):
    marketing = base_marketing(resultado["golden"])
    consentiram = resultado["golden"].set_index("cliente_id")["opt_in_marketing"]
    assert consentiram.loc[marketing["cliente_id"]].all()
    assert email_valido(marketing["email"]).all()
    assert marketing["cpf_mascarado"].dropna().str.fullmatch(r"\*\*\*\.\d{3}\.\d{3}-\*\*").all()
    assert "cpf" not in marketing.columns
