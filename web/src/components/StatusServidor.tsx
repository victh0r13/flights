"use client";

import { useState } from "react";

import { api, mensagemDeErro, type StatusServidor as Status } from "@/lib/api";
import { Botao } from "./ui";

/** Mostra se as rotas daqui já foram enviadas ao robô (GitHub) e permite sincronizar. */
export function StatusServidor({ status, aoSincronizar }: { status: Status | null; aoSincronizar: () => void }) {
  const [sincronizando, setSincronizando] = useState(false);
  const [mensagem, setMensagem] = useState<{ ok: boolean; texto: string } | null>(null);

  async function sincronizar() {
    setSincronizando(true);
    setMensagem(null);
    try {
      await api.sincronizar();
      setMensagem({ ok: true, texto: "Sincronizado: rotas enviadas e preços atualizados." });
      aoSincronizar();
    } catch (e) {
      setMensagem({ ok: false, texto: mensagemDeErro(e) });
    } finally {
      setSincronizando(false);
    }
  }

  if (!status) return null;
  if (!status.conectado)
    return <span className="text-sm text-amber-200">Não conectado ao GitHub (README, passo 3)</span>;

  return (
    <div className="flex flex-wrap items-center justify-end gap-3 text-sm">
      {mensagem && <span className={mensagem.ok ? "text-emerald-200" : "text-red-200"}>{mensagem.texto}</span>}
      <a href={`${status.endereco}/actions`} target="_blank" rel="noreferrer" className="text-sky-100 hover:underline">
        Robô no GitHub ↗
      </a>
      {status.pendente && <span className="rounded-full bg-amber-400 px-2 py-0.5 text-xs font-semibold text-amber-950">alterações não enviadas</span>}
      <Botao onClick={sincronizar} disabled={sincronizando}>
        {sincronizando ? "Sincronizando…" : "Sincronizar"}
      </Botao>
    </div>
  );
}
