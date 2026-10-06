const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

export const reais = (valor: number) => moeda.format(valor);

/** "2026-12-18" -> "18/12/2026" (sem passar por Date, para não sofrer com fuso horário). */
export function data(iso: string): string {
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
}

/** "2026-12-18" -> "18/12" */
export const diaMes = (iso: string) => data(iso).slice(0, 5);

/** "2026-10-06T00:39-03:00" -> "06/10 às 00:39" */
export function dataHora(iso: string): string {
  return `${diaMes(iso)} às ${iso.slice(11, 16)}`;
}

const DIAS_SEMANA = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];

export function diaSemana(iso: string): string {
  const [ano, mes, dia] = iso.split("-").map(Number);
  return DIAS_SEMANA[new Date(ano, mes - 1, dia).getDay()];
}

export const conexoes = (n: number) => (n === 0 ? "direto" : n === 1 ? "1 conexão" : `${n} conexões`);
