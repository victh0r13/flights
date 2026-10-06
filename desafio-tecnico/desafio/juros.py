"""Exercício 3: juros por atraso, calculados na data de hoje.

Taxa de 2,5% ao dia, juros simples sobre o valor original:

    juros = valor x 2,5% x dias de atraso

Se a conta ainda não venceu (ou vence hoje), não há juros.

Uso:
  python -m desafio.juros 1000 01/10/2026
  python -m desafio.juros 1000 01/10/2026 --hoje 04/10/2026   (simula outra data)
  python -m desafio.juros                                     (pergunta os dados)
"""

import argparse
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from desafio.formatacao import reais

TAXA_DIARIA = Decimal("0.025")
CENTAVO = Decimal("0.01")


@dataclass
class ResultadoJuros:
    valor: Decimal
    vencimento: date
    data_calculo: date
    dias_atraso: int
    juros: Decimal

    @property
    def total(self) -> Decimal:
        return self.valor + self.juros


def calcular_juros(
    valor: Decimal, vencimento: date, hoje: date | None = None, taxa_diaria: Decimal = TAXA_DIARIA
) -> ResultadoJuros:
    if valor < 0:
        raise ValueError("O valor não pode ser negativo.")
    hoje = hoje or date.today()
    dias_atraso = max((hoje - vencimento).days, 0)
    juros = (valor * taxa_diaria * dias_atraso).quantize(CENTAVO, ROUND_HALF_UP)
    return ResultadoJuros(valor, vencimento, hoje, dias_atraso, juros)


def ler_data(texto: str) -> date:
    """Aceita dd/mm/aaaa ou aaaa-mm-dd."""
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto.strip(), formato).date()
        except ValueError:
            pass
    raise ValueError(f"Data inválida: '{texto}'. Use dd/mm/aaaa.")


def ler_valor(texto: str) -> Decimal:
    """Aceita "1500.50", "1500,50" e "1.500,50"."""
    limpo = texto.strip().replace("R$", "").replace(" ", "")
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    try:
        valor = Decimal(limpo)
    except InvalidOperation:
        raise ValueError(f"Valor inválido: '{texto}'.") from None
    if not valor.is_finite():
        raise ValueError(f"Valor inválido: '{texto}'.")
    return valor


def texto_resultado(r: ResultadoJuros) -> str:
    linhas = [
        f"Valor original:   {reais(r.valor)}",
        f"Vencimento:       {r.vencimento:%d/%m/%Y}",
        f"Data do cálculo:  {r.data_calculo:%d/%m/%Y}",
    ]
    if r.dias_atraso == 0:
        linhas.append("Em dia: sem juros.")
    else:
        linhas.append(f"Dias de atraso:   {r.dias_atraso}")
        linhas.append(f"Juros (2,5%/dia): {reais(r.juros)}")
    linhas.append(f"Total a pagar:    {reais(r.total)}")
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calcula juros de 2,5% ao dia sobre uma conta vencida.")
    parser.add_argument("valor", nargs="?", help="valor da conta, ex.: 1500,00")
    parser.add_argument("vencimento", nargs="?", help="data de vencimento, ex.: 25/09/2026")
    parser.add_argument("--hoje", help="data de referência (padrão: hoje)")
    args = parser.parse_args(argv)

    try:
        valor = ler_valor(args.valor or input("Valor: "))
        vencimento = ler_data(args.vencimento or input("Vencimento (dd/mm/aaaa): "))
        hoje = ler_data(args.hoje) if args.hoje else None
        resultado = calcular_juros(valor, vencimento, hoje)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return 1
    print(texto_resultado(resultado))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
