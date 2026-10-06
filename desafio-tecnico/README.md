# Desafio Técnico

Soluções em **Python 3.10+**, usando só a biblioteca padrão (nada para instalar).

```
desafio-tecnico/
├── dados/
│   ├── vendas.json        # JSON do exercício 1
│   └── estoque.json       # JSON do exercício 2 (estoque inicial)
├── desafio/
│   ├── comissoes.py       # Exercício 1
│   ├── estoque.py         # Exercício 2
│   ├── juros.py           # Exercício 3
│   └── formatacao.py      # formatação de moeda (R$ 1.234,56)
└── tests/                 # testes automáticos
```

Todos os comandos abaixo são executados de dentro da pasta `desafio-tecnico/`.

---

## 1. Comissão dos vendedores

```bash
python -m desafio.comissoes                  # usa dados/vendas.json
python -m desafio.comissoes outro.json       # ou outro arquivo no mesmo formato
```

```
Vendedor           Vendas    Total vendido      Comissão
--------------------------------------------------------
João Silva             10     R$ 10.754,70     R$ 495,69
Maria Souza             9      R$ 9.874,30     R$ 465,96
Carlos Oliveira         8      R$ 7.928,35     R$ 379,38
Ana Lima                9      R$ 8.763,95     R$ 404,99
--------------------------------------------------------
TOTAL                  36     R$ 37.321,30   R$ 1.746,02
```

| Valor da venda               | Comissão |
|------------------------------|----------|
| abaixo de R$ 100,00          | 0%       |
| R$ 100,00 até R$ 499,99      | 1%       |
| a partir de R$ 500,00        | 5%       |

**Decisões:**
- A regra vale **para cada venda** (como diz o enunciado), não para o total do vendedor.
- Valores em dinheiro usam `Decimal`, não `float`, para evitar erros de arredondamento
  (`0.1 + 0.2 != 0.3`). A comissão de cada venda é arredondada ao centavo antes de somar,
  como aconteceria se cada uma fosse paga separadamente.
- Exatamente R$ 500,00 já paga 5% ("a partir de"); exatamente R$ 100,00 já paga 1%.
- As faixas ficam numa tabela (`FAIXAS`), então mudar ou adicionar faixas não exige mexer na lógica.

## 2. Movimentação de estoque

Menu interativo:

```bash
python -m desafio.estoque
```

```
=== Controle de Estoque ===
1 - Entrada de mercadoria
2 - Saída de mercadoria
3 - Consultar estoque
4 - Histórico de movimentações
0 - Sair
```

Ou direto pela linha de comando:

```bash
python -m desafio.estoque entrada 101 50 "Compra do fornecedor"
# Movimentação #1 registrada (ENTRADA: Compra do fornecedor).
# Caneta Azul: +50 -> estoque final: 200

python -m desafio.estoque saida 101 30 "Venda balcão"
# Movimentação #2 registrada (SAIDA: Venda balcão).
# Caneta Azul: -30 -> estoque final: 170

python -m desafio.estoque saida 102 999 "Venda"
# Erro: Estoque insuficiente de 'Caderno Universitário': disponível 75, solicitado 999.

python -m desafio.estoque saldo
python -m desafio.estoque historico
```

Cada movimentação tem:

| Campo           | Descrição                                                    |
|-----------------|--------------------------------------------------------------|
| `id`            | número identificador único e sequencial (1, 2, 3...)         |
| `tipo`          | `ENTRADA` ou `SAIDA`                                         |
| `descricao`     | texto livre identificando a movimentação (compra, venda, devolução, ajuste de inventário...) |
| `quantidade`    | inteiro maior que zero                                       |
| `data_hora`     | quando foi lançada                                           |
| `estoque_final` | quantidade do produto após a movimentação (o retorno pedido) |

**Decisões:**
- O `dados/estoque.json` original **nunca é alterado**. As movimentações são gravadas em
  `dados/movimentacoes.json` e o saldo atual = estoque inicial + todas as movimentações.
  Assim o histórico é completo e auditável, e os dados persistem entre execuções.
  Para recomeçar do zero, basta apagar `movimentacoes.json`.
- Validações: produto precisa existir, quantidade inteira e positiva, descrição obrigatória
  e **não é permitida saída maior que o saldo** (o estoque nunca fica negativo).
  Uma movimentação rejeitada não altera nada e não consome id.
- A regra de negócio (`Estoque.movimentar`) é separada da interface (menu/linha de comando),
  então poderia ser reaproveitada numa API, por exemplo.

## 3. Juros por atraso

```bash
python -m desafio.juros 1000 24/09/2026                     # calcula na data de hoje
python -m desafio.juros "1.000,00" 24/09/2026 --hoje 04/10/2026
python -m desafio.juros                                     # pergunta valor e vencimento
```

```
Valor original:   R$ 1.000,00
Vencimento:       24/09/2026
Data do cálculo:  04/10/2026
Dias de atraso:   10
Juros (2,5%/dia): R$ 250,00
Total a pagar:    R$ 1.250,00
```

**Fórmula (juros simples):** `juros = valor × 2,5% × dias de atraso`

**Decisões:**
- O enunciado chama de "multa" mas descreve uma taxa diária, então tratei como **juros
  simples de 2,5% ao dia** sobre o valor original (sem juros sobre juros), que é a forma
  usual de cobrança de atraso no Brasil.
- Pago no dia do vencimento ou antes: **sem juros**.
- A data de cálculo é a de hoje; `--hoje` permite simular outra data (útil para conferir e testar).
- Aceita valor como `1500.50`, `1500,50`, `1.500,50` ou `R$ 1.500,50`, e data como `dd/mm/aaaa`
  ou `aaaa-mm-dd`. Entradas inválidas geram uma mensagem clara, sem travar o programa.

---

## Testes

```bash
python -m unittest discover tests        # sem instalar nada
# ou
python -m pytest
```

Os testes cobrem as faixas de comissão (inclusive os limites exatos de R$ 100 e R$ 500),
o resultado com os dados do enunciado, IDs únicos, saldo insuficiente, validações,
persistência das movimentações e o cálculo de juros (em dia, atrasado, arredondamento).
