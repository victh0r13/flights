"use client";

import { useState, type FormEvent } from "react";

import { api, mensagemDeErro } from "@/lib/api";
import { Aviso, Botao, Campo, estiloCampo } from "./ui";

/** Confere se o Gmail + senha de app funcionam. Nada é salvo. */
export function TesteEmail({ emailPadrao }: { emailPadrao: string }) {
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [para, setPara] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState<{ ok: boolean; texto: string } | null>(null);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setResultado(null);
    try {
      const { mensagem } = await api.testarEmail({ usuario, senha, para: para || usuario || emailPadrao });
      setResultado({ ok: true, texto: mensagem });
    } catch (e) {
      setResultado({ ok: false, texto: mensagemDeErro(e) });
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="space-y-4">
      <p className="text-sm text-slate-600">
        Use um Gmail e uma <strong>senha de app</strong> (16 letras, criada em{" "}
        <a className="text-sky-700 underline" href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer">
          myaccount.google.com/apppasswords
        </a>
        ). Nada do que você digitar aqui fica salvo — no robô, esses dados ficam nos Secrets do GitHub.
      </p>
      <div className="grid gap-4 sm:grid-cols-3">
        <Campo rotulo="Gmail (remetente)">
          <input type="email" className={estiloCampo} value={usuario} onChange={(e) => setUsuario(e.target.value)} required />
        </Campo>
        <Campo rotulo="Senha de app" ajuda={`${senha.replace(/\s/g, "").length} de 16 letras`}>
          <input className={estiloCampo} value={senha} onChange={(e) => setSenha(e.target.value)} autoComplete="off" required />
        </Campo>
        <Campo rotulo="Enviar o teste para" ajuda="Vazio = o próprio Gmail">
          <input type="email" className={estiloCampo} value={para} placeholder={usuario || emailPadrao} onChange={(e) => setPara(e.target.value)} />
        </Campo>
      </div>
      <div className="flex items-center gap-3">
        <Botao type="submit" variante="primario" disabled={enviando}>
          {enviando ? "Enviando…" : "Enviar e-mail de teste"}
        </Botao>
        {resultado && <Aviso tipo={resultado.ok ? "sucesso" : "erro"}>{resultado.texto}</Aviso>}
      </div>
    </form>
  );
}
