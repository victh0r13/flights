"""Decide se um alerta deve ser enviado.

Este módulo é "puro": não acessa internet nem arquivos, só recebe números e
devolve uma decisão. Isso facilita testar (veja tests/test_analise.py).
"""

from dataclasses import dataclass

from .buscador import Resultado
from .config import Rota, formatar_reais

# Depois de avisar, só avisa de novo se o valor cair pelo menos 3% a mais.
# Evita um e-mail a cada R$ 5 de oscilação.
QUEDA_MINIMA_PARA_NOVO_AVISO = 0.03


@dataclass
class Resumo:
    dias_com_preco: int
    mais_barato: Resultado
    media: float
    maior_preco: int


@dataclass
class Decisao:
    avisar: bool
    motivo: str
    valor: float  # o número que foi comparado com a meta (menor preço ou média)
    valor_para_lembrar: float | None  # o que guardar como "último aviso" (None = esquecer)


def resumir(resultados: list[Resultado]) -> Resumo | None:
    if not resultados:
        return None
    precos = [r.preco for r in resultados]
    return Resumo(
        dias_com_preco=len(precos),
        mais_barato=min(resultados, key=lambda r: r.preco),
        media=sum(precos) / len(precos),
        maior_preco=max(precos),
    )


def decidir(rota: Rota, resumo: Resumo, ultimo_aviso: float | None) -> Decisao:
    """Compara com a meta e com o último aviso enviado.

    - acima da meta              -> não avisa e "esquece" o último aviso
                                    (se voltar a cair, avisa de novo)
    - atingiu a meta pela 1ª vez -> avisa
    - já avisou, caiu +3%        -> avisa de novo
    - já avisou, não caiu o bastante -> não avisa (anti-spam)
    """
    valor = resumo.mais_barato.preco if rota.regra == "menor_preco" else resumo.media
    nome_valor = "menor preço" if rota.regra == "menor_preco" else "média do período"

    if valor > rota.preco_alvo:
        return Decisao(False, f"{nome_valor} {formatar_reais(valor)} acima da meta", valor, None)

    if ultimo_aviso is None:
        return Decisao(True, f"{nome_valor} atingiu a meta: {formatar_reais(valor)}", valor, valor)

    if valor <= ultimo_aviso * (1 - QUEDA_MINIMA_PARA_NOVO_AVISO):
        motivo = f"{nome_valor} caiu ainda mais: {formatar_reais(valor)} (antes {formatar_reais(ultimo_aviso)})"
        return Decisao(True, motivo, valor, valor)

    return Decisao(False, f"{nome_valor} {formatar_reais(valor)} — já avisado antes", valor, ultimo_aviso)
