"""Buscas de teste em segundo plano.

Pesquisar 57 dias leva uns 3 minutos — tempo demais para uma requisição HTTP ficar
esperando. Então: POST /api/buscas inicia a pesquisa numa thread e devolve um id na hora;
o front pergunta GET /api/buscas/{id} a cada segundo ("polling") e mostra o progresso.
"""

import threading
import uuid
from dataclasses import dataclass, field

from rastreador.buscador import Resultado, buscar_periodo, datas_do_periodo
from rastreador.config import Rota

MAX_GUARDADAS = 20  # buscas antigas são esquecidas para não acumular memória


class BuscaEmAndamento(Exception):
    """Já existe uma busca rodando (uma por vez, para não sermos bloqueados pelo Google)."""


@dataclass
class Busca:
    id: str
    rota: Rota
    total: int
    status: str = "rodando"
    feitos: int = 0
    resultados: list[Resultado] = field(default_factory=list)
    erro: str | None = None


_buscas: dict[str, Busca] = {}
_trava = threading.Lock()  # protege _buscas quando duas requisições chegam juntas


def iniciar(rota: Rota) -> Busca:
    with _trava:
        if any(b.status == "rodando" for b in _buscas.values()):
            raise BuscaEmAndamento("Já existe uma busca em andamento. Aguarde ela terminar.")
        busca = Busca(id=uuid.uuid4().hex[:12], rota=rota, total=len(datas_do_periodo(rota)))
        _buscas[busca.id] = busca
        while len(_buscas) > MAX_GUARDADAS:
            del _buscas[next(iter(_buscas))]  # remove a mais antiga
    threading.Thread(target=_executar, args=(busca,), daemon=True).start()
    return busca


def obter(busca_id: str) -> Busca | None:
    return _buscas.get(busca_id)


def _executar(busca: Busca) -> None:
    def ao_buscar(_data, resultado: Resultado | None) -> None:
        busca.feitos += 1
        if resultado:
            busca.resultados.append(resultado)

    try:
        buscar_periodo(busca.rota, ao_buscar=ao_buscar)
        busca.status = "concluida"
    except Exception as erro:  # a thread não pode "explodir" em silêncio
        busca.status, busca.erro = "erro", f"{type(erro).__name__}: {erro}"
