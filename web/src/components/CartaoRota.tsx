"use client";

import { useEffect, useState } from "react";

import { api, mensagemDeErro, type Historico, type Rota } from "@/lib/api";
import { data, dataHora, reais } from "@/lib/formato";
import { Aviso, Botao } from "./ui";

const CORES_SITUACAO = {
  ativa: "bg-emerald-100 text-emerald-800",
  pausada: "bg-amber-100 text-amber-800",
  encerrada: "bg-slate-200 text-slate-600",
};

export function CartaoRota({
  rota,
  aoTestar,
  aoEditar,
  aoAlternarPausa,
  aoRemover,
}: {
  rota: Rota;
  aoTestar: () => void;
  aoEditar: () => void;
  aoAlternarPausa: () => void;
  aoRemover: () => void;
}) {
  const [verHistorico, setVerHistorico] = useState(false);
  const leitura = rota.ultima_leitura;
  const valorMonitorado = leitura && (rota.regra === "menor_preco" ? leitura.menor : leitura.media);
  const naMeta = valorMonitorado !== null && valorMonitorado <= rota.preco_alvo;

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-slate-900">{rota.nome}</h3>
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${CORES_SITUACAO[rota.situacao]}`}>{rota.situacao}</span>
          </div>
          <p className="text-2xl font-bold tracking-tight text-slate-800">
            {rota.origem} <span className="text-slate-400">→</span> {rota.destino}
          </p>
          <p className="text-sm text-slate-600">
            Saída entre {data(rota.periodo_inicio)} e {data(rota.periodo_fim)} ·{" "}
            {rota.dias_de_viagem ? `ida e volta (${rota.dias_de_viagem} dias)` : "só ida"} · {rota.adultos} adulto(s)
            {rota.max_conexoes === 0 ? " · só direto" : rota.max_conexoes === 1 ? " · até 1 conexão" : ""}
          </p>
          <p className="text-sm text-slate-600">
            Meta: <strong>{reais(rota.preco_alvo)}</strong> ({rota.regra === "menor_preco" ? "menor preço" : "média do período"}) · alertas para {rota.email}
          </p>
        </div>

        <div className="min-w-48 rounded-lg bg-slate-50 px-4 py-3 text-right">
          {leitura ? (
            <>
              <div className="text-xs text-slate-500">Última verificação do robô · {dataHora(leitura.quando)}</div>
              <div className={`text-xl font-bold ${naMeta ? "text-emerald-700" : "text-slate-900"}`}>{reais(leitura.menor)}</div>
              <div className="text-xs text-slate-500">menor · média {reais(leitura.media)}</div>
            </>
          ) : (
            <div className="text-sm text-slate-500">
              Sem verificações ainda.
              <br />
              Sincronize para baixar.
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Botao variante="primario" onClick={aoTestar}>
          Testar busca agora
        </Botao>
        <Botao onClick={() => setVerHistorico((v) => !v)}>{verHistorico ? "Esconder histórico" : "Histórico"}</Botao>
        <Botao onClick={aoEditar}>Editar</Botao>
        <Botao onClick={aoAlternarPausa}>{rota.ativa ? "Pausar" : "Reativar"}</Botao>
        <Botao variante="perigo" onClick={aoRemover}>
          Remover
        </Botao>
      </div>

      {verHistorico && <HistoricoRota rotaId={rota.id} precoAlvo={rota.preco_alvo} />}
    </article>
  );
}

function HistoricoRota({ rotaId, precoAlvo }: { rotaId: string; precoAlvo: number }) {
  const [historico, setHistorico] = useState<Historico | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    api.historico(rotaId).then(setHistorico).catch((e) => setErro(mensagemDeErro(e)));
  }, [rotaId]);

  if (erro) return <div className="mt-4"><Aviso tipo="erro">{erro}</Aviso></div>;
  if (!historico) return <p className="mt-4 text-sm text-slate-500">Carregando…</p>;
  if (historico.consultas.length === 0)
    return <p className="mt-4 text-sm text-slate-500">O robô ainda não verificou esta rota (ou falta sincronizar).</p>;

  // Barras vão do menor ao maior valor visto, para pequenas variações ficarem visíveis
  const valores = historico.consultas.map((c) => c.menor);
  const minimo = Math.min(...valores);
  const faixa = Math.max(...valores) - minimo || 1;
  return (
    <div className="mt-4 rounded-lg border border-slate-200">
      <div className="border-b border-slate-200 px-4 py-2 text-sm font-medium text-slate-700">
        Menor preço em cada verificação do robô (mais recente primeiro)
      </div>
      <ul className="max-h-72 overflow-auto px-4 py-2 text-sm">
        {historico.consultas.map((c) => (
          <li key={c.quando} className="flex items-center gap-3 py-1">
            <span className="w-28 shrink-0 text-slate-500">{dataHora(c.quando)}</span>
            <span className="w-24 shrink-0 text-right font-medium">{reais(c.menor)}</span>
            <span className="h-2 rounded bg-sky-400" style={{ width: `${8 + ((c.menor - minimo) / faixa) * 52}%` }} />
            <span className="shrink-0 text-xs text-slate-400">média {reais(c.media)}</span>
            {c.menor <= precoAlvo && <span className="text-xs font-semibold text-emerald-700">na meta</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
