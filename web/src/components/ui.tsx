"use client";

import { useEffect, type ButtonHTMLAttributes, type ReactNode } from "react";

// Peças visuais reaproveitadas em toda a tela.

export const estiloCampo =
  "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 " +
  "focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200 disabled:bg-slate-100";

const VARIANTES = {
  primario: "bg-sky-600 text-white hover:bg-sky-700",
  secundario: "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50",
  perigo: "border border-red-200 bg-white text-red-700 hover:bg-red-50",
};

export function Botao({
  variante = "secundario",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variante?: keyof typeof VARIANTES }) {
  return (
    <button
      type="button"
      className={`rounded-md px-3 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTES[variante]} ${className}`}
      {...props}
    />
  );
}

export function Campo({ rotulo, ajuda, children }: { rotulo: string; ajuda?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700">{rotulo}</span>
      {children}
      {ajuda && <span className="mt-1 block text-xs text-slate-500">{ajuda}</span>}
    </label>
  );
}

export function Aviso({ tipo, children }: { tipo: "erro" | "sucesso" | "info"; children: ReactNode }) {
  const cores = {
    erro: "border-red-200 bg-red-50 text-red-800",
    sucesso: "border-emerald-200 bg-emerald-50 text-emerald-800",
    info: "border-sky-200 bg-sky-50 text-sky-800",
  };
  return <div className={`rounded-md border px-3 py-2 text-sm ${cores[tipo]}`}>{children}</div>;
}

export function Modal({ titulo, aoFechar, children }: { titulo: string; aoFechar: () => void; children: ReactNode }) {
  useEffect(() => {
    const aoTeclar = (e: KeyboardEvent) => e.key === "Escape" && aoFechar();
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [aoFechar]);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/40 p-4 sm:p-8">
      <div className="w-full max-w-3xl rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <h2 className="text-lg font-semibold text-slate-900">{titulo}</h2>
          <button onClick={aoFechar} className="rounded p-1 text-slate-500 hover:bg-slate-100" aria-label="Fechar">
            ✕
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
