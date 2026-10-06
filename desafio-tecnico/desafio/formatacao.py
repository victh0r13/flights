"""Formatação de valores no padrão brasileiro."""

from decimal import Decimal


def reais(valor: Decimal) -> str:
    """Formata um valor como moeda brasileira: Decimal("1234.5") -> "R$ 1.234,50"."""
    texto = f"{valor:,.2f}"  # 1,234.50
    return "R$ " + texto.replace(",", "_").replace(".", ",").replace("_", ".")
