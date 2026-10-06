"""Formato dos dados que entram e saem da API (equivalente aos DTOs do C#).

O Pydantic confere os tipos automaticamente: se o front mandar texto onde deveria
haver número, a API responde 422 explicando o campo, antes de qualquer código nosso rodar.
As regras de negócio (período máximo, origem ≠ destino...) continuam em Rota.validar().
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Regra = Literal["menor_preco", "media"]


class RotaEntrada(BaseModel):
    """O que o front envia ao criar ou editar uma rota."""

    nome: str = Field(min_length=1, max_length=80)
    origem: str
    destino: str
    periodo_inicio: date
    periodo_fim: date
    preco_alvo: int
    email: str
    regra: Regra = "menor_preco"
    dias_de_viagem: int | None = None  # None = só ida
    adultos: int = 1
    max_conexoes: int | None = None  # None = qualquer
    ativa: bool = True


class Leitura(BaseModel):
    quando: str
    menor: int
    media: float


class RotaSaida(RotaEntrada):
    id: str
    situacao: Literal["ativa", "pausada", "encerrada"]
    ultima_leitura: Leitura | None


class Consulta(BaseModel):
    """Resumo de uma verificação do robô."""

    quando: str
    menor: int
    media: float
    dias: int


class PrecoDia(BaseModel):
    data_ida: date
    data_volta: date | None
    preco: int
    companhia: str
    conexoes: int
    link: str | None = None


class Historico(BaseModel):
    consultas: list[Consulta]
    ultima: list[PrecoDia]


class BuscaEntrada(BaseModel):
    """Uma pesquisa de teste: os mesmos campos da rota, sem nome/e-mail; meta opcional."""

    origem: str
    destino: str
    periodo_inicio: date
    periodo_fim: date
    dias_de_viagem: int | None = None
    adultos: int = 1
    max_conexoes: int | None = None
    regra: Regra = "menor_preco"
    preco_alvo: int | None = None


class Resumo(BaseModel):
    menor: int
    data_menor: date
    media: float
    maior: int


class Decisao(BaseModel):
    avisar: bool
    motivo: str


class BuscaSaida(BaseModel):
    id: str
    status: Literal["rodando", "concluida", "erro"]
    total: int
    feitos: int
    resultados: list[PrecoDia]
    resumo: Resumo | None
    decisao: Decisao | None  # só quando há meta
    sugestao_alvo: int | None  # 10% abaixo do valor de hoje
    erro: str | None


class Aeroporto(BaseModel):
    codigo: str
    descricao: str


class EmailTeste(BaseModel):
    usuario: str
    senha: str
    para: str


class StatusServidor(BaseModel):
    conectado: bool
    endereco: str | None
    pendente: bool
