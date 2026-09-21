# Ink — classes públicas

O sistema Ink vive em dois arquivos e um ponto de entrada:

- `src/styles.css` — único arquivo que a aplicação importa (`@import "@basis/ui/styles.css";`).
  Ele carrega as fontes (Archivo com eixo `wdth` + Martian Mono), o Tailwind v4, os tokens e as classes.
- `src/styles/tokens.css` — `:root` / `:root[data-theme="dark"]`, o bloco `@theme inline`
  (cores, fontes, `--breakpoint-xs: 500px`), estilos base de elemento e `.tnum`.
- `src/styles/ink.css` — as classes de componente abaixo.

## Estrutura e layout

| Classe | Uso |
| --- | --- |
| `.shell` | Container central de no máximo 96rem com gutter fluido. |
| `.bar` | Barra fixa do topo; combina com `.bar-in` (64px) e `.stuck` (borda de 1px ao rolar). |
| `.mark` | Logotipo quadrado ink/paper de 34px; gira −90° no hover. |
| `.late` | Nome que aparece na barra só depois do `.stuck`. |
| `.seg` | Grupo de botões segmentados; `aria-pressed="true"` preenche em ink. |
| `.sq` | Botão quadrado de 34px com borda ink que inverte no hover. |
| `.hero`, `.hero-grid`, `.hero-main`, `.hero-role`, `.hero-cta` | Grade editorial do topo da página. |
| `.giant` | Título de clamp(3.6rem, 11vw, 12.5rem) com paralaxe de scroll nativa. |
| `.lede` | Parágrafo de abertura em ash com no máximo 42ch. |
| `.rail`, `.rail-links` | Trilho lateral de informações com links sublinhados. |
| `.media` | Imagem de recorte 1:1 em grayscale (antigo `.portrait` do portfólio). |
| `.lab` | Rótulo mono uppercase em ash acima de um bloco. |
| `.sec-head` | Cabeçalho de seção com regra de 2px e kicker mono. |
| `.cat`, `.cat-rail` | Grade categoria + conteúdo; trilho fixo (sticky) a partir de 960px. |
| `.rule-top`, `.tail` | Regras de 1px que se desenham com `animation-timeline: view()`. |

## Texto, listas e revelações

| Classe | Uso |
| --- | --- |
| `.mono` | Micro-rótulo mono uppercase de 0.62rem com tracking 0.14em. |
| `.wide` | Archivo com `wdth` 125 para chamadas largas. |
| `.num` / `.tnum` | Números tabulares (`.num` é o alias histórico do portfólio). |
| `.line` | Máscara de revelação linha a linha; o `span` interno entra de baixo. |
| `.fade` | Fade + translateY de 16px controlado por `.on`. |
| `.on` | Estado revelado para `.line` e `.fade` (aplicado por `useReveal`). |
| `.roll` | Rolagem vertical de texto em links de navegação. |
| `.pill` | CTA arredondado (999px) ink/paper que inverte no hover. |
| `.plain` | Link sublinhado com borda que escurece no hover. |
| `.arw` | Seta que gira −45° no hover do link pai. |
| `.dec` | Lista de decisões com marcadores em `--rule`. |
| `.impact` | Bloco de impacto com rótulo dourado (`.impact .lbl`) sobre regra de 1px. |
| `.live` | Indicador de status ao vivo: ponto dourado + texto dourado. |
| `.led` | Linha de ledger de experiência (trilho + prosa) com hover de fundo. |
| `.more`, `.more .ext` | Lista de projetos com seta diagonal no canto. |
| `.close` | Seção de fecho invertida (fundo ink, texto paper). |
| `.foot`, `.foot-grid`, `.foot-bar`, `.colo`, `.totop` | Rodapé editorial com barra final e "voltar ao topo". |
| `.prog` | Barra de progresso de leitura fixa de 2px. |
| `.band`, `.band-track`, `.band .sep`, `.sr-only` | Faixa marquee infinita e utilitário de leitura assistiva. |

## Adições Basis

| Classe | Uso |
| --- | --- |
| `.ledger` | Tabela financeira: cabeçalho mono sobre regra de 2px, linhas de 1px, números tabulares e hover. |
| `.ledger .pos` / `.ledger .neg` | Ganho (positive) e perda (destructive) — nunca decorativos. |
| `.ledger .right` | Alinha colunas numéricas à direita. |
| `.metric` + `.metric-label` / `.metric-value` / `.metric-delta` | Bloco de KPI: rótulo mono, valor em display 800 com `wdth` 112 e delta opcional `.pos` / `.neg`. |
| `.grid-lines` | Fundo de painel com grade de fios de 1px em `--rule` (`--grid-size`, padrão 3rem). |
| `.chip` | Etiqueta quadrada de 1px com borda ink e texto mono uppercase. |
| `.skeleton` | Shimmer Ink baseado em `--rule` com guarda de movimento reduzido. |

## Movimento

`@media (prefers-reduced-motion: reduce)` desliga animações, transições e scroll suave.
`@media (pointer: coarse)` garante alvos de toque de pelo menos 24px (34px para `.sq` e `.seg`).
`.grid-lines`, `.skeleton` e as animações de timeline respeitam as duas regras.
