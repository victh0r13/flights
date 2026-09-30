"""Memória do robô, guardada em arquivos simples dentro da pasta dados/.

- historico.csv: todo preço encontrado, para análises e gráficos futuros
  (abre no Excel/Google Sheets).
- avisos.json: último valor avisado por rota, para não repetir o mesmo e-mail.

O servidor salva esses arquivos de volta no GitHub a cada execução, então
nada se perde quando a máquina do servidor é desligada.
"""

import csv
import json
from datetime import datetime
from pathlib import Path

from .buscador import Resultado
from .config import PASTA_PROJETO, Rota

ARQ_HISTORICO = PASTA_PROJETO / "dados" / "historico.csv"
ARQ_AVISOS = PASTA_PROJETO / "dados" / "avisos.json"

COLUNAS = ["consultado_em", "rota", "origem", "destino", "data_ida", "data_volta", "preco", "companhia", "conexoes"]


def registrar_historico(rota: Rota, resultados: list[Resultado], momento: datetime, caminho: Path = ARQ_HISTORICO) -> None:
    novo = not caminho.exists()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("a", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        if novo:
            escritor.writerow(COLUNAS)
        for r in resultados:
            escritor.writerow([
                momento.isoformat(timespec="minutes"),
                rota.id,
                rota.origem,
                rota.destino,
                r.data_ida.isoformat(),
                r.data_volta.isoformat() if r.data_volta else "",
                r.preco,
                r.companhia,
                r.conexoes,
            ])


def ultima_leitura(rota_id: str, caminho: Path = ARQ_HISTORICO) -> tuple[str, int, float] | None:
    """(quando, menor preço, média) da verificação mais recente de uma rota, se houver."""
    if not caminho.exists():
        return None
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        linhas = [l for l in csv.DictReader(arquivo) if l["rota"] == rota_id]
    if not linhas:
        return None
    quando = max(l["consultado_em"] for l in linhas)
    precos = [int(l["preco"]) for l in linhas if l["consultado_em"] == quando]
    return quando, min(precos), sum(precos) / len(precos)


def carregar_avisos(caminho: Path = ARQ_AVISOS) -> dict[str, float]:
    if not caminho.exists():
        return {}
    return json.loads(caminho.read_text(encoding="utf-8"))


def salvar_avisos(avisos: dict[str, float], caminho: Path = ARQ_AVISOS) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(avisos, indent=2, sort_keys=True) + "\n", encoding="utf-8")
