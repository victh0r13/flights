"""Assistente de configuração — é este arquivo que vira o Configurar.exe.

Um menu no terminal (cmd) que faz perguntas simples e grava as respostas em
config/rotas.json. Depois, a opção "Sincronizar" envia o arquivo para o GitHub,
onde o robô (robo.py) passa a usá-lo.
"""

import os
import re
import sys
from datetime import date, datetime

from rastreador import aeroportos
from rastreador.analise import Resumo, decidir, resumir
from rastreador.armazenamento import ultima_leitura
from rastreador.buscador import Resultado, buscar_periodo, datas_do_periodo
from rastreador.config import (
    MAX_DIAS_PERIODO,
    PASTA_PROJETO,
    REGRAS,
    ErroConfig,
    Rota,
    carregar_rotas,
    email_valido,
    formatar_reais,
    gerar_id,
    hoje,
    salvar_rotas,
)
from rastreador import sincronizacao
from rastreador.notificador import ErroEmail, enviar_email
from rastreador.sincronizacao import ErroSincronizacao, endereco_github, git

LINHA = "=" * 64
SEGUNDOS_POR_DIA = 4  # estimativa para avisar quanto tempo a busca vai levar
DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


# ------------------------------------------------------------ perguntas

def titulo(texto: str) -> None:
    print(f"\n{LINHA}\n  {texto}\n{LINHA}")


def perguntar(texto: str, padrao: str | None = None) -> str:
    sufixo = f" [{padrao}]" if padrao else ""
    resposta = input(f"{texto}{sufixo}: ").strip()
    return resposta or (padrao or "")


def perguntar_numero(texto: str, minimo: int, maximo: int, padrao: int | None = None) -> int:
    while True:
        resposta = perguntar(texto, str(padrao) if padrao is not None else None)
        resposta = resposta.replace("R$", "").replace(".", "").replace(",", "").strip()
        if resposta.isdigit() and minimo <= int(resposta) <= maximo:
            return int(resposta)
        print(f"  → Digite um número entre {minimo} e {maximo}.")


def perguntar_opcao(texto: str, opcoes: list[str]) -> int:
    """Mostra opções numeradas e devolve o índice escolhido (começando em 0)."""
    print(texto)
    for n, opcao in enumerate(opcoes, 1):
        print(f"  {n}) {opcao}")
    return perguntar_numero("Escolha", 1, len(opcoes)) - 1


def confirmar(texto: str, padrao: bool = True) -> bool:
    resposta = perguntar(f"{texto} (s/n)", "s" if padrao else "n").lower()
    return resposta.startswith("s")


def perguntar_email(texto: str, padrao: str | None = None) -> str:
    while True:
        resposta = perguntar(texto, padrao)
        if padrao and resposta.lower() in ("s", "sim"):  # a pessoa quis dizer "sim, esse mesmo"
            return padrao
        if email_valido(resposta):
            return resposta
        print("  → Isso não parece um e-mail. Exemplo: nome@gmail.com")


def ler_data(texto: str) -> date | None:
    """Aceita 25/12/2026, 25/12/26, 25/12 (ano automático) ou 2026-12-25."""
    texto = texto.strip()
    for formato in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            pass
    try:
        dia_mes = datetime.strptime(texto, "%d/%m")
    except ValueError:
        return None
    candidata = date(hoje().year, dia_mes.month, dia_mes.day)
    return candidata if candidata >= hoje() else date(hoje().year + 1, dia_mes.month, dia_mes.day)


def perguntar_data(texto: str, minima: date) -> date:
    while True:
        data = ler_data(perguntar(texto))
        if data is None:
            print("  → Use o formato dia/mês/ano, ex.: 15/12/2026")
        elif data < minima:
            print(f"  → A data precisa ser a partir de {minima:%d/%m/%Y}.")
        else:
            return data


def perguntar_aeroporto(texto: str) -> str:
    while True:
        opcoes = aeroportos.procurar(perguntar(texto))
        if not opcoes:
            print("  → Não encontrei. Tente o nome da cidade (ex.: Recife) ou o código de 3 letras (ex.: REC).")
            continue
        if len(opcoes) == 1:
            codigo, descricao = opcoes[0]
            print(f"  → {codigo} — {descricao}")
            return codigo
        escolha = perguntar_opcao("  Encontrei mais de um aeroporto:", [f"{c} — {d}" for c, d in opcoes])
        return opcoes[escolha][0]


# ------------------------------------------------------------ buscas

def pesquisar_com_progresso(rota: Rota) -> tuple[list[Resultado], Resumo | None]:
    dias = len(datas_do_periodo(rota))
    print(f"\nPesquisando {dias} data(s) no Google Flights (cerca de {dias * SEGUNDOS_POR_DIA} segundos)...")

    def mostrar(data_ida: date, resultado: Resultado | None) -> None:
        if resultado:
            print(f"  {data_ida:%d/%m} ({DIAS_SEMANA[data_ida.weekday()]}): {formatar_reais(resultado.preco):>11}  {resultado.companhia}")
        else:
            print(f"  {data_ida:%d/%m} ({DIAS_SEMANA[data_ida.weekday()]}): sem voos encontrados")

    resultados = buscar_periodo(rota, ao_buscar=mostrar)
    resumo = resumir(resultados)
    if resumo:
        barato = resumo.mais_barato
        print(f"\n  Menor preço: {formatar_reais(barato.preco)} saindo em {barato.data_ida:%d/%m/%Y} ({barato.companhia})")
        print(f"  Média:       {formatar_reais(resumo.media)}")
        print(f"  Maior preço: {formatar_reais(resumo.maior_preco)}")
    else:
        print("\n  Nenhum preço encontrado. Confira os aeroportos e as datas.")
    return resultados, resumo


# ------------------------------------------------------------ ações do menu

def ver_rotas(rotas: list[Rota]) -> None:
    titulo("Minhas rotas")
    if not rotas:
        print("Nenhuma rota cadastrada ainda. Use a opção 2.")
        return
    for n, rota in enumerate(rotas, 1):
        situacao = "PAUSADA" if not rota.ativa else "ENCERRADA (período passou)" if rota.fim < hoje() else "ativa"
        print(f"\n{n}. {rota.nome}  [{situacao}]")
        print(f"   {rota.descrever()}")
        print(f"   alertas para: {rota.email}")
        leitura = ultima_leitura(rota.id)
        if leitura:
            quando, menor, media = leitura
            print(f"   última verificação: {datetime.fromisoformat(quando):%d/%m %H:%M} — "
                  f"menor {formatar_reais(menor)}, média {formatar_reais(media)}")


def cadastrar_rota(rotas: list[Rota]) -> bool:
    titulo("Nova rota")
    print("Responda às perguntas. Quando houver [algo entre colchetes], é só apertar")
    print("Enter para aceitar aquele valor.\n")

    origem = perguntar_aeroporto("De onde você sai? (cidade ou código)")
    while (destino := perguntar_aeroporto("Para onde vai?")) == origem:
        print("  → O destino precisa ser diferente da origem.")

    print("\nPERÍODO — em quais datas você aceitaria SAIR (data de ida)?")
    print(f"Quanto maior o período, mais demora cada busca (máximo {MAX_DIAS_PERIODO} dias).")
    inicio = perguntar_data("Primeira data de ida possível (dd/mm/aaaa)", minima=hoje())
    while True:
        fim = perguntar_data("Última data de ida possível (dd/mm/aaaa)", minima=inicio)
        if (fim - inicio).days + 1 <= MAX_DIAS_PERIODO:
            break
        print(f"  → O período pode ter no máximo {MAX_DIAS_PERIODO} dias.")

    dias_de_viagem = None
    if perguntar_opcao("\nTipo de passagem:", ["Só ida", "Ida e volta"]) == 1:
        dias_de_viagem = perguntar_numero("Quantos dias de viagem? (a volta será esse número de dias após a ida)", 1, 90)

    adultos = perguntar_numero("\nQuantos adultos?", 1, 9, padrao=1)
    conexoes = [None, 0, 1][perguntar_opcao("\nConexões:", ["Tanto faz", "Só voo direto", "No máximo 1 conexão"])]

    print("\nREGRA DO ALERTA — quando você quer receber o e-mail?")
    regras = list(REGRAS)
    regra = regras[perguntar_opcao("", [REGRAS[r] for r in regras])]

    rota = Rota(
        id=gerar_id(origem, destino, rotas), nome="", origem=origem, destino=destino,
        periodo_inicio=inicio.isoformat(), periodo_fim=fim.isoformat(), preco_alvo=1,
        email="a@b.co", regra=regra, dias_de_viagem=dias_de_viagem, adultos=adultos, max_conexoes=conexoes,
    )

    sugestao = None
    if confirmar("\nQuer que eu pesquise os preços de hoje para ajudar a escolher o valor alvo?"):
        _, resumo = pesquisar_com_progresso(rota)
        if resumo:
            base = resumo.mais_barato.preco if regra == "menor_preco" else resumo.media
            sugestao = int(base * 0.9 // 10 * 10)  # 10% abaixo do valor de hoje, arredondado
            print(f"\n  Dica: {formatar_reais(sugestao)} é 10% abaixo do valor de hoje.")

    total = " (total de todos os passageiros" + (", ida + volta)" if dias_de_viagem else ")")
    rota.preco_alvo = perguntar_numero(f"\nValor alvo em R${total}", 50, 500_000, padrao=sugestao)

    ultimo_email = rotas[-1].email if rotas else None
    rota.email = perguntar_email("\nE-mail que vai receber os alertas", ultimo_email)

    cidade = lambda codigo: aeroportos.nome(codigo).split(" (")[0]  # "Lisboa (Humberto Delgado)" -> "Lisboa"
    nome_sugerido = f"{cidade(origem)} → {cidade(destino)}"
    rota.nome = perguntar("Um apelido para esta rota", nome_sugerido)

    try:
        rota.validar()  # rede de segurança: as perguntas acima já conferem cada resposta
    except ErroConfig as erro:
        print(f"[ERRO] {erro}")
        return False

    print(f"\nResumo:\n  {rota.nome}\n  {rota.descrever()}\n  alertas para {rota.email}")
    if not confirmar("Salvar esta rota?"):
        print("Cancelado.")
        return False
    rotas.append(rota)
    salvar_rotas(rotas)
    print("[OK] Rota salva! Lembre de usar a opção 5 para enviar ao servidor.")
    return True


def escolher_rota(rotas: list[Rota], acao: str) -> Rota | None:
    if not rotas:
        print("Nenhuma rota cadastrada ainda.")
        return None
    nomes = [f"{r.nome} — {r.origem}→{r.destino}{' (pausada)' if not r.ativa else ''}" for r in rotas]
    indice = perguntar_opcao(f"Qual rota quer {acao}?", nomes + ["Voltar"])
    return None if indice == len(rotas) else rotas[indice]


def gerenciar_rota(rotas: list[Rota]) -> bool:
    titulo("Pausar / reativar / remover")
    rota = escolher_rota(rotas, "alterar")
    if not rota:
        return False
    if perguntar_opcao("O que fazer?", ["Reativar" if not rota.ativa else "Pausar", "Remover", "Voltar"]) == 0:
        rota.ativa = not rota.ativa
        print("[OK] Rota " + ("reativada." if rota.ativa else "pausada (o robô vai pular esta rota)."))
    elif confirmar(f"Remover '{rota.nome}' de vez?", padrao=False):
        rotas.remove(rota)
        print("[OK] Rota removida.")
    else:
        return False
    salvar_rotas(rotas)
    return True


def testar_busca(rotas: list[Rota]) -> None:
    titulo("Busca de teste")
    print("Faz a mesma busca que o robô faz, mas só mostra na tela (não envia e-mail).\n")
    rota = escolher_rota(rotas, "testar")
    if not rota:
        return
    _, resumo = pesquisar_com_progresso(rota)
    if resumo:
        decisao = decidir(rota, resumo, ultimo_aviso=None)
        print(f"\n  Meta: {formatar_reais(rota.preco_alvo)} → "
              + ("o robô ENVIARIA um alerta agora." if decisao.avisar else "ainda não enviaria alerta."))


def testar_email() -> None:
    titulo("Testar envio de e-mail")
    print("Use um Gmail e uma SENHA DE APP (não é a sua senha normal).")
    print("Como criar: https://myaccount.google.com/apppasswords  (veja o README, passo 2)")
    print("Nada do que você digitar aqui fica salvo.\n")
    usuario = perguntar_email("Seu Gmail (remetente)")

    # A senha aparece na tela de propósito. No modo invisível (getpass), o cmd lê tecla
    # por tecla e não entende Ctrl+V como "colar": chegava um caractere de controle no
    # lugar da senha. Como é uma senha de app (só serve para e-mail e pode ser apagada
    # a qualquer momento), ver o que foi colado vale mais que escondê-lo.
    print("\nAgora a senha de app: cole com Ctrl+V (ou botão direito do mouse) e aperte Enter.")
    while True:
        senha = perguntar("Senha de app").replace(" ", "")
        if len(senha) == 16:
            break
        print(f"  [!] A senha de app tem 16 letras, mas chegaram {len(senha)} caractere(s).")
        if not confirmar("  Colar/digitar de novo?"):
            break

    para = perguntar_email("\nPara qual e-mail mandar o teste? (Enter = o mesmo)", usuario)
    print("\nEnviando...")
    try:
        enviar_email(
            para, "✈️ Teste do Rastreador de Passagens",
            "Se você recebeu este e-mail, o envio está funcionando!",
            "<p>Se você recebeu este e-mail, o envio está <b>funcionando</b>! ✈️</p>",
            usuario=usuario, senha=senha,
        )
        print(f"\n[OK] E-mail enviado para {para}. Confira a caixa de entrada (e o spam).")
        if endereco := endereco_github():
            print(f"  Cadastre os mesmos dados nos Secrets do GitHub: {endereco}/settings/secrets/actions")
        else:
            print("  Depois de conectar ao GitHub (opção 7), cadastre esses dados nos Secrets de lá.")
    except ErroEmail as erro:
        print(f"\n[ERRO] {erro}")


# ------------------------------------------------------------ GitHub (servidor)
# O "git" é o programa que envia e baixa arquivos do GitHub. O assistente
# roda os comandos por você; docs/COMO_FUNCIONA.md explica cada um.

def conectar_github() -> None:
    titulo("Conectar ao GitHub (só na primeira vez)")
    if endereco := endereco_github():
        print(f"Esta pasta já está conectada a {endereco}")
        print(f"Robô trabalhando: {endereco}/actions")
        return

    print("O GitHub guarda o projeto e roda o robô de graça, mesmo com o PC desligado.\n")
    print("1. Crie uma conta em https://github.com (se ainda não tiver).")
    print("2. Crie um repositório em https://github.com/new")
    print("     • Repository name: rastreador-passagens (ou outro nome)")
    print("     • marque PRIVATE (suas rotas e e-mails ficam visíveis só para você)")
    print("     • deixe o resto como está e clique em 'Create repository'")
    print("3. Copie o endereço HTTPS que aparece, parecido com:")
    print("     https://github.com/seu-usuario/rastreador-passagens.git\n")
    url = perguntar("Cole o endereço aqui (ou Enter para voltar)").rstrip("/")
    if not url:
        return
    if not re.fullmatch(r"https://github\.com/[A-Za-z0-9-]+/[A-Za-z0-9._-]+", url):
        print("[ERRO] Esse endereço não parece de um repositório do GitHub (deve começar com https://github.com/).")
        return
    endereco = url.removesuffix(".git")

    try:
        if not (PASTA_PROJETO / ".git").exists():
            git("init", "-b", "main")
        if not git("config", "user.email").stdout.strip():
            print("\nO git precisa de um nome e e-mail para assinar os envios (só nesta pasta).")
            git("config", "user.name", perguntar("Seu nome"))
            git("config", "user.email", perguntar_email("Seu e-mail"))
        git("add", "-A")
        git("commit", "-m", "Primeira versão do rastreador")
        git("remote", "add", "origin", endereco + ".git")
        print("\nEnviando o projeto... Se abrir uma janela pedindo login no GitHub, faça o login.\n")
        if git("push", "-u", "origin", "main", mostrar=True).returncode != 0:
            git("remote", "remove", "origin")  # desfaz, para poder tentar de novo
            print("\n[ERRO] O envio falhou. Confira o endereço e o login e tente de novo.")
            return
    except FileNotFoundError:
        print("[ERRO] O Git não está instalado. Baixe em https://git-scm.com/download/win e tente de novo.")
        return

    print("\n[OK] Projeto enviado! Último passo: guardar os dados do e-mail no GitHub.")
    print(f"  Abra {endereco}/settings/secrets/actions e crie dois 'New repository secret':")
    print("    GMAIL_USUARIO   = seu Gmail")
    print("    GMAIL_SENHA_APP = a senha de app (README, passo 2)")
    print(f"\n  Depois acompanhe o robô em {endereco}/actions")


def sincronizar() -> bool:
    """Envia config/rotas.json para o GitHub e baixa o histórico novo do robô."""
    titulo("Sincronizar com o servidor (GitHub)")
    try:
        sincronizacao.sincronizar(avisar=lambda passo: print(f"• {passo}"), mostrar_git=True)
    except ErroSincronizacao as erro:
        print(f"[ERRO] {erro}")
        return False
    print(f"[OK] O robô roda em seguida com as rotas novas: {endereco_github()}/actions")
    return True


# ------------------------------------------------------------ menu

def menu() -> None:
    rotas = carregar_rotas()
    pendente = False  # há alteração que ainda não foi para o servidor?
    while True:
        titulo(f"RASTREADOR DE PASSAGENS — {len(rotas)} rota(s) cadastrada(s)")
        if not endereco_github():
            print("  [!] Ainda não conectado ao servidor: quando quiser, use a opção 7.\n")
        print("  1) Ver minhas rotas")
        print("  2) Cadastrar nova rota")
        print("  3) Pausar / reativar / remover rota")
        print("  4) Fazer uma busca de teste agora")
        print("  5) Sincronizar com o servidor" + ("   ← você tem alterações não enviadas" if pendente else ""))
        print("  6) Testar envio de e-mail")
        print("  7) Conectar ao GitHub (primeira vez)")
        print("  0) Sair")
        escolha = perguntar("\nOpção")

        if escolha == "1":
            ver_rotas(rotas)
        elif escolha == "2":
            pendente |= cadastrar_rota(rotas)
        elif escolha == "3":
            pendente |= gerenciar_rota(rotas)
        elif escolha == "4":
            testar_busca(rotas)
        elif escolha == "5":
            if sincronizar():
                pendente = False
                rotas = carregar_rotas()
        elif escolha == "6":
            testar_email()
        elif escolha == "7":
            conectar_github()
        elif escolha == "0":
            if pendente and confirmar("Você tem alterações não enviadas ao servidor. Enviar agora?"):
                sincronizar()
            return
        else:
            print("Opção inválida.")
            continue
        input("\n(Enter para voltar ao menu)")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if os.name == "nt":
        os.system("title Rastreador de Passagens")
    try:
        menu()
    except KeyboardInterrupt:
        print("\nAté logo!")
    except ErroConfig as erro:
        print(f"\n[ERRO] Problema no arquivo de rotas: {erro}")
        input("\nEnter para fechar.")
    except Exception as erro:  # no .exe, evita a janela fechar sem mostrar o erro
        print(f"\n[ERRO] Erro inesperado: {type(erro).__name__}: {erro}")
        input("\nEnter para fechar.")


if __name__ == "__main__":
    main()
