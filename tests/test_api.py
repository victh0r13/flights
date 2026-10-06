"""Testes da API (sem internet): o TestClient faz requisições HTTP de mentira direto no app.

As rotas são gravadas numa pasta temporária, para não mexer no config/rotas.json real.
"""

import pytest
from fastapi.testclient import TestClient

import api.main as api
from rastreador import config

NOVA = {
    "nome": "Recife", "origem": "gru", "destino": "REC", "periodo_inicio": "2026-12-18",
    "periodo_fim": "2026-12-20", "preco_alvo": 1700, "email": "eu@exemplo.com",
}


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    arquivo = tmp_path / "rotas.json"
    monkeypatch.setattr(api, "carregar_rotas", lambda: config.carregar_rotas(arquivo))
    monkeypatch.setattr(api, "salvar_rotas", lambda rotas: config.salvar_rotas(rotas, arquivo))
    monkeypatch.setattr(api, "ultima_leitura", lambda rota_id: None)
    return TestClient(api.app)


def test_criar_listar_editar_remover(cliente):
    assert cliente.get("/api/rotas").json() == []

    criada = cliente.post("/api/rotas", json=NOVA)
    assert criada.status_code == 201
    assert criada.json()["id"] == "gru-rec"
    assert criada.json()["origem"] == "GRU"  # normalizado para maiúsculas

    editada = cliente.put("/api/rotas/gru-rec", json={**NOVA, "ativa": False})
    assert editada.json()["situacao"] == "pausada"

    assert cliente.delete("/api/rotas/gru-rec").status_code == 204
    assert cliente.get("/api/rotas").json() == []


def test_regra_do_motor_vira_422_com_mensagem(cliente):
    resposta = cliente.post("/api/rotas", json={**NOVA, "periodo_fim": "2027-06-01"})
    assert resposta.status_code == 422
    assert "60 dias" in resposta.json()["detail"]


def test_tipo_errado_e_barrado_pelo_pydantic(cliente):
    resposta = cliente.post("/api/rotas", json={**NOVA, "preco_alvo": "barato"})
    assert resposta.status_code == 422
    assert resposta.json()["detail"][0]["loc"] == ["body", "preco_alvo"]


def test_rota_inexistente_da_404(cliente):
    assert cliente.put("/api/rotas/nao-existe", json=NOVA).status_code == 404
    assert cliente.delete("/api/rotas/nao-existe").status_code == 404


def test_ids_nao_se_repetem(cliente):
    cliente.post("/api/rotas", json=NOVA)
    assert cliente.post("/api/rotas", json=NOVA).json()["id"] == "gru-rec-2"


def test_busca_de_aeroportos(cliente):
    codigos = [a["codigo"] for a in cliente.get("/api/aeroportos", params={"q": "lisboa"}).json()]
    assert codigos == ["LIS"]
