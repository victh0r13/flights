"use client";

import { useEffect, useState } from "react";

import { api, type Aeroporto } from "@/lib/api";
import { estiloCampo } from "./ui";

/** Campo com sugestões: a pessoa digita "Lisboa" e escolhe "LIS — Lisboa (Humberto Delgado)". */
export function CampoAeroporto({ valor, aoMudar }: { valor: string; aoMudar: (codigo: string) => void }) {
  const [texto, setTexto] = useState(valor);
  const [opcoes, setOpcoes] = useState<Aeroporto[]>([]);
  const [aberto, setAberto] = useState(false);

  // Espera a pessoa parar de digitar (250 ms) antes de perguntar à API: o "debounce".
  useEffect(() => {
    if (!aberto || texto.trim().length < 2) return;
    const espera = setTimeout(() => {
      api.aeroportos(texto).then(setOpcoes).catch(() => setOpcoes([]));
    }, 250);
    return () => clearTimeout(espera);
  }, [texto, aberto]);

  function digitar(novo: string) {
    setTexto(novo);
    setAberto(true);
    // 3 letras já podem ser um código válido (ex.: "gru"); o resto exige escolher na lista
    aoMudar(/^[a-z]{3}$/i.test(novo.trim()) ? novo.trim().toUpperCase() : "");
  }

  function escolher(aeroporto: Aeroporto) {
    setTexto(`${aeroporto.codigo} — ${aeroporto.descricao}`);
    setAberto(false);
    aoMudar(aeroporto.codigo);
  }

  return (
    <div className="relative">
      <input
        className={estiloCampo}
        value={texto}
        placeholder="Cidade ou código (ex.: Lisboa, GRU)"
        onChange={(e) => digitar(e.target.value)}
        onBlur={() => setTimeout(() => setAberto(false), 150)} // dá tempo do clique na opção
      />
      {aberto && opcoes.length > 0 && (
        <ul className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md border border-slate-200 bg-white py-1 shadow-lg">
          {opcoes.map((a) => (
            <li key={a.codigo}>
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => escolher(a)}
                className="w-full px-3 py-2 text-left text-sm hover:bg-sky-50"
              >
                <span className="font-semibold">{a.codigo}</span> — {a.descricao}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
