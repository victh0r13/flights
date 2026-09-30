"""Montagem e envio do e-mail de alerta, pelo Gmail.

O envio usa SMTP, o protocolo padrão de e-mail. O Gmail exige uma "senha de app"
(uma senha especial só para programas, diferente da sua senha normal). Ela nunca
fica no código: vem das variáveis de ambiente GMAIL_USUARIO e GMAIL_SENHA_APP,
que no servidor são os "Secrets" do GitHub.
"""

import html
import os
import smtplib
from email.message import EmailMessage

from . import aeroportos
from .analise import Resumo
from .buscador import Resultado
from .config import Rota, formatar_reais

SERVIDOR_SMTP = "smtp.gmail.com"
PORTA_SMTP = 465  # porta com criptografia (SSL)


class ErroEmail(Exception):
    """Falha no envio, com mensagem amigável."""


def descrever_conexoes(n: int) -> str:
    return "direto" if n == 0 else "1 conexão" if n == 1 else f"{n} conexões"


def montar_email(rota: Rota, resumo: Resumo, resultados: list[Resultado], motivo: str) -> tuple[str, str, str]:
    """Devolve (assunto, texto simples, html)."""
    barato = resumo.mais_barato
    motivo = motivo[:1].upper() + motivo[1:]
    assunto = f"✈️ {rota.origem}→{rota.destino} por {formatar_reais(barato.preco)} — {rota.nome}"

    linhas_texto = [
        f"{rota.nome}: {motivo}",
        rota.descrever(),
        "",
        f"Mais barato: {formatar_reais(barato.preco)} saindo {barato.data_ida:%d/%m/%Y} ({barato.companhia})",
        f"Média do período: {formatar_reais(resumo.media)} ({resumo.dias_com_preco} dias pesquisados)",
        "",
        "Preço por data de ida:",
    ]
    linhas_tabela = []
    for r in sorted(resultados, key=lambda r: r.data_ida):
        abaixo = r.preco <= rota.preco_alvo
        volta = f" (volta {r.data_volta:%d/%m})" if r.data_volta else ""
        linhas_texto.append(f"  {r.data_ida:%d/%m}{volta}: {formatar_reais(r.preco)} {r.companhia}{'  <-- na meta' if abaixo else ''}")
        estilo = "background:#e6f4ea;font-weight:bold" if abaixo else ""
        linhas_tabela.append(
            f'<tr style="{estilo}"><td>{r.data_ida:%d/%m/%Y}{volta}</td>'
            f"<td>{formatar_reais(r.preco)}</td><td>{html.escape(r.companhia)}</td>"
            f"<td>{descrever_conexoes(r.conexoes)}</td>"
            f'<td><a href="{html.escape(r.link)}">ver</a></td></tr>'
        )
    linhas_texto += ["", f"Abrir no Google Flights: {barato.link}"]

    corpo_html = f"""\
<div style="font-family:Arial,sans-serif;max-width:640px">
  <h2 style="margin-bottom:4px">{html.escape(rota.nome)}</h2>
  <p style="margin-top:0;color:#555">{html.escape(aeroportos.nome(rota.origem))} → {html.escape(aeroportos.nome(rota.destino))}</p>
  <p style="font-size:16px"><b>{html.escape(motivo)}</b></p>
  <p>Mais barato: <b>{formatar_reais(barato.preco)}</b> saindo em {barato.data_ida:%d/%m/%Y} ({html.escape(barato.companhia)})<br>
     Média do período: {formatar_reais(resumo.media)} · meta: {formatar_reais(rota.preco_alvo)}</p>
  <p><a href="{html.escape(barato.link)}" style="background:#1a73e8;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none">Abrir no Google Flights</a></p>
  <table cellpadding="6" style="border-collapse:collapse;font-size:14px">
    <tr style="background:#f1f3f4"><th align="left">Ida</th><th align="left">Preço</th><th align="left">Companhia</th><th align="left">Voo</th><th></th></tr>
    {"".join(linhas_tabela)}
  </table>
  <p style="color:#888;font-size:12px">{html.escape(rota.descrever())}<br>
     Preços do Google Flights no momento da consulta; podem mudar a qualquer hora.</p>
</div>"""
    return assunto, "\n".join(linhas_texto), corpo_html


def enviar_email(para: str, assunto: str, texto: str, corpo_html: str,
                 usuario: str | None = None, senha: str | None = None) -> None:
    usuario = usuario or os.environ.get("GMAIL_USUARIO")
    senha = senha or os.environ.get("GMAIL_SENHA_APP")
    if not usuario or not senha:
        raise ErroEmail("Faltam o Gmail e/ou a senha de app (no servidor: Secrets do GitHub, README passo 4).")

    mensagem = EmailMessage()
    mensagem["Subject"] = assunto
    mensagem["From"] = f"Rastreador de Passagens <{usuario}>"
    mensagem["To"] = para
    mensagem.set_content(texto)  # versão simples, para leitores de e-mail sem HTML
    mensagem.add_alternative(corpo_html, subtype="html")

    try:
        with smtplib.SMTP_SSL(SERVIDOR_SMTP, PORTA_SMTP, timeout=30) as servidor:
            servidor.login(usuario, senha.replace(" ", ""))  # o Google mostra a senha com espaços
            servidor.send_message(mensagem)
    except smtplib.SMTPAuthenticationError:
        raise ErroEmail("O Gmail recusou o login. Confira o e-mail e a SENHA DE APP (não é a senha normal).") from None
    except (smtplib.SMTPException, OSError) as erro:
        raise ErroEmail(f"Não foi possível enviar o e-mail: {erro}") from None
