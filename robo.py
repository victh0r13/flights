"""Robô de verificação: roda UMA rodada completa e termina.

É isto que o servidor (GitHub Actions) executa a cada 6 horas:
    1. lê as rotas de config/rotas.json
    2. para cada rota ativa, busca o preço de cada dia do período
    3. salva os preços em dados/historico.csv
    4. calcula menor preço / média e decide se deve avisar
    5. se sim, envia o e-mail e anota em dados/avisos.json

Também dá para rodar no seu PC:  python robo.py
"""

import os
import sys
from datetime import datetime

from rastreador.analise import decidir, resumir
from rastreador.armazenamento import carregar_avisos, registrar_historico, salvar_avisos
from rastreador.buscador import buscar_periodo
from rastreador.config import FUSO_BRASILIA, ErroConfig, carregar_rotas, formatar_reais, hoje
from rastreador.notificador import ErroEmail, enviar_email, montar_email


def main() -> int:
    momento = datetime.now(FUSO_BRASILIA)
    print(f"Rodada de verificação — {momento:%d/%m/%Y %H:%M} (Brasília)")

    try:
        rotas = carregar_rotas()
    except ErroConfig as erro:
        print(f"ERRO na configuração: {erro}")
        return 1

    # No servidor, sem os Secrets do Gmail nenhum alerta sairia. Melhor avisar já
    # na primeira execução do que descobrir só quando o preço cair.
    no_servidor = os.environ.get("GITHUB_ACTIONS") == "true"
    if no_servidor and not (os.environ.get("GMAIL_USUARIO") and os.environ.get("GMAIL_SENHA_APP")):
        print("ERRO: cadastre os Secrets GMAIL_USUARIO e GMAIL_SENHA_APP no GitHub (README, passo 4).")
        return 1

    # Esquece avisos de rotas que foram removidas
    avisos = {rota_id: valor for rota_id, valor in carregar_avisos().items() if rota_id in {r.id for r in rotas}}
    verificadas = falhas = emails = erros_email = 0

    for rota in rotas:
        print(f"\n[{rota.id}] {rota.nome}\n  {rota.descrever()}")
        if not rota.ativa:
            print("  pausada — pulando")
            continue
        if rota.fim < hoje():
            print("  período já passou — pode remover esta rota")
            continue

        resultados = buscar_periodo(rota)
        if not resultados:
            print("  nenhum preço encontrado (sem voos ou busca bloqueada)")
            falhas += 1
            continue
        verificadas += 1
        registrar_historico(rota, resultados, momento)

        resumo = resumir(resultados)
        print(f"  {resumo.dias_com_preco} dias com preço | menor {formatar_reais(resumo.mais_barato.preco)}"
              f" em {resumo.mais_barato.data_ida:%d/%m} | média {formatar_reais(resumo.media)}")

        decisao = decidir(rota, resumo, avisos.get(rota.id))
        print(f"  {'>>> AVISAR: ' if decisao.avisar else ''}{decisao.motivo}")

        if decisao.avisar:
            try:
                enviar_email(rota.email, *montar_email(rota, resumo, resultados, decisao.motivo))
                emails += 1
                print(f"  e-mail enviado para {rota.email}")
            except ErroEmail as erro:
                # não anota o aviso: na próxima rodada ele tenta enviar de novo
                print(f"  ERRO no e-mail: {erro}")
                erros_email += 1
                continue

        if decisao.valor_para_lembrar is None:
            avisos.pop(rota.id, None)
        else:
            avisos[rota.id] = decisao.valor_para_lembrar

    salvar_avisos(avisos)
    print(f"\nFim: {verificadas} rota(s) verificada(s), {emails} e-mail(s) enviado(s), "
          f"{falhas} busca(s) sem resultado, {erros_email} erro(s) de e-mail.")

    # Código de saída diferente de 0 faz o GitHub marcar a execução como "falhou"
    # e mandar um e-mail para você. Fazemos isso se o e-mail falhou (quase sempre é
    # senha/configuração) ou se NENHUMA busca funcionou (possível bloqueio do Google).
    # Uma falha passageira em uma rota só não gera alarme.
    return 1 if erros_email or (falhas and not verificadas) else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
