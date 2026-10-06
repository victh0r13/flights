"""API do Rastreador de Passagens (FastAPI).

Ela é uma "casca" HTTP em volta do motor (pasta rastreador/): não tem regra de negócio
própria, só traduz requisições em chamadas ao motor e respostas em JSON.

Rodar:  .venv\\Scripts\\uvicorn api.main:app --reload
Documentação interativa (tipo Swagger): http://127.0.0.1:8000/docs
"""

import threading
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from rastreador import aeroportos, sincronizacao
from rastreador.analise import decidir, resumir
from rastreador.armazenamento import historico_rota, ultima_leitura
from rastreador.buscador import Resultado
from rastreador.config import ErroConfig, Rota, carregar_rotas, gerar_id, hoje, salvar_rotas
from rastreador.notificador import ErroEmail, enviar_email

from . import buscas
from .modelos import (
    Aeroporto,
    BuscaEntrada,
    BuscaSaida,
    Decisao,
    EmailTeste,
    Historico,
    Leitura,
    PrecoDia,
    Resumo,
    RotaEntrada,
    RotaSaida,
    StatusServidor,
)

app = FastAPI(title="Rastreador de Passagens", version="1.0")

# Em desenvolvimento o Next.js repassa /api para cá (proxy), então o navegador nem fala
# direto com a API. O CORS libera mesmo assim o acesso direto de localhost:3000.
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])

_trava_rotas = threading.Lock()  # duas requisições não podem gravar rotas.json ao mesmo tempo


@app.exception_handler(ErroConfig)
def erro_de_validacao(_request: Request, erro: ErroConfig) -> JSONResponse:
    """Regras do motor (ex.: 'período de no máximo 60 dias') viram HTTP 422 com a mensagem."""
    return JSONResponse(status_code=422, content={"detail": str(erro)})


# ------------------------------------------------------------ conversões

def _rota_de(dados: RotaEntrada | BuscaEntrada, rota_id: str) -> Rota:
    """Monta a Rota do motor a partir do JSON recebido (e valida)."""
    campos = dados.model_dump()
    campos["periodo_inicio"] = dados.periodo_inicio.isoformat()
    campos["periodo_fim"] = dados.periodo_fim.isoformat()
    campos["origem"], campos["destino"] = dados.origem.strip().upper(), dados.destino.strip().upper()
    if isinstance(dados, BuscaEntrada):  # busca de teste: nome, e-mail e meta não importam
        campos |= {"nome": "Busca de teste", "email": "teste@exemplo.com", "preco_alvo": dados.preco_alvo or 1}
    rota = Rota(id=rota_id, **campos)
    rota.validar()
    return rota


def _rota_saida(rota: Rota) -> RotaSaida:
    situacao = "pausada" if not rota.ativa else "encerrada" if rota.fim < hoje() else "ativa"
    leitura = ultima_leitura(rota.id)
    return RotaSaida(
        **asdict(rota),
        situacao=situacao,
        ultima_leitura=Leitura(quando=leitura[0], menor=leitura[1], media=leitura[2]) if leitura else None,
    )


def _preco_dia(r: Resultado) -> PrecoDia:
    return PrecoDia(data_ida=r.data_ida, data_volta=r.data_volta, preco=r.preco, companhia=r.companhia,
                    conexoes=r.conexoes, link=r.link)


def _encontrar(rotas: list[Rota], rota_id: str) -> Rota:
    for rota in rotas:
        if rota.id == rota_id:
            return rota
    raise HTTPException(status.HTTP_404_NOT_FOUND, f"Rota '{rota_id}' não encontrada.")


# ------------------------------------------------------------ rotas monitoradas

@app.get("/api/rotas", response_model=list[RotaSaida])
def listar_rotas():
    return [_rota_saida(r) for r in carregar_rotas()]


@app.post("/api/rotas", response_model=RotaSaida, status_code=status.HTTP_201_CREATED)
def criar_rota(dados: RotaEntrada):
    with _trava_rotas:
        rotas = carregar_rotas()
        rota = _rota_de(dados, gerar_id(dados.origem.strip().upper(), dados.destino.strip().upper(), rotas))
        rotas.append(rota)
        salvar_rotas(rotas)
    return _rota_saida(rota)


@app.put("/api/rotas/{rota_id}", response_model=RotaSaida)
def editar_rota(rota_id: str, dados: RotaEntrada):
    with _trava_rotas:
        rotas = carregar_rotas()
        indice = rotas.index(_encontrar(rotas, rota_id))
        rotas[indice] = _rota_de(dados, rota_id)  # o id não muda: o histórico continua ligado à rota
        salvar_rotas(rotas)
    return _rota_saida(rotas[indice])


@app.delete("/api/rotas/{rota_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_rota(rota_id: str):
    with _trava_rotas:
        rotas = carregar_rotas()
        rotas.remove(_encontrar(rotas, rota_id))
        salvar_rotas(rotas)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/rotas/{rota_id}/historico", response_model=Historico)
def ver_historico(rota_id: str):
    _encontrar(carregar_rotas(), rota_id)
    consultas, ultima = historico_rota(rota_id)
    return Historico(consultas=consultas, ultima=ultima)


# ------------------------------------------------------------ apoio ao formulário

@app.get("/api/aeroportos", response_model=list[Aeroporto])
def procurar_aeroportos(q: str = Query(min_length=1)):
    return [Aeroporto(codigo=c, descricao=d) for c, d in aeroportos.procurar(q)]


@app.post("/api/buscas", response_model=BuscaSaida, status_code=status.HTTP_202_ACCEPTED)
def iniciar_busca(dados: BuscaEntrada):
    rota = _rota_de(dados, "teste")
    try:
        busca = buscas.iniciar(rota)
    except buscas.BuscaEmAndamento as erro:
        raise HTTPException(status.HTTP_409_CONFLICT, str(erro)) from None
    return _busca_saida(busca, dados.preco_alvo)


@app.get("/api/buscas/{busca_id}", response_model=BuscaSaida)
def acompanhar_busca(busca_id: str, preco_alvo: int | None = None):
    busca = buscas.obter(busca_id)
    if not busca:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Busca não encontrada (o servidor pode ter reiniciado).")
    return _busca_saida(busca, preco_alvo)


def _busca_saida(busca: buscas.Busca, preco_alvo: int | None) -> BuscaSaida:
    resultados = sorted(busca.resultados, key=lambda r: r.data_ida)  # cópia: a thread continua adicionando
    resumo = resumir(resultados)
    decisao = sugestao = None
    if resumo:
        base = resumo.mais_barato.preco if busca.rota.regra == "menor_preco" else resumo.media
        sugestao = int(base * 0.9 // 10 * 10)  # 10% abaixo do valor de hoje, arredondado
        if preco_alvo:
            busca.rota.preco_alvo = preco_alvo
            d = decidir(busca.rota, resumo, ultimo_aviso=None)
            decisao = Decisao(avisar=d.avisar, motivo=d.motivo)
    return BuscaSaida(
        id=busca.id, status=busca.status, total=busca.total, feitos=busca.feitos,
        resultados=[_preco_dia(r) for r in resultados],
        resumo=Resumo(menor=resumo.mais_barato.preco, data_menor=resumo.mais_barato.data_ida,
                      media=resumo.media, maior=resumo.maior_preco) if resumo else None,
        decisao=decisao, sugestao_alvo=sugestao, erro=busca.erro,
    )


# ------------------------------------------------------------ e-mail e servidor

@app.post("/api/email/teste")
def testar_email(dados: EmailTeste):
    try:
        enviar_email(
            dados.para, "✈️ Teste do Rastreador de Passagens",
            "Se você recebeu este e-mail, o envio está funcionando!",
            "<p>Se você recebeu este e-mail, o envio está <b>funcionando</b>! ✈️</p>",
            usuario=dados.usuario, senha=dados.senha,
        )
    except ErroEmail as erro:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(erro)) from None
    return {"mensagem": f"E-mail enviado para {dados.para}. Confira a caixa de entrada (e o spam)."}


@app.get("/api/servidor", response_model=StatusServidor)
def status_servidor():
    endereco = sincronizacao.endereco_github()
    return StatusServidor(conectado=endereco is not None, endereco=endereco,
                          pendente=sincronizacao.tem_alteracoes_pendentes())


@app.post("/api/servidor/sincronizar")
def sincronizar():
    passos: list[str] = []
    with _trava_rotas:
        try:
            sincronizacao.sincronizar(avisar=passos.append)
        except sincronizacao.ErroSincronizacao as erro:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(erro)) from None
    return {"passos": passos}
