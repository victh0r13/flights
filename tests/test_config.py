"""Testes de validação das rotas e da busca de aeroportos."""

import json

import pytest

from rastreador import aeroportos
from rastreador.config import ErroConfig, Rota, carregar_rotas, gerar_id, salvar_rotas


def rota_valida(**mudancas):
    dados = dict(id="gru-lis", nome="Lisboa", origem="GRU", destino="LIS",
                 periodo_inicio="2026-12-01", periodo_fim="2026-12-20",
                 preco_alvo=4000, email="eu@exemplo.com")
    dados.update(mudancas)
    return Rota(**dados)


def test_rota_valida_passa():
    rota_valida().validar()


@pytest.mark.parametrize("mudanca", [
    {"origem": "gru"},                     # minúsculo
    {"destino": "GRU"},                    # igual à origem
    {"periodo_fim": "2026-11-30"},         # fim antes do início
    {"periodo_fim": "2027-03-01"},         # período maior que 60 dias
    {"periodo_inicio": "01/12/2026"},      # formato errado
    {"preco_alvo": 0},
    {"regra": "qualquer"},
    {"email": "sem-arroba"},
    {"adultos": 0},
    {"max_conexoes": 5},
])
def test_rota_invalida_explica_o_erro(mudanca):
    with pytest.raises(ErroConfig):
        rota_valida(**mudanca).validar()


def test_salvar_e_carregar_ida_e_volta(tmp_path):
    arquivo = tmp_path / "rotas.json"
    salvar_rotas([rota_valida(dias_de_viagem=10)], arquivo)
    [carregada] = carregar_rotas(arquivo)
    assert carregada == rota_valida(dias_de_viagem=10)


def test_campo_desconhecido_no_arquivo(tmp_path):
    arquivo = tmp_path / "rotas.json"
    arquivo.write_text(json.dumps([{**rota_valida().__dict__, "cor": "azul"}]), encoding="utf-8")
    with pytest.raises(ErroConfig, match="cor"):
        carregar_rotas(arquivo)


def test_campo_faltando_no_arquivo(tmp_path):
    arquivo = tmp_path / "rotas.json"
    dados = rota_valida().__dict__
    del dados["email"]
    arquivo.write_text(json.dumps([dados]), encoding="utf-8")
    with pytest.raises(ErroConfig, match="email"):
        carregar_rotas(arquivo)


def test_gerar_id_nao_repete():
    assert gerar_id("GRU", "LIS", []) == "gru-lis"
    assert gerar_id("GRU", "LIS", [rota_valida()]) == "gru-lis-2"


@pytest.mark.parametrize("texto, esperado", [
    ("Lisboa", ["LIS"]),
    ("  sao PAULO ", ["GRU", "CGH", "VCP"]),   # sem acento, maiúsculas, espaços
    ("gru", ["GRU"]),                           # código conhecido
    ("rio", ["GIG", "SDU", "RBR"]),             # parte do nome: Rio de Janeiro e Rio Branco
    ("Porto", ["OPO"]),                         # nome exato vence "Porto Alegre"
    ("XYZ", ["XYZ"]),                           # 3 letras fora da lista: aceita
    ("Cidade Inexistente", []),
])
def test_procurar_aeroporto(texto, esperado):
    assert [codigo for codigo, _ in aeroportos.procurar(texto)] == esperado
