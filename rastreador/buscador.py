"""Consulta de preços no Google Flights.

Não existe uma API oficial e gratuita do Google Flights. A biblioteca `fast-flights`
monta o mesmo endereço que o site usa e lê os dados da página que volta
(técnica chamada "web scraping"). Aqui nós só pedimos: "qual o voo mais barato
saindo no dia X?" — uma vez para cada dia do período.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from fast_flights import FlightQuery, FlightsNotFound, Passengers, create_query, get_flights

from .config import Rota, hoje

PAUSA_ENTRE_BUSCAS = 2  # segundos entre uma busca e outra, para não sermos bloqueados
TENTATIVAS = 3  # se der erro de rede, tenta de novo antes de desistir daquele dia


@dataclass
class Resultado:
    """O voo mais barato encontrado para uma data de ida."""

    data_ida: date
    data_volta: date | None
    preco: int  # total em reais, para todos os passageiros
    companhia: str
    conexoes: int
    link: str  # abre a mesma busca no Google Flights


def buscar_dia(rota: Rota, data_ida: date) -> Resultado | None:
    """Busca o voo mais barato para uma data de ida. None se não houver voo ou der erro."""
    data_volta = data_ida + timedelta(days=rota.dias_de_viagem) if rota.dias_de_viagem else None

    trechos = [FlightQuery(date=data_ida.isoformat(), from_airport=rota.origem, to_airport=rota.destino)]
    if data_volta:
        trechos.append(FlightQuery(date=data_volta.isoformat(), from_airport=rota.destino, to_airport=rota.origem))

    consulta = create_query(
        flights=trechos,
        trip="round-trip" if data_volta else "one-way",
        passengers=Passengers(adults=rota.adultos),
        currency="BRL",
        language="pt-BR",
        max_stops=rota.max_conexoes,
    )

    for tentativa in range(1, TENTATIVAS + 1):
        try:
            voos = get_flights(consulta)
            break
        except FlightsNotFound:
            return None
        except Exception as erro:  # rede instável, bloqueio temporário, página diferente...
            if tentativa == TENTATIVAS:
                print(f"    ! {data_ida:%d/%m}: falhou após {TENTATIVAS} tentativas ({type(erro).__name__}: {erro})")
                return None
            time.sleep(PAUSA_ENTRE_BUSCAS * tentativa)  # espera um pouco mais a cada tentativa

    voos = [v for v in voos if v.price]
    if not voos:
        return None

    mais_barato = min(voos, key=lambda v: v.price)
    return Resultado(
        data_ida=data_ida,
        data_volta=data_volta,
        preco=mais_barato.price,
        companhia=", ".join(mais_barato.airlines),
        conexoes=len(mais_barato.flights) - 1,
        link=consulta.url(),
    )


def datas_do_periodo(rota: Rota) -> list[date]:
    """Todas as datas de ida do período que ainda não passaram."""
    primeira = max(rota.inicio, hoje())
    return [primeira + timedelta(days=n) for n in range((rota.fim - primeira).days + 1)]


def buscar_periodo(rota: Rota, ao_buscar: Callable[[date, Resultado | None], None] | None = None) -> list[Resultado]:
    """Busca cada dia do período. `ao_buscar` é chamado a cada dia (para mostrar progresso)."""
    resultados = []
    datas = datas_do_periodo(rota)
    for i, data_ida in enumerate(datas):
        resultado = buscar_dia(rota, data_ida)
        if resultado:
            resultados.append(resultado)
        if ao_buscar:
            ao_buscar(data_ida, resultado)
        if i < len(datas) - 1:
            time.sleep(PAUSA_ENTRE_BUSCAS)
    return resultados
