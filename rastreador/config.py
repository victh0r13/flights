"""Rotas monitoradas: leitura, validação e gravação de config/rotas.json.

Uma "rota" é um pedido do tipo: "me avise quando GRU -> LIS, saindo entre
01/12 e 20/12, custar até R$ 4.000".
"""

import json
import re
import sys
from dataclasses import MISSING, asdict, dataclass, fields
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Quando o programa vira .exe, o Python roda de uma pasta temporária.
# A pasta "de verdade" do projeto é onde o .exe está.
if getattr(sys, "frozen", False):
    PASTA_PROJETO = Path(sys.executable).resolve().parent
else:
    PASTA_PROJETO = Path(__file__).resolve().parent.parent

ARQ_ROTAS = PASTA_PROJETO / "config" / "rotas.json"

# O Brasil não tem mais horário de verão, então Brasília é sempre UTC-3.
# O servidor do GitHub roda em UTC; usamos isto para as datas saírem certas.
FUSO_BRASILIA = timezone(timedelta(hours=-3))

MAX_DIAS_PERIODO = 60  # cada dia do período é uma busca; limita o tempo de execução

REGRAS = {
    "menor_preco": "quando QUALQUER dia do período custar até o valor",
    "media": "quando a MÉDIA de preço do período ficar até o valor",
}


def hoje() -> date:
    return datetime.now(FUSO_BRASILIA).date()


class ErroConfig(Exception):
    """Problema no arquivo de rotas, com mensagem amigável."""


@dataclass
class Rota:
    id: str
    nome: str
    origem: str
    destino: str
    periodo_inicio: str  # AAAA-MM-DD: primeira data de ida aceitável
    periodo_fim: str  # AAAA-MM-DD: última data de ida aceitável
    preco_alvo: int  # em reais, total para todos os passageiros
    email: str  # quem recebe o alerta
    regra: str = "menor_preco"
    dias_de_viagem: int | None = None  # None = só ida; 10 = volta 10 dias depois
    adultos: int = 1
    max_conexoes: int | None = None  # None = qualquer; 0 = só voo direto
    ativa: bool = True

    @property
    def inicio(self) -> date:
        return date.fromisoformat(self.periodo_inicio)

    @property
    def fim(self) -> date:
        return date.fromisoformat(self.periodo_fim)

    def validar(self) -> None:
        """Confere tudo e explica o problema em português, se houver."""
        onde = f"Rota '{self.nome or self.id}'"
        for campo in ("origem", "destino"):
            if not re.fullmatch(r"[A-Z]{3}", getattr(self, campo)):
                raise ErroConfig(f"{onde}: {campo} deve ser um código de 3 letras (ex.: GRU).")
        if self.origem == self.destino:
            raise ErroConfig(f"{onde}: origem e destino são iguais.")
        try:
            inicio, fim = self.inicio, self.fim
        except ValueError:
            raise ErroConfig(f"{onde}: datas devem estar no formato AAAA-MM-DD.") from None
        if fim < inicio:
            raise ErroConfig(f"{onde}: o fim do período é antes do início.")
        if (fim - inicio).days + 1 > MAX_DIAS_PERIODO:
            raise ErroConfig(f"{onde}: o período pode ter no máximo {MAX_DIAS_PERIODO} dias.")
        if self.preco_alvo <= 0:
            raise ErroConfig(f"{onde}: o preço alvo deve ser maior que zero.")
        if self.regra not in REGRAS:
            raise ErroConfig(f"{onde}: regra deve ser uma destas: {', '.join(REGRAS)}.")
        if self.dias_de_viagem is not None and not 1 <= self.dias_de_viagem <= 90:
            raise ErroConfig(f"{onde}: dias_de_viagem deve ficar entre 1 e 90.")
        if not 1 <= self.adultos <= 9:
            raise ErroConfig(f"{onde}: adultos deve ficar entre 1 e 9.")
        if self.max_conexoes is not None and not 0 <= self.max_conexoes <= 2:
            raise ErroConfig(f"{onde}: max_conexoes deve ser 0, 1 ou 2.")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", self.email):
            raise ErroConfig(f"{onde}: e-mail inválido ({self.email}).")

    def descrever(self) -> str:
        """Resumo de uma linha, para mostrar na tela e no e-mail."""
        tipo = f"ida e volta ({self.dias_de_viagem} dias)" if self.dias_de_viagem else "só ida"
        periodo = f"{self.inicio:%d/%m/%Y} a {self.fim:%d/%m/%Y}"
        regra = "menor preço" if self.regra == "menor_preco" else "média"
        return (
            f"{self.origem} → {self.destino} | saída entre {periodo} | {tipo} | "
            f"alvo {formatar_reais(self.preco_alvo)} ({regra})"
        )


def formatar_reais(valor: float) -> str:
    return "R$ " + f"{valor:,.0f}".replace(",", ".")


def carregar_rotas(caminho: Path = ARQ_ROTAS) -> list[Rota]:
    if not caminho.exists():
        return []
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as erro:
        raise ErroConfig(f"O arquivo {caminho.name} está mal formatado (linha {erro.lineno}).") from None

    campos_validos = {f.name for f in fields(Rota)}
    rotas = []
    for item in dados:
        desconhecidos = set(item) - campos_validos
        if desconhecidos:
            raise ErroConfig(f"Campo(s) desconhecido(s) em {caminho.name}: {', '.join(desconhecidos)}")
        try:
            rota = Rota(**item)
        except TypeError:
            faltando = [f.name for f in fields(Rota) if f.name not in item and f.default is MISSING]
            raise ErroConfig(f"Falta(m) campo(s) em {caminho.name}: {', '.join(faltando)}") from None
        rota.validar()
        rotas.append(rota)
    return rotas


def salvar_rotas(rotas: list[Rota], caminho: Path = ARQ_ROTAS) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conteudo = json.dumps([asdict(r) for r in rotas], indent=2, ensure_ascii=False)
    caminho.write_text(conteudo + "\n", encoding="utf-8")


def gerar_id(origem: str, destino: str, rotas: list[Rota]) -> str:
    """Identificador legível e único, ex.: 'gru-lis', 'gru-lis-2'."""
    base = f"{origem}-{destino}".lower()
    usados = {r.id for r in rotas}
    if base not in usados:
        return base
    n = 2
    while f"{base}-{n}" in usados:
        n += 1
    return f"{base}-{n}"
