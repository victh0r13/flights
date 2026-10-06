// Tipos e chamadas da API. Os tipos espelham api/modelos.py (o "contrato" entre front e back).

export type Regra = "menor_preco" | "media";

export interface RotaEntrada {
  nome: string;
  origem: string;
  destino: string;
  periodo_inicio: string; // AAAA-MM-DD
  periodo_fim: string;
  preco_alvo: number;
  email: string;
  regra: Regra;
  dias_de_viagem: number | null; // null = só ida
  adultos: number;
  max_conexoes: number | null; // null = qualquer
  ativa: boolean;
}

export interface Leitura {
  quando: string;
  menor: number;
  media: number;
}

export interface Rota extends RotaEntrada {
  id: string;
  situacao: "ativa" | "pausada" | "encerrada";
  ultima_leitura: Leitura | null;
}

export interface PrecoDia {
  data_ida: string;
  data_volta: string | null;
  preco: number;
  companhia: string;
  conexoes: number;
  link: string | null;
}

export interface Historico {
  consultas: { quando: string; menor: number; media: number; dias: number }[];
  ultima: PrecoDia[];
}

export type BuscaEntrada = Pick<
  RotaEntrada,
  "origem" | "destino" | "periodo_inicio" | "periodo_fim" | "dias_de_viagem" | "adultos" | "max_conexoes" | "regra"
> & { preco_alvo: number | null };

export interface Busca {
  id: string;
  status: "rodando" | "concluida" | "erro";
  total: number;
  feitos: number;
  resultados: PrecoDia[];
  resumo: { menor: number; data_menor: string; media: number; maior: number } | null;
  decisao: { avisar: boolean; motivo: string } | null;
  sugestao_alvo: number | null;
  erro: string | null;
}

export interface Aeroporto {
  codigo: string;
  descricao: string;
}

export interface StatusServidor {
  conectado: boolean;
  endereco: string | null;
  pendente: boolean;
}

/** Erro com a mensagem que a API mandou (já em português quando vem do motor). */
export class ErroApi extends Error {}

const NOMES_CAMPOS: Record<string, string> = {
  nome: "Apelido", origem: "Origem", destino: "Destino", periodo_inicio: "Início do período",
  periodo_fim: "Fim do período", preco_alvo: "Valor alvo", email: "E-mail", adultos: "Adultos",
  dias_de_viagem: "Dias de viagem", usuario: "Gmail", senha: "Senha de app", para: "Destinatário",
};

async function requisitar<T>(caminho: string, opcoes?: RequestInit): Promise<T> {
  let resposta: Response;
  try {
    resposta = await fetch(caminho, {
      ...opcoes,
      headers: { "Content-Type": "application/json", ...opcoes?.headers },
    });
  } catch {
    throw new ErroApi("Não consegui falar com a API. Ela está rodando? (veja o README)");
  }
  if (resposta.status === 204) return undefined as T;
  const corpo = await resposta.json().catch(() => null);
  if (!resposta.ok) {
    const detalhe = corpo?.detail;
    if (typeof detalhe === "string") throw new ErroApi(detalhe);
    if (Array.isArray(detalhe)) {
      // erros de tipo do Pydantic: [{loc: ["body", "preco_alvo"], msg: "..."}]
      throw new ErroApi(
        detalhe.map((d: { loc: string[]; msg: string }) => `${NOMES_CAMPOS[d.loc.at(-1) ?? ""] ?? d.loc.at(-1)}: ${d.msg}`).join(" · "),
      );
    }
    throw new ErroApi(`Erro ${resposta.status} na API.`);
  }
  return corpo as T;
}

const json = (dados: unknown) => JSON.stringify(dados);

export const api = {
  listarRotas: () => requisitar<Rota[]>("/api/rotas"),
  criarRota: (dados: RotaEntrada) => requisitar<Rota>("/api/rotas", { method: "POST", body: json(dados) }),
  editarRota: (id: string, dados: RotaEntrada) =>
    requisitar<Rota>(`/api/rotas/${id}`, { method: "PUT", body: json(dados) }),
  removerRota: (id: string) => requisitar<void>(`/api/rotas/${id}`, { method: "DELETE" }),
  historico: (id: string) => requisitar<Historico>(`/api/rotas/${id}/historico`),
  aeroportos: (q: string) => requisitar<Aeroporto[]>(`/api/aeroportos?q=${encodeURIComponent(q)}`),
  iniciarBusca: (dados: BuscaEntrada) => requisitar<Busca>("/api/buscas", { method: "POST", body: json(dados) }),
  acompanharBusca: (id: string, precoAlvo: number | null) =>
    requisitar<Busca>(`/api/buscas/${id}${precoAlvo ? `?preco_alvo=${precoAlvo}` : ""}`),
  testarEmail: (dados: { usuario: string; senha: string; para: string }) =>
    requisitar<{ mensagem: string }>("/api/email/teste", { method: "POST", body: json(dados) }),
  statusServidor: () => requisitar<StatusServidor>("/api/servidor"),
  sincronizar: () => requisitar<{ passos: string[] }>("/api/servidor/sincronizar", { method: "POST" }),
};

export function mensagemDeErro(erro: unknown): string {
  return erro instanceof Error ? erro.message : String(erro);
}
