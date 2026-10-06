import tempfile
import unittest
from pathlib import Path

from desafio.estoque import ARQUIVO_ESTOQUE, ErroEstoque, Estoque, Produto, TipoMovimentacao


def novo_estoque() -> Estoque:
    return Estoque([Produto(101, "Caneta Azul", 150), Produto(102, "Caderno", 75)])


class TestMovimentar(unittest.TestCase):
    def test_entrada_soma_e_retorna_estoque_final(self):
        m = novo_estoque().movimentar(101, TipoMovimentacao.ENTRADA, 50, "Compra fornecedor")
        self.assertEqual(m.estoque_final, 200)
        self.assertEqual(m.descricao, "Compra fornecedor")

    def test_saida_subtrai(self):
        m = novo_estoque().movimentar(102, "saida", 75, "Venda")
        self.assertEqual(m.estoque_final, 0)

    def test_ids_sao_unicos_e_sequenciais(self):
        estoque = novo_estoque()
        ids = [estoque.movimentar(101, "ENTRADA", 1, "x").id for _ in range(3)]
        ids.append(estoque.movimentar(102, "SAIDA", 1, "x").id)
        self.assertEqual(ids, [1, 2, 3, 4])

    def test_saida_maior_que_estoque_e_rejeitada_sem_alterar_saldo(self):
        estoque = novo_estoque()
        with self.assertRaises(ErroEstoque):
            estoque.movimentar(102, "SAIDA", 76, "Venda")
        self.assertEqual(estoque.produto(102).estoque, 75)
        self.assertEqual(estoque.movimentacoes, [])

    def test_validacoes(self):
        estoque = novo_estoque()
        invalidas = [
            (999, "ENTRADA", 1, "x"),     # produto inexistente
            (101, "ENTRADA", 0, "x"),     # quantidade zero
            (101, "ENTRADA", -5, "x"),    # quantidade negativa
            (101, "ENTRADA", 1.5, "x"),   # quantidade fracionada
            (101, "ENTRADA", 1, "   "),   # sem descrição
            (101, "TRANSFERENCIA", 1, "x"),
        ]
        for args in invalidas:
            with self.subTest(args=args), self.assertRaises(ErroEstoque):
                estoque.movimentar(*args)


class TestPersistencia(unittest.TestCase):
    def test_salvar_e_carregar_mantem_saldo_e_ids(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "movimentacoes.json"
            estoque = Estoque.carregar(ARQUIVO_ESTOQUE, arquivo)
            estoque.movimentar(101, "ENTRADA", 50, "Compra")
            estoque.movimentar(101, "SAIDA", 20, "Venda")
            estoque.salvar(arquivo)

            recarregado = Estoque.carregar(ARQUIVO_ESTOQUE, arquivo)
            self.assertEqual(recarregado.produto(101).estoque, 180)
            self.assertEqual(recarregado.movimentar(103, "SAIDA", 10, "Venda").id, 3)


if __name__ == "__main__":
    unittest.main()
