"use client";

import { useState, type FormEvent } from "react";

import { api, mensagemDeErro, type Regra, type Rota, type RotaEntrada } from "@/lib/api";
import { reais } from "@/lib/formato";
import { CampoAeroporto } from "./CampoAeroporto";
import { ResultadoBusca, useBusca } from "./PainelBusca";
import { Aviso, Botao, Campo, estiloCampo } from "./ui";

const MAX_DIAS_PERIODO = 60;

/** Estado do formulário: números ficam como texto enquanto a pessoa digita. */
interface Formulario {
  nome: string;
  origem: string;
  destino: string;
  periodo_inicio: string;
  periodo_fim: string;
  idaEVolta: boolean;
  dias_de_viagem: string;
  adultos: string;
  max_conexoes: "" | "0" | "1";
  regra: Regra;
  preco_alvo: string;
  email: string;
}

function inicial(rota: Rota | null, emailPadrao: string): Formulario {
  return {
    nome: rota?.nome ?? "",
    origem: rota?.origem ?? "",
    destino: rota?.destino ?? "",
    periodo_inicio: rota?.periodo_inicio ?? "",
    periodo_fim: rota?.periodo_fim ?? "",
    idaEVolta: rota ? rota.dias_de_viagem !== null : true,
    dias_de_viagem: String(rota?.dias_de_viagem ?? 7),
    adultos: String(rota?.adultos ?? 1),
    max_conexoes: rota?.max_conexoes === 0 ? "0" : rota?.max_conexoes === 1 ? "1" : "",
    regra: rota?.regra ?? "menor_preco",
    preco_alvo: rota ? String(rota.preco_alvo) : "",
    email: rota?.email ?? emailPadrao,
  };
}

/** Confere o básico antes de chamar a API (a API confere tudo de novo, por segurança). */
function problemas(f: Formulario, exigirTudo: boolean): string[] {
  const lista: string[] = [];
  if (!f.origem) lista.push("Escolha a origem na lista de sugestões.");
  if (!f.destino) lista.push("Escolha o destino na lista de sugestões.");
  if (f.origem && f.origem === f.destino) lista.push("Origem e destino são iguais.");
  if (!f.periodo_inicio || !f.periodo_fim) lista.push("Preencha as duas datas do período.");
  if (f.periodo_inicio && f.periodo_fim) {
    const dias = (Date.parse(f.periodo_fim) - Date.parse(f.periodo_inicio)) / 86_400_000 + 1;
    if (dias < 1) lista.push("O fim do período é antes do início.");
    if (dias > MAX_DIAS_PERIODO) lista.push(`O período pode ter no máximo ${MAX_DIAS_PERIODO} dias.`);
  }
  if (exigirTudo) {
    if (!(Number(f.preco_alvo) > 0)) lista.push("Informe o valor alvo.");
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(f.email)) lista.push("Informe um e-mail válido.");
  }
  return lista;
}

export function FormularioRota({
  rota,
  emailPadrao,
  aoSalvar,
  aoCancelar,
}: {
  rota: Rota | null; // null = nova rota
  emailPadrao: string;
  aoSalvar: (rota: Rota) => void;
  aoCancelar: () => void;
}) {
  const [f, setF] = useState<Formulario>(() => inicial(rota, emailPadrao));
  const [erros, setErros] = useState<string[]>([]);
  const [salvando, setSalvando] = useState(false);
  const { busca, erro: erroBusca, iniciar, rodando } = useBusca();

  const mudar = <K extends keyof Formulario>(campo: K, valor: Formulario[K]) => setF((atual) => ({ ...atual, [campo]: valor }));

  const apelidoPadrao = f.origem && f.destino ? `${f.origem} → ${f.destino}` : "";
  const diasDeViagem = f.idaEVolta ? Number(f.dias_de_viagem) : null;
  const maxConexoes = f.max_conexoes === "" ? null : Number(f.max_conexoes);

  function pesquisarPrecos() {
    const lista = problemas(f, false);
    setErros(lista);
    if (lista.length) return;
    iniciar({
      origem: f.origem, destino: f.destino, periodo_inicio: f.periodo_inicio, periodo_fim: f.periodo_fim,
      dias_de_viagem: diasDeViagem, adultos: Number(f.adultos), max_conexoes: maxConexoes, regra: f.regra,
      preco_alvo: Number(f.preco_alvo) || null,
    });
  }

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    const lista = problemas(f, true);
    setErros(lista);
    if (lista.length) return;

    const dados: RotaEntrada = {
      nome: f.nome.trim() || apelidoPadrao, origem: f.origem, destino: f.destino, periodo_inicio: f.periodo_inicio,
      periodo_fim: f.periodo_fim, preco_alvo: Number(f.preco_alvo), email: f.email.trim(), regra: f.regra,
      dias_de_viagem: diasDeViagem, adultos: Number(f.adultos), max_conexoes: maxConexoes, ativa: rota?.ativa ?? true,
    };
    setSalvando(true);
    try {
      aoSalvar(rota ? await api.editarRota(rota.id, dados) : await api.criarRota(dados));
    } catch (e) {
      setErros([mensagemDeErro(e)]);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <form onSubmit={salvar} className="space-y-6">
      <section className="grid gap-4 sm:grid-cols-2">
        <Campo rotulo="De onde sai?">
          <CampoAeroporto valor={f.origem} aoMudar={(c) => mudar("origem", c)} />
        </Campo>
        <Campo rotulo="Para onde vai?">
          <CampoAeroporto valor={f.destino} aoMudar={(c) => mudar("destino", c)} />
        </Campo>
        <Campo rotulo="Primeira data de ida possível">
          <input type="date" className={estiloCampo} value={f.periodo_inicio} onChange={(e) => mudar("periodo_inicio", e.target.value)} />
        </Campo>
        <Campo rotulo="Última data de ida possível" ajuda={`Cada dia do período é uma pesquisa (máx. ${MAX_DIAS_PERIODO} dias).`}>
          <input type="date" className={estiloCampo} value={f.periodo_fim} min={f.periodo_inicio} onChange={(e) => mudar("periodo_fim", e.target.value)} />
        </Campo>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <Campo rotulo="Tipo de passagem">
          <select className={estiloCampo} value={f.idaEVolta ? "ida-volta" : "ida"} onChange={(e) => mudar("idaEVolta", e.target.value === "ida-volta")}>
            <option value="ida-volta">Ida e volta</option>
            <option value="ida">Só ida</option>
          </select>
        </Campo>
        {f.idaEVolta && (
          <Campo rotulo="Dias de viagem" ajuda="A volta é X dias depois da ida.">
            <input type="number" min={1} max={90} className={estiloCampo} value={f.dias_de_viagem} onChange={(e) => mudar("dias_de_viagem", e.target.value)} />
          </Campo>
        )}
        <Campo rotulo="Adultos">
          <input type="number" min={1} max={9} className={estiloCampo} value={f.adultos} onChange={(e) => mudar("adultos", e.target.value)} />
        </Campo>
        <Campo rotulo="Conexões">
          <select className={estiloCampo} value={f.max_conexoes} onChange={(e) => mudar("max_conexoes", e.target.value as Formulario["max_conexoes"])}>
            <option value="">Tanto faz</option>
            <option value="0">Só voo direto</option>
            <option value="1">No máximo 1 conexão</option>
          </select>
        </Campo>
      </section>

      <section className="space-y-3 rounded-lg border border-slate-200 p-4">
        <div className="text-sm font-medium text-slate-700">Quando você quer receber o e-mail?</div>
        <div className="grid gap-2 sm:grid-cols-2">
          {(
            [
              ["menor_preco", "Menor preço", "quando QUALQUER dia do período custar até o valor"],
              ["media", "Média", "quando a MÉDIA de preço do período ficar até o valor"],
            ] as const
          ).map(([valor, titulo, descricao]) => (
            <label key={valor} className={`cursor-pointer rounded-md border p-3 text-sm ${f.regra === valor ? "border-sky-500 bg-sky-50" : "border-slate-200"}`}>
              <input type="radio" name="regra" className="mr-2" checked={f.regra === valor} onChange={() => mudar("regra", valor)} />
              <span className="font-medium">{titulo}</span>
              <span className="block pl-5 text-slate-500">{descricao}</span>
            </label>
          ))}
        </div>
        <div className="grid items-end gap-4 sm:grid-cols-2">
          <Campo rotulo="Valor alvo (R$)" ajuda={`Total para ${Number(f.adultos) > 1 ? "todos os passageiros" : "1 passageiro"}${f.idaEVolta ? ", ida + volta" : ""}.`}>
            <input type="number" min={1} className={estiloCampo} value={f.preco_alvo} onChange={(e) => mudar("preco_alvo", e.target.value)} />
          </Campo>
          <Botao onClick={pesquisarPrecos} disabled={rodando}>
            {rodando ? "Pesquisando…" : "Pesquisar preços de hoje"}
          </Botao>
        </div>
        {busca?.sugestao_alvo && !rodando && (
          <Aviso tipo="info">
            Dica: {reais(busca.sugestao_alvo)} fica 10% abaixo do valor de hoje.{" "}
            <button type="button" className="font-semibold underline" onClick={() => mudar("preco_alvo", String(busca.sugestao_alvo))}>
              Usar esse valor
            </button>
          </Aviso>
        )}
        <ResultadoBusca busca={busca} erro={erroBusca} precoAlvo={Number(f.preco_alvo) || null} />
      </section>

      <section className="grid gap-4 sm:grid-cols-2">
        <Campo rotulo="E-mail que recebe os alertas">
          <input type="email" className={estiloCampo} value={f.email} onChange={(e) => mudar("email", e.target.value)} />
        </Campo>
        <Campo rotulo="Apelido da rota" ajuda="Opcional.">
          <input className={estiloCampo} value={f.nome} placeholder={apelidoPadrao || "Ex.: Férias em Salvador"} onChange={(e) => mudar("nome", e.target.value)} />
        </Campo>
      </section>

      {erros.length > 0 && (
        <Aviso tipo="erro">
          <ul className="list-inside list-disc">
            {erros.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        </Aviso>
      )}

      <div className="flex justify-end gap-2 border-t border-slate-200 pt-4">
        <Botao onClick={aoCancelar}>Cancelar</Botao>
        <Botao type="submit" variante="primario" disabled={salvando}>
          {salvando ? "Salvando…" : rota ? "Salvar alterações" : "Cadastrar rota"}
        </Botao>
      </div>
    </form>
  );
}
