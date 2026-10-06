import unittest
from datetime import date
from decimal import Decimal

from desafio.juros import calcular_juros, ler_data, ler_valor

HOJE = date(2026, 10, 4)


class TestCalcularJuros(unittest.TestCase):
    def test_juros_simples_de_2_5_porcento_ao_dia(self):
        r = calcular_juros(Decimal("1000"), date(2026, 9, 24), HOJE)
        self.assertEqual(r.dias_atraso, 10)
        self.assertEqual(r.juros, Decimal("250.00"))
        self.assertEqual(r.total, Decimal("1250.00"))

    def test_um_dia_de_atraso(self):
        self.assertEqual(calcular_juros(Decimal("200"), date(2026, 10, 3), HOJE).juros, Decimal("5.00"))

    def test_arredonda_ao_centavo(self):
        self.assertEqual(calcular_juros(Decimal("250.50"), date(2026, 10, 1), HOJE).juros, Decimal("18.79"))

    def test_sem_juros_no_vencimento_ou_antes(self):
        for vencimento in (HOJE, date(2026, 12, 1)):
            r = calcular_juros(Decimal("1000"), vencimento, HOJE)
            self.assertEqual((r.dias_atraso, r.juros), (0, Decimal("0.00")))

    def test_usa_a_data_de_hoje_por_padrao(self):
        self.assertEqual(calcular_juros(Decimal("100"), date.today()).dias_atraso, 0)

    def test_valor_negativo_e_rejeitado(self):
        with self.assertRaises(ValueError):
            calcular_juros(Decimal("-1"), HOJE, HOJE)


class TestEntradas(unittest.TestCase):
    def test_ler_valor(self):
        self.assertEqual(ler_valor("1.500,50"), Decimal("1500.50"))
        self.assertEqual(ler_valor("R$ 99,9"), Decimal("99.9"))
        self.assertEqual(ler_valor("1500.50"), Decimal("1500.50"))
        for invalido in ("abc", "nan", ""):
            with self.subTest(invalido=invalido), self.assertRaises(ValueError):
                ler_valor(invalido)

    def test_ler_data(self):
        self.assertEqual(ler_data("04/10/2026"), HOJE)
        self.assertEqual(ler_data("2026-10-04"), HOJE)
        with self.assertRaises(ValueError):
            ler_data("31/02/2026")


if __name__ == "__main__":
    unittest.main()
