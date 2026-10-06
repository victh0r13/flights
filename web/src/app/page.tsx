"use client";

import { useCallback, useEffect, useState } from "react";

import { CartaoRota } from "@/components/CartaoRota";
import { FormularioRota } from "@/components/FormularioRota";
import { ResultadoBusca, useBusca } from "@/components/PainelBusca";
import { StatusServidor } from "@/components/StatusServidor";
import { TesteEmail } from "@/components/TesteEmail";
import { Aviso, Botao, Modal } from "@/components/ui";
import { api, mensagemDeErro, type Rota, type StatusServidor as Status } from "@/lib/api";

export default function Pagina() {
  const [rotas, setRotas] = useState<Rota[] | null>(null);
  const [status, setStatus] = useState<Status | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [editando, setEditando] = useState<Rota | "nova" | null>(null);
  const [testando, setTestando] = useState<Rota | null>(null);
  const teste = useBusca();

  const carregar = useCallback(async () => {
    try {
      const [listaRotas, statusServidor] = await Promise.all([api.listarRotas(), api.statusServidor()]);
      setRotas(listaRotas);
      setStatus(statusServidor);
      setErro(null);
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- busca inicial dos dados da API
    carregar();
  }, [carregar]);

  async function executar(acao: () => Promise<unknown>) {
    try {
      await acao();
      await carregar();
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  }

  function testar(rota: Rota) {
    setTestando(rota);
    teste.iniciar({ ...rota, preco_alvo: rota.preco_alvo });
  }

  const alternarPausa = (rota: Rota) => executar(() => api.editarRota(rota.id, { ...rota, ativa: !rota.ativa }));
  const remover = (rota: Rota) =>
    confirm(`Remover a rota "${rota.nome}"? O histórico de preços continua guardado.`) && executar(() => api.removerRota(rota.id));

  const emailPadrao = rotas?.at(-1)?.email ?? "";

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="bg-sky-800 text-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-4 py-4">
          <div>
            <h1 className="text-xl font-bold">✈️ Rastreador de Passagens</h1>
            <p className="text-sm text-sky-100">O robô verifica suas rotas 4x por dia e avisa por e-mail.</p>
          </div>
          <StatusServidor status={status} aoSincronizar={carregar} />
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-4 py-8">
        {erro && <Aviso tipo="erro">{erro}</Aviso>}

        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-800">Minhas rotas</h2>
          <Botao variante="primario" onClick={() => setEditando("nova")}>
            + Nova rota
          </Botao>
        </div>

        {rotas === null && !erro && <p className="text-slate-500">Carregando…</p>}
        {rotas?.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">
            Nenhuma rota ainda. Clique em <strong>+ Nova rota</strong> para começar.
          </div>
        )}
        {rotas?.map((rota) => (
          <CartaoRota
            key={rota.id}
            rota={rota}
            aoTestar={() => testar(rota)}
            aoEditar={() => setEditando(rota)}
            aoAlternarPausa={() => alternarPausa(rota)}
            aoRemover={() => remover(rota)}
          />
        ))}

        {status?.pendente && (
          <Aviso tipo="info">
            Você tem alterações que o robô ainda não conhece. Clique em <strong>Sincronizar</strong> no topo para enviá-las.
          </Aviso>
        )}

        <details className="rounded-xl border border-slate-200 bg-white p-5">
          <summary className="cursor-pointer font-semibold text-slate-800">Testar envio de e-mail</summary>
          <div className="mt-4">
            <TesteEmail emailPadrao={emailPadrao} />
          </div>
        </details>
      </main>

      {editando && (
        <Modal titulo={editando === "nova" ? "Nova rota" : `Editar: ${editando.nome}`} aoFechar={() => setEditando(null)}>
          <FormularioRota
            rota={editando === "nova" ? null : editando}
            emailPadrao={emailPadrao}
            aoCancelar={() => setEditando(null)}
            aoSalvar={() => {
              setEditando(null);
              carregar();
            }}
          />
        </Modal>
      )}

      {testando && (
        <Modal titulo={`Busca de teste: ${testando.nome}`} aoFechar={() => setTestando(null)}>
          <p className="mb-4 text-sm text-slate-600">
            A mesma pesquisa que o robô faz, mas só mostra aqui (não envia e-mail nem salva histórico).
          </p>
          <ResultadoBusca busca={teste.busca} erro={teste.erro} precoAlvo={testando.preco_alvo} />
        </Modal>
      )}
    </div>
  );
}
