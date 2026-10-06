"""Sincronização com o GitHub (o "servidor" onde o robô roda), via git.

- envia config/rotas.json para o GitHub (o robô passa a usar as rotas novas)
- baixa os commits do robô (dados/historico.csv com os preços mais recentes)

Usado pela API (interface web) e pelo assistente de terminal (configurar.py).
"""

import subprocess
import sys
from collections.abc import Callable

from .config import PASTA_PROJETO


class ErroSincronizacao(Exception):
    """Falha ao falar com o GitHub, com mensagem amigável."""


def git(*args: str, mostrar: bool = False) -> subprocess.CompletedProcess:
    """Roda um comando do git na pasta do projeto.

    mostrar=True deixa o git falar direto no terminal — necessário quando ele pode
    pedir login (na primeira vez abre uma janela do GitHub).
    """
    if mostrar:
        sys.stdout.flush()  # garante que nossas mensagens apareçam antes das do git
        return subprocess.run(["git", *args], cwd=PASTA_PROJETO)
    return subprocess.run(["git", *args], cwd=PASTA_PROJETO, capture_output=True, text=True, encoding="utf-8")


def endereco_github() -> str | None:
    """Página do repositório no GitHub, se esta pasta já estiver conectada."""
    if not (PASTA_PROJETO / ".git").exists():
        return None
    try:
        resultado = git("remote", "get-url", "origin")
    except FileNotFoundError:  # git não instalado
        return None
    return resultado.stdout.strip().removesuffix(".git") if resultado.returncode == 0 else None


def tem_alteracoes_pendentes() -> bool:
    """Há rotas alteradas aqui que o GitHub ainda não recebeu?"""
    if not endereco_github():
        return False
    arquivo_mudou = git("status", "--porcelain", "--", "config/rotas.json").stdout.strip() != ""
    commits_a_enviar = git("rev-list", "--count", "@{u}..HEAD").stdout.strip() not in ("", "0")
    return arquivo_mudou or commits_a_enviar


def sincronizar(avisar: Callable[[str], None] = print, mostrar_git: bool = False) -> None:
    """Envia as rotas e baixa o histórico. `avisar` recebe cada passo, para mostrar progresso."""
    if not endereco_github():
        raise ErroSincronizacao("Esta pasta ainda não está conectada ao GitHub (README, passo 3).")

    git("add", "config/rotas.json")
    if git("diff", "--cached", "--quiet").returncode != 0:
        git("commit", "-m", "Atualiza rotas")
        avisar("Alterações nas rotas preparadas para envio.")

    avisar("Baixando novidades do servidor (histórico de preços)...")
    baixar = git("pull", "--rebase", "--autostash")
    if baixar.returncode != 0:
        raise ErroSincronizacao(f"Não consegui baixar do GitHub: {baixar.stderr.strip()}")

    avisar("Enviando as rotas...")
    enviar = git("push", mostrar=mostrar_git)
    if enviar.returncode != 0:
        detalhe = "" if mostrar_git else f": {enviar.stderr.strip()}"
        raise ErroSincronizacao(f"Não consegui enviar para o GitHub{detalhe}")
    avisar("Tudo sincronizado.")
