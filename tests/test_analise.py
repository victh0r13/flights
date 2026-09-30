"""Testes da regra de alerta (o "cérebro" do robô). Rode com:  python -m pytest"""

from datetime import date

from rastreador.analise import decidir, resumir
from rastreador.buscador import Resultado
from rastreador.config import Rota


def rota(regra="menor_preco", alvo=1000):
    return Rota(id="gru-rec", nome="Teste", origem="GRU", destino="REC",
                periodo_inicio="2026-12-01", periodo_fim="2026-12-03",
                preco_alvo=alvo, email="eu@exemplo.com", regra=regra)


def resultados(*precos):
    return [Resultado(date(2026, 12, 1 + i), None, p, "Gol", 0, "http://x") for i, p in enumerate(precos)]


def test_resumo_calcula_menor_media_e_maior():
    resumo = resumir(resultados(1200, 900, 1500))
    assert resumo.mais_barato.preco == 900
    assert resumo.mais_barato.data_ida == date(2026, 12, 2)
    assert resumo.media == 1200
    assert resumo.maior_preco == 1500


def test_resumo_vazio():
    assert resumir([]) is None


def test_acima_da_meta_nao_avisa_e_esquece_aviso_anterior():
    decisao = decidir(rota(), resumir(resultados(1100, 1200)), ultimo_aviso=950)
    assert not decisao.avisar
    assert decisao.valor_para_lembrar is None


def test_primeira_vez_na_meta_avisa():
    decisao = decidir(rota(), resumir(resultados(1100, 990)), ultimo_aviso=None)
    assert decisao.avisar
    assert decisao.valor_para_lembrar == 990


def test_igual_a_meta_tambem_avisa():
    assert decidir(rota(), resumir(resultados(1000)), ultimo_aviso=None).avisar


def test_ja_avisado_e_queda_pequena_nao_repete():
    decisao = decidir(rota(), resumir(resultados(960)), ultimo_aviso=980)  # só 2% menor
    assert not decisao.avisar
    assert decisao.valor_para_lembrar == 980  # continua lembrando do aviso antigo


def test_ja_avisado_e_queda_grande_avisa_de_novo():
    decisao = decidir(rota(), resumir(resultados(900)), ultimo_aviso=980)  # ~8% menor
    assert decisao.avisar
    assert decisao.valor_para_lembrar == 900


def test_regra_media_ignora_um_dia_barato_isolado():
    precos = resultados(800, 1300, 1300)  # um dia barato, média 1133
    assert decidir(rota("menor_preco"), resumir(precos), None).avisar
    assert not decidir(rota("media"), resumir(precos), None).avisar


def test_regra_media_avisa_quando_media_na_meta():
    decisao = decidir(rota("media"), resumir(resultados(900, 1000, 1050)), None)  # média 983
    assert decisao.avisar
    assert round(decisao.valor) == 983
