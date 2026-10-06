"use client";

import { useEffect, useRef, useState } from "react";

import { api, mensagemDeErro, type Busca, type BuscaEntrada } from "@/lib/api";
import { conexoes, data, diaMes, diaSemana, reais } from "@/lib/formato";
import { Aviso } from "./ui";

const INTERVALO_MS = 1500;

/**
 * Inicia uma busca de teste e acompanha o progresso.
 * A API devolve um id na hora; daqui perguntamos o andamento a cada 1,5 s ("polling").
 */
export function useBusca() {
  const [busca, setBusca] = useState<Busca | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const alvo = useRef<number | null>(null);

  async function iniciar(entrada: BuscaEntrada) {
    setErro(null);
    setBusca(null);
    alvo.current = entrada.preco_alvo;
    try {
      setBusca(await api.iniciarBusca(entrada));
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  }

  useEffect(() => {
    if (busca?.status !== "rodando") return;
    const proxima = setTimeout(async () => {
      try {
        setBusca(await api.acompanharBusca(busca.id, alvo.current));
      } catch (e) {
        setErro(mensagemDeErro(e));
      }
    }, INTERVALO_MS);
    return () => clearTimeout(proxima);
  }, [busca]);

  return { busca, erro, iniciar, rodando: busca?.status === "rodando" };
}

export function ResultadoBusca({ busca, erro, precoAlvo }: { busca: Busca | null; erro: string | null; precoAlvo: number | null }) {
  if (erro) return <Aviso tipo="erro">{erro}</Aviso>;
  if (!busca) return null;

  const progresso = busca.total ? Math.round((busca.feitos / busca.total) * 100) : 100;
  const segundosRestantes = (busca.total - busca.feitos) * 3;

  return (
    <div className="space-y-4">
      {busca.status === "rodando" && (
        <div>
          <div className="mb-1 flex justify-between text-sm text-slate-600">
            <span>
              Pesquisando no Google Flights… {busca.feitos} de {busca.total} dias
            </span>
            <span>~{segundosRestantes}s</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-200">
            <div className="h-full bg-sky-500 transition-all" style={{ width: `${progresso}%` }} />
          </div>
        </div>
      )}
      {busca.status === "erro" && <Aviso tipo="erro">A busca falhou: {busca.erro}</Aviso>}

      {busca.resumo && (
        <div className="grid grid-cols-3 gap-3">
          <Numero rotulo="Menor preço" valor={reais(busca.resumo.menor)} detalhe={`saindo ${data(busca.resumo.data_menor)}`} />
          <Numero rotulo="Média" valor={reais(busca.resumo.media)} detalhe={`${busca.resultados.length} dias com preço`} />
          <Numero rotulo="Maior preço" valor={reais(busca.resumo.maior)} />
        </div>
      )}

      {busca.decisao && (
        <Aviso tipo={busca.decisao.avisar ? "sucesso" : "info"}>
          {busca.decisao.avisar ? "O robô ENVIARIA um alerta agora: " : "Ainda não enviaria alerta: "}
          {busca.decisao.motivo}
        </Aviso>
      )}

      {busca.status === "concluida" && busca.resultados.length === 0 && (
        <Aviso tipo="info">Nenhum voo encontrado. Confira os aeroportos e as datas.</Aviso>
      )}

      {busca.resultados.length > 0 && (
        <div className="max-h-80 overflow-auto rounded-md border border-slate-200">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-slate-50 text-left text-slate-600">
              <tr>
                <th className="px-3 py-2">Ida</th>
                <th className="px-3 py-2">Volta</th>
                <th className="px-3 py-2">Preço</th>
                <th className="px-3 py-2">Companhia</th>
                <th className="px-3 py-2">Voo</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {busca.resultados.map((r) => {
                const naMeta = precoAlvo !== null && r.preco <= precoAlvo;
                return (
                  <tr key={r.data_ida} className={`border-t border-slate-100 ${naMeta ? "bg-emerald-50 font-medium" : ""}`}>
                    <td className="px-3 py-1.5">
                      {diaMes(r.data_ida)} <span className="text-slate-400">{diaSemana(r.data_ida)}</span>
                    </td>
                    <td className="px-3 py-1.5">{r.data_volta ? diaMes(r.data_volta) : "—"}</td>
                    <td className="px-3 py-1.5">{reais(r.preco)}</td>
                    <td className="px-3 py-1.5">{r.companhia}</td>
                    <td className="px-3 py-1.5">{conexoes(r.conexoes)}</td>
                    <td className="px-3 py-1.5">
                      {r.link && (
                        <a href={r.link} target="_blank" rel="noreferrer" className="text-sky-700 hover:underline">
                          ver
                        </a>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function Numero({ rotulo, valor, detalhe }: { rotulo: string; valor: string; detalhe?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
      <div className="text-xs uppercase tracking-wide text-slate-500">{rotulo}</div>
      <div className="text-lg font-semibold text-slate-900">{valor}</div>
      {detalhe && <div className="text-xs text-slate-500">{detalhe}</div>}
    </div>
  );
}
