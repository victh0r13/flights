"""Testes do e-mail, sem internet: trocamos o servidor do Gmail por um "dublê" (mock).

O dublê imita o comportamento real do Gmail que descobrimos testando:
ao recusar a senha, ele responde 535 e FECHA a conexão.
"""

import smtplib
from datetime import date

import pytest

from rastreador.analise import resumir
from rastreador.buscador import Resultado
from rastreador.config import Rota
from rastreador.notificador import ErroEmail, enviar_email, montar_email


class GmailFalso:
    """Imita smtplib.SMTP_SSL. `problema` define como ele vai se comportar."""

    problema = None  # None = tudo certo
    enviadas = []

    def __init__(self, *args, **kwargs):
        self.fechada = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def ehlo(self):
        return 250, b"ok"

    def auth_plain(self, challenge=None):
        return f"\0{self.user}\0{self.password}"

    def auth(self, mecanismo, objeto_auth):
        if self.fechada:
            raise smtplib.SMTPServerDisconnected("Connection unexpectedly closed")
        if GmailFalso.problema == "senha_errada":
            self.fechada = True  # o Gmail de verdade fecha a conexão aqui
            raise smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")
        if GmailFalso.problema == "senha_normal":
            raise smtplib.SMTPAuthenticationError(534, b"5.7.9 Application-specific password required")
        return 235, b"Accepted"

    def login(self, usuario, senha):  # o jeito antigo: tenta PLAIN e depois LOGIN
        self.user, self.password = usuario, senha
        for _ in ("PLAIN", "LOGIN"):
            try:
                return self.auth(_, self.auth_plain)
            except smtplib.SMTPAuthenticationError as erro:
                ultimo = erro
        raise ultimo

    def send_message(self, mensagem):
        if GmailFalso.problema == "destino_invalido":
            raise smtplib.SMTPRecipientsRefused({mensagem["To"]: (553, b"5.1.3 not a valid RFC 5321 address")})
        if GmailFalso.problema == "caiu":
            raise smtplib.SMTPServerDisconnected("Connection unexpectedly closed")
        GmailFalso.enviadas.append(mensagem)


@pytest.fixture
def gmail(monkeypatch):
    """Troca o servidor de verdade pelo dublê durante o teste."""
    GmailFalso.problema = None
    GmailFalso.enviadas = []
    monkeypatch.setattr(smtplib, "SMTP_SSL", GmailFalso)
    return GmailFalso


def enviar(para="eu@exemplo.com", senha="abcd efgh ijkl mnop"):
    enviar_email(para, "Assunto", "texto", "<p>html</p>", usuario="eu@gmail.com", senha=senha)


def test_envio_normal(gmail):
    enviar()
    [mensagem] = gmail.enviadas
    assert mensagem["To"] == "eu@exemplo.com"
    assert mensagem["Subject"] == "Assunto"


def test_senha_errada_mostra_o_motivo_real_e_nao_conexao_fechada(gmail):
    gmail.problema = "senha_errada"
    with pytest.raises(ErroEmail, match="recusou o login"):
        enviar()


def test_o_jeito_antigo_escondia_o_erro_real(gmail):
    """Documenta o bug: com login(), a 2ª tentativa bate na conexão fechada."""
    gmail.problema = "senha_errada"
    with pytest.raises(smtplib.SMTPServerDisconnected):
        GmailFalso().login("eu@gmail.com", "senha-errada")


def test_senha_normal_no_lugar_da_senha_de_app(gmail):
    gmail.problema = "senha_normal"
    with pytest.raises(ErroEmail, match="exige uma SENHA DE APP"):
        enviar()


def test_destino_invalido(gmail):
    gmail.problema = "destino_invalido"
    with pytest.raises(ErroEmail, match="endereço de destino"):
        enviar(para="s")


def test_conexao_caiu(gmail):
    gmail.problema = "caiu"
    with pytest.raises(ErroEmail, match="encerrou a conexão"):
        enviar()


def test_sem_senha(gmail, monkeypatch):
    monkeypatch.delenv("GMAIL_SENHA_APP", raising=False)
    with pytest.raises(ErroEmail, match="Faltam"):
        enviar(senha="")


def test_email_de_alerta_escapa_html():
    rota = Rota(id="gru-rec", nome="Teste <b>", origem="GRU", destino="REC",
                periodo_inicio="2026-12-01", periodo_fim="2026-12-01", preco_alvo=1500, email="eu@exemplo.com")
    resultados = [Resultado(date(2026, 12, 1), None, 1346, "<script>alert(1)</script>", 0, "http://x?a=1&b=2")]
    assunto, texto, corpo_html = montar_email(rota, resumir(resultados), resultados, "menor preço atingiu a meta")
    assert "R$ 1.346" in assunto
    assert "Menor preço atingiu a meta" in corpo_html  # primeira letra maiúscula
    assert "<script>" not in corpo_html  # texto perigoso vira texto inofensivo
    assert "&lt;script&gt;" in corpo_html
