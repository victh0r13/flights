"""Exercício 2: movimentações de estoque (entrada e saída).

Cada movimentação tem um identificador único (sequencial), um tipo
(ENTRADA ou SAIDA), uma descrição livre e retorna o estoque final do produto.

O estoque inicial vem de dados/estoque.json e nunca é alterado. As
movimentações ficam gravadas em dados/movimentacoes.json; o saldo atual é
o estoque inicial com todas as movimentações aplicadas. Assim o histórico
é completo e dá para conferir de onde veio cada número.

Uso:
  python -m desafio.estoque                          (menu interativo)
  python -m desafio.estoque entrada 101 50 "Compra do fornecedor X"
  python -m desafio.estoque saida 102 5 "Venda pedido 123"
  python -m desafio.estoque saldo
  python -m desafio.estoque historico
"""

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

PASTA_DADOS = Path(__file__).resolve().parent.parent / "dados"
ARQUIVO_ESTOQUE = PASTA_DADOS / "estoque.json"
ARQUIVO_MOVIMENTACOES = PASTA_DADOS / "movimentacoes.json"


class TipoMovimentacao(str, Enum):
    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"


class ErroEstoque(Exception):
    """Movimentação inválida (produto inexistente, quantidade inválida, saldo insuficiente)."""


@dataclass
class Produto:
    codigo: int
    descricao: str
    estoque: int


@dataclass
class Movimentacao:
    id: int
    codigo_produto: int
    tipo: TipoMovimentacao
    quantidade: int
    descricao: str
    data_hora: str
    estoque_final: int


class Estoque:
    def __init__(self, produtos: list[Produto]):
        self.produtos = {p.codigo: p for p in produtos}
        self.movimentacoes: list[Movimentacao] = []

    def produto(self, codigo: int) -> Produto:
        try:
            return self.produtos[codigo]
        except KeyError:
            raise ErroEstoque(f"Produto {codigo} não cadastrado.") from None

    def proximo_id(self) -> int:
        return max((m.id for m in self.movimentacoes), default=0) + 1

    def movimentar(
        self,
        codigo_produto: int,
        tipo: TipoMovimentacao | str,
        quantidade: int,
        descricao: str,
        data_hora: datetime | None = None,
    ) -> Movimentacao:
        """Lança uma movimentação e devolve-a com o estoque final do produto."""
        if not isinstance(tipo, TipoMovimentacao):
            try:
                tipo = TipoMovimentacao(str(tipo).upper())
            except ValueError:
                raise ErroEstoque(f"Tipo de movimentação inválido: {tipo}. Use ENTRADA ou SAIDA.") from None
        produto = self.produto(codigo_produto)
        if isinstance(quantidade, bool) or not isinstance(quantidade, int) or quantidade <= 0:
            raise ErroEstoque("A quantidade deve ser um número inteiro maior que zero.")
        descricao = descricao.strip()
        if not descricao:
            raise ErroEstoque("Informe uma descrição para a movimentação.")
        if tipo is TipoMovimentacao.SAIDA and quantidade > produto.estoque:
            raise ErroEstoque(
                f"Estoque insuficiente de '{produto.descricao}': "
                f"disponível {produto.estoque}, solicitado {quantidade}."
            )

        produto.estoque += quantidade if tipo is TipoMovimentacao.ENTRADA else -quantidade
        movimentacao = Movimentacao(
            id=self.proximo_id(),
            codigo_produto=produto.codigo,
            tipo=tipo,
            quantidade=quantidade,
            descricao=descricao,
            data_hora=(data_hora or datetime.now()).isoformat(timespec="seconds"),
            estoque_final=produto.estoque,
        )
        self.movimentacoes.append(movimentacao)
        return movimentacao

    # ---- persistência -------------------------------------------------

    @classmethod
    def carregar(
        cls, arquivo_estoque: Path = ARQUIVO_ESTOQUE, arquivo_movimentacoes: Path = ARQUIVO_MOVIMENTACOES
    ) -> "Estoque":
        with open(arquivo_estoque, encoding="utf-8") as f:
            itens = json.load(f)["estoque"]
        estoque = cls([Produto(i["codigoProduto"], i["descricaoProduto"], i["estoque"]) for i in itens])
        if arquivo_movimentacoes.exists():
            with open(arquivo_movimentacoes, encoding="utf-8") as f:
                for m in json.load(f)["movimentacoes"]:
                    estoque.aplicar_registrada(Movimentacao(**{**m, "tipo": TipoMovimentacao(m["tipo"])}))
        return estoque

    def aplicar_registrada(self, m: Movimentacao) -> None:
        """Reaplica uma movimentação já gravada, mantendo o id original."""
        produto = self.produto(m.codigo_produto)
        produto.estoque += m.quantidade if m.tipo is TipoMovimentacao.ENTRADA else -m.quantidade
        self.movimentacoes.append(m)

    def salvar(self, arquivo_movimentacoes: Path = ARQUIVO_MOVIMENTACOES) -> None:
        dados = {"movimentacoes": [{**asdict(m), "tipo": m.tipo.value} for m in self.movimentacoes]}
        with open(arquivo_movimentacoes, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)


# ---- interface de linha de comando ------------------------------------


def texto_saldo(estoque: Estoque) -> str:
    linhas = [f"{'Código':<8}{'Produto':<28}{'Estoque':>8}"]
    for p in estoque.produtos.values():
        linhas.append(f"{p.codigo:<8}{p.descricao:<28}{p.estoque:>8}")
    return "\n".join(linhas)


def texto_historico(estoque: Estoque) -> str:
    if not estoque.movimentacoes:
        return "Nenhuma movimentação lançada."
    linhas = [f"{'ID':>4}  {'Data/hora':<19}  {'Prod.':<5}  {'Tipo':<7}{'Qtde':>6}{'Saldo':>7}  Descrição"]
    for m in estoque.movimentacoes:
        linhas.append(
            f"{m.id:>4}  {m.data_hora:<19}  {m.codigo_produto:<5}  {m.tipo.value:<7}"
            f"{m.quantidade:>6}{m.estoque_final:>7}  {m.descricao}"
        )
    return "\n".join(linhas)


def texto_movimentacao(estoque: Estoque, m: Movimentacao) -> str:
    produto = estoque.produto(m.codigo_produto)
    sinal = "+" if m.tipo is TipoMovimentacao.ENTRADA else "-"
    return (
        f"Movimentação #{m.id} registrada ({m.tipo.value}: {m.descricao}).\n"
        f"{produto.descricao}: {sinal}{m.quantidade} -> estoque final: {m.estoque_final}"
    )


def perguntar_inteiro(pergunta: str) -> int:
    while True:
        resposta = input(pergunta).strip()
        try:
            return int(resposta)
        except ValueError:
            print("Digite um número inteiro.")


def menu(estoque: Estoque, arquivo_movimentacoes: Path) -> None:
    opcoes = {"1": TipoMovimentacao.ENTRADA, "2": TipoMovimentacao.SAIDA}
    while True:
        print("\n=== Controle de Estoque ===")
        print("1 - Entrada de mercadoria")
        print("2 - Saída de mercadoria")
        print("3 - Consultar estoque")
        print("4 - Histórico de movimentações")
        print("0 - Sair")
        opcao = input("Opção: ").strip()

        if opcao == "0":
            return
        if opcao == "3":
            print(texto_saldo(estoque))
        elif opcao == "4":
            print(texto_historico(estoque))
        elif opcao in opcoes:
            print(texto_saldo(estoque))
            codigo = perguntar_inteiro("Código do produto: ")
            quantidade = perguntar_inteiro("Quantidade: ")
            descricao = input("Descrição (ex.: Compra fornecedor, Venda, Devolução): ")
            try:
                m = estoque.movimentar(codigo, opcoes[opcao], quantidade, descricao)
            except ErroEstoque as erro:
                print(f"Erro: {erro}")
                continue
            estoque.salvar(arquivo_movimentacoes)
            print(texto_movimentacao(estoque, m))
        else:
            print("Opção inválida.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Movimentações de estoque.")
    parser.add_argument("--movimentacoes", type=Path, default=ARQUIVO_MOVIMENTACOES,
                        help="arquivo onde as movimentações são gravadas")
    sub = parser.add_subparsers(dest="comando")
    for nome in ("entrada", "saida"):
        p = sub.add_parser(nome, help=f"lança uma {nome}")
        p.add_argument("codigo", type=int)
        p.add_argument("quantidade", type=int)
        p.add_argument("descricao")
    sub.add_parser("saldo", help="mostra o estoque atual")
    sub.add_parser("historico", help="lista as movimentações")
    args = parser.parse_args(argv)

    estoque = Estoque.carregar(arquivo_movimentacoes=args.movimentacoes)
    if args.comando is None:
        menu(estoque, args.movimentacoes)
    elif args.comando == "saldo":
        print(texto_saldo(estoque))
    elif args.comando == "historico":
        print(texto_historico(estoque))
    else:
        try:
            m = estoque.movimentar(args.codigo, args.comando.upper(), args.quantidade, args.descricao)
        except ErroEstoque as erro:
            print(f"Erro: {erro}")
            return 1
        estoque.salvar(args.movimentacoes)
        print(texto_movimentacao(estoque, m))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
