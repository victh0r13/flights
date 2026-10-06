import unittest
from decimal import Decimal

from desafio.comissoes import calcular_comissao, calcular_comissoes, carregar_vendas, ARQUIVO_PADRAO


class TestCalcularComissao(unittest.TestCase):
    def test_abaixo_de_100_nao_gera_comissao(self):
        self.assertEqual(calcular_comissao(Decimal("99.99")), Decimal("0"))
        self.assertEqual(calcular_comissao(Decimal("0")), Decimal("0"))

    def test_de_100_ate_abaixo_de_500_gera_1_porcento(self):
        self.assertEqual(calcular_comissao(Decimal("100.00")), Decimal("1.00"))
        self.assertEqual(calcular_comissao(Decimal("499.99")), Decimal("5.00"))

    def test_a_partir_de_500_gera_5_porcento(self):
        self.assertEqual(calcular_comissao(Decimal("500.00")), Decimal("25.00"))
        self.assertEqual(calcular_comissao(Decimal("1200.50")), Decimal("60.03"))

    def test_valor_negativo_e_rejeitado(self):
        with self.assertRaises(ValueError):
            calcular_comissao(Decimal("-1"))


class TestCalcularComissoes(unittest.TestCase):
    def test_agrupa_por_vendedor(self):
        vendas = [
            {"vendedor": "A", "valor": 1000},
            {"vendedor": "B", "valor": 50},
            {"vendedor": "A", "valor": 200},
        ]
        a, b = calcular_comissoes(vendas)
        self.assertEqual((a.vendedor, a.quantidade_vendas, a.total_vendido, a.comissao),
                         ("A", 2, Decimal("1200"), Decimal("52.00")))
        self.assertEqual((b.vendedor, b.comissao), ("B", Decimal("0")))

    def test_dados_do_desafio(self):
        resumos = {r.vendedor: r.comissao for r in calcular_comissoes(carregar_vendas(ARQUIVO_PADRAO))}
        self.assertEqual(resumos, {
            "João Silva": Decimal("495.69"),
            "Maria Souza": Decimal("465.96"),
            "Carlos Oliveira": Decimal("379.38"),
            "Ana Lima": Decimal("404.99"),
        })


if __name__ == "__main__":
    unittest.main()
