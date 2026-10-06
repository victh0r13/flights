"""Abre o Rastreador como um aplicativo: janela própria do Chrome/Edge, sem barra de endereço.

O que acontece ao abrir:
  1. liga a API (FastAPI, porta 8000) e a interface (Next.js, porta 3000) escondidas, sem janelas pretas
  2. espera as duas responderem
  3. abre o Chrome (ou o Edge) no "modo aplicativo" (--app=...)
  4. quando você fecha a janela, desliga os dois servidores

A extensão .pyw faz o Windows rodar este arquivo com pythonw.exe, que não abre terminal.
Por isso os erros aparecem numa caixa de mensagem, e os detalhes ficam nos logs.
"""

import ctypes
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PASTA = Path(__file__).resolve().parent
URL_APP = "http://localhost:3000"
URL_PRONTO = "http://127.0.0.1:3000/api/servidor"  # só responde quando interface E API estão de pé
ESPERA_MAXIMA = 120  # segundos (a primeira compilação do Next pode demorar)

# Fora do OneDrive: perfil do navegador e logs mudam o tempo todo e não devem sincronizar
PASTA_LOCAL = Path(os.environ.get("LOCALAPPDATA", PASTA)) / "RastreadorPassagens"
PERFIL_NAVEGADOR = PASTA_LOCAL / "perfil-navegador"
PASTA_LOGS = PASTA_LOCAL / "logs"

NAVEGADORES = [
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Microsoft/Edge/Application/msedge.exe",
]

SEM_JANELA = subprocess.CREATE_NO_WINDOW


def mensagem(texto: str, erro: bool = True) -> None:
    """Caixa de mensagem do Windows (pythonw não tem terminal para mostrar erros)."""
    icone = 0x10 if erro else 0x40
    ctypes.windll.user32.MessageBoxW(None, texto, "Rastreador de Passagens", icone)


def esta_respondendo(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as resposta:
            return resposta.status == 200
    except Exception:
        return False


def iniciar_servidores() -> list[subprocess.Popen]:
    PASTA_LOGS.mkdir(parents=True, exist_ok=True)
    python = PASTA / ".venv" / "Scripts" / "python.exe"
    pnpm = shutil.which("pnpm")
    if not python.exists():
        raise RuntimeError("Não encontrei o .venv. Siga o README, seção 'Interface web'.")
    if not pnpm:
        raise RuntimeError("Não encontrei o pnpm. Instale o Node.js e o pnpm (README, 'Interface web').")
    if not (PASTA / "web" / "node_modules").exists():
        raise RuntimeError("Falta instalar a interface: abra um terminal em web/ e rode 'pnpm install'.")

    api = subprocess.Popen(
        [str(python), "-m", "uvicorn", "api.main:app", "--reload", "--reload-dir", "api",
         "--reload-dir", "rastreador", "--port", "8000"],
        cwd=PASTA, creationflags=SEM_JANELA,
        stdout=open(PASTA_LOGS / "api.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT,
    )
    interface = subprocess.Popen(
        [pnpm, "dev"], cwd=PASTA / "web", creationflags=SEM_JANELA,
        stdout=open(PASTA_LOGS / "interface.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT,
    )
    return [api, interface]


def desligar(processos: list[subprocess.Popen]) -> None:
    """Encerra cada servidor e todos os processos filhos dele (/T = árvore inteira)."""
    for processo in processos:
        subprocess.run(["taskkill", "/PID", str(processo.pid), "/T", "/F"], capture_output=True, creationflags=SEM_JANELA)


def abrir_janela() -> subprocess.Popen:
    navegador = next((n for n in NAVEGADORES if n.exists()), None)
    if not navegador:
        raise RuntimeError("Não encontrei o Google Chrome nem o Microsoft Edge.")
    # Um perfil só do Rastreador faz o navegador abrir um processo separado, que só termina
    # quando esta janela fecha — é assim que sabemos a hora de desligar os servidores.
    return subprocess.Popen([
        str(navegador), f"--app={URL_APP}", f"--user-data-dir={PERFIL_NAVEGADOR}",
        "--window-size=1280,860", "--no-first-run", "--no-default-browser-check",
    ])


def main() -> None:
    # Se os servidores já estão ligados (app já aberto, ou iniciar.bat), só abre outra janela
    if esta_respondendo(URL_PRONTO):
        abrir_janela()
        return

    processos = []
    try:
        processos = iniciar_servidores()
        inicio = time.time()
        while not esta_respondendo(URL_PRONTO):
            if any(p.poll() is not None for p in processos):
                raise RuntimeError(f"Um dos servidores parou ao iniciar. Veja os logs em:\n{PASTA_LOGS}")
            if time.time() - inicio > ESPERA_MAXIMA:
                raise RuntimeError(f"Os servidores demoraram demais para iniciar. Veja os logs em:\n{PASTA_LOGS}")
            time.sleep(1)
        abrir_janela().wait()  # fica aqui até a janela ser fechada
    except RuntimeError as erro:
        mensagem(str(erro))
    except Exception as erro:
        mensagem(f"Erro inesperado: {type(erro).__name__}: {erro}")
    finally:
        desligar(processos)


if __name__ == "__main__":
    main()
    sys.exit(0)
