"""Exercício 1: comissão de cada vendedor.

Regra aplicada a cada venda, individualmente:
  - abaixo de R$ 100,00          -> sem comissão
  - de R$ 100,00 até R$ 499,99   -> 1%
  - a partir de R$ 500,00        -> 5%

Uso:  python -m desafio.comissoes [arquivo.json]
"""

import json
import sys
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from desafio.formatacao import reais

ARQUIVO_PADRAO = Path(__file__).resolve().parent.parent / "dados" / "vendas.json"

# (valor mínimo da venda, percentual), do maior para o menor
FAIXAS = [
    (Decimal("500.00"), Decimal("0.05")),
    (Decimal("100.00"), Decimal("0.01")),
]
CENTAVO = Decimal("0.01")


@dataclass
class ResumoVendedor:
    vendedor: str
    quantidade_vendas: int = 0
    total_vendido: Decimal = Decimal("0")
    comissao: Decimal = Decimal("0")


def percentual_comissao(valor: Decimal) -> Decimal:
    for minimo, percentual in FAIXAS:
        if valor >= minimo:
            return percentual
    return Decimal("0")


def calcular_comissao(valor: Decimal) -> Decimal:
    """Comissão de uma única venda, arredondada ao centavo."""
    if valor < 0:
        raise ValueError(f"Valor de venda negativo: {valor}")
    return (valor * percentual_comissao(valor)).quantize(CENTAVO, ROUND_HALF_UP)


def calcular_comissoes(vendas: list[dict]) -> list[ResumoVendedor]:
    """Agrupa as vendas por vendedor, na ordem em que aparecem."""
    resumos: dict[str, ResumoVendedor] = {}
    for venda in vendas:
        nome = venda["vendedor"]
        # str() evita imprecisão de float: Decimal(1200.5) != Decimal("1200.5")
        valor = Decimal(str(venda["valor"]))
        resumo = resumos.setdefault(nome, ResumoVendedor(nome))
        resumo.quantidade_vendas += 1
        resumo.total_vendido += valor
        resumo.comissao += calcular_comissao(valor)
    return list(resumos.values())


def carregar_vendas(caminho: Path) -> list[dict]:
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)["vendas"]


def relatorio(resumos: list[ResumoVendedor]) -> str:
    linhas = [
        f"{'Vendedor':<18}{'Vendas':>7}{'Total vendido':>17}{'Comissão':>14}",
        "-" * 56,
    ]
    for r in resumos:
        linhas.append(
            f"{r.vendedor:<18}{r.quantidade_vendas:>7}"
            f"{reais(r.total_vendido):>17}{reais(r.comissao):>14}"
        )
    linhas.append("-" * 56)
    total_vendido = sum((r.total_vendido for r in resumos), Decimal("0"))
    total_comissao = sum((r.comissao for r in resumos), Decimal("0"))
    quantidade = sum(r.quantidade_vendas for r in resumos)
    linhas.append(
        f"{'TOTAL':<18}{quantidade:>7}{reais(total_vendido):>17}{reais(total_comissao):>14}"
    )
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    caminho = Path(argv[0]) if argv else ARQUIVO_PADRAO
    print(relatorio(calcular_comissoes(carregar_vendas(caminho))))


if __name__ == "__main__":
    main()
