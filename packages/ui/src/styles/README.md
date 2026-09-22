# Ink — classes públicas

O sistema Ink vive em três arquivos:

- `src/styles.css` — único ponto de entrada que a aplicação importa (`@import "@basis/ui/styles.css"`).
  Carrega as fontes (Archivo com eixo `wdth` + Martian Mono), o Tailwind v4, os tokens e as classes.
- `src/styles/tokens.css` — `:root` / `:root[data-theme="dark"]`, o bloco `@theme inline`
  (cores, fontes, `--breakpoint-xs: 500px`), a paleta categórica de gráficos, estilos base de
  elemento e `.tnum`.
- `src/styles/ink.css` — as classes de componente documentadas abaixo.

## Estrutura e layout

| Classe | Uso |
| --- | --- |
| `.shell` | Container central de no máximo 96rem com gutter fluido. |
| `.bar` | Barra fixa do topo; combina com `.bar-in` (64px) e `.stuck` (borda de 1px). |
| `.mark` | Logotipo quadrado ink/paper de 34px; gira −90° no hover. |
| `.late` | Texto que cresce na barra quando ela está `.stuck`. |
| `.seg` | Grupo de botões segmentados; `aria-pressed="true"` preenche em ink. |
| `.sq` | Botão quadrado de 34px com borda ink que inverte no hover. |
| `.sec-head` | Cabeçalho de seção com regra de 2px + `.kicker` mono. |
| `.panel`, `.panel-head`, `.panel-body` | Painel plano: borda de 1px, cabeçalho com divisor. |
| `.pill` | Botão arredondado (o único raio 999px do sistema) que inverte no hover. |
| `.plain` | Ação discreta com sublinhado de 1px que escurece no hover. |
| `.grid-lines` | Fundo com grade de fios de 1px, para áreas vazias. |
| `.skeleton` | Placeholder animado no tom de `--rule` (respeita `prefers-reduced-motion`). |
| `.foot`, `.foot-grid` | Rodapé de três colunas a partir de 760px. |

## Tipografia

| Classe | Uso |
| --- | --- |
| `.mono` | Micro-rótulo em Martian Mono: 0.62rem, uppercase, tracking .14em. |
| `.wide` | `font-variation-settings: 'wdth' 125` (assinatura da marca). |
| `.giant` | Título de clamp(3rem, 9vw, 8rem) com `wdth` 125 e tracking negativo. |
| `.lede` | Parágrafo de abertura em ash com no máximo 46ch. |
| `.kicker` | Rótulo mono de seção em ash. |
| `.tnum` | Numerais tabulares para tabelas e métricas. |

## Dados

| Classe | Uso |
| --- | --- |
| `.ledger` | Tabela financeira: cabeçalho mono sobre regra de 2px, linhas de 1px, hover em `--hover-bg`. |
| `.ledger .num` | Coluna numérica alinhada à direita em Martian Mono. |
| `.ledger .pos` / `.ledger .neg` | Valores positivos em verde, negativos em vermelho. |
| `.metric`, `.metric-label`, `.metric-value`, `.metric-delta` | Bloco de KPI; o valor escala com a viewport e usa numerais tabulares. |
| `.chip` (`.gold`, `.muted`) | Etiqueta quadrada de status. |
| `.live` | Marcador com quadrado dourado de 7px, reservado a sinal/valor. |

## Movimento

| Classe | Uso |
| --- | --- |
| `.line` / `.line > span` | Reveal por máscara (o `<span>` sobe 108% e a classe `.on` revela). |
| `.fade` / `.fade.on` | Fade + 16px de subida, revelado por `useReveal`. |
| `.roll` | Rolagem de duas cópias do texto no hover (usado na navegação). |
| `.arw` | Seta que desliza e gira −45° no hover. |

> Todo o movimento é desligado sob `prefers-reduced-motion: reduce`. O dourado
> (`--gold`/`--gold-fill`) é reservado a estado/valor; a paleta categórica
> (`--chart-1..8`) existe apenas para gráficos de distribuição.
