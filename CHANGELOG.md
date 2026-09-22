# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e versionamento semântico.

## [0.1.0] — 2026-09-22

Primeira entrega completa: reescrita do case legado (Fastify + Prisma + Next.js, catálogo hardcoded, nenhum teste) como uma plataforma de gestão de investimentos com DDD, dados de mercado reais e design system próprio.

### Adicionado

- **Identidade e acesso**: Argon2id com re-hash transparente, access token JWT curto mantido apenas em memória, refresh opaco rotativo em cookie httpOnly com detecção de reuso, papéis admin/advisor/viewer, troca de senha que revoga todas as sessões, cadastro de conta na própria tela de acesso (entrar/criar conta) e bootstrap do primeiro usuário como admin.
- **Clientes**: validação de CPF/CNPJ com dígitos verificadores (mod-11), documento mascarado na API, unicidade com `409`, questionário de suitability (5–10 respostas de 0 a 4 → score 0–100 → perfil conservador/moderado/arrojado), busca por nome/e-mail, filtro por situação e arquivamento reversível.
- **Carteiras**: extrato *append-only* de compras, vendas, proventos e taxas; posições derivadas por custo médio ponderado com ganho realizado; alocação alvo em basis points (soma exata de 100%); valoração mark-to-market por posição com peso, valor de mercado e P&L; lista de carteiras marcada a mercado em um único lote de cotações.
- **Mercado**: catálogo de instrumentos com ISIN (Luhn/ISO 6166), MIC (ISO 10383) e CFI (ISO 10962); providers brapi.dev, Yahoo Finance e BCB SGS atrás de um protocolo único, com cache TTL, roteamento por símbolo e fallback determinístico; séries macro (Selic, CDI, IPCA, USD/BRL); histórico diário para gráficos.
- **Analytics**: TWR por sub-períodos diários, XIRR (Newton-Raphson com bisseção, actual/365), volatilidade anualizada, Sharpe com Selic anualizada do BCB, beta vs. Ibovespa, drawdown máximo, VaR histórico 95%, exposição por classe, drift em bps e plano de rebalanceamento com valor mínimo de negociação.
- **Interface Ink**: design system portado do portfólio para `packages/ui` (tokens, primitivos sobre Radix, tabela-ledger, gráficos SVG próprios e `lightweight-charts` para candles), tema claro/escuro, i18n PT/EN com paridade verificada por teste.
- **Operação**: Alembic com descoberta automática de modelos, seed idempotente (catálogo + admin + demo de 12 meses), Docker Compose com Postgres 16/API/web, contrato OpenAPI 3.1 exportado e tipos TypeScript gerados para o frontend.

### Alterado

- Repositório renomeado para **Basis** (`@basis/*`, pacote Python `basis`, prefixo `BASIS_`), substituindo AnkaFlow/AnkaTechCase.
- Backend reescrito em Python 3.14 + FastAPI + SQLAlchemy 2 assíncrono (era Node/Fastify/Prisma/MySQL).
- Frontend reconstruído em Vite + React 19 com FSD (era Next.js com componentes soltos).
- "Oportunidades" deixou de ser um array no código e passou a ser catálogo persistido com cotações de provedores reais.

### Corrigido

- Divisão de dinheiro com dízima estourava a validação (`2618 / 30`); a aritmética agora limita a 12 casas com arredondamento bancário.
- Taxa livre de risco extrapolada de uma janela de 100 anos: o `latest` da série macro delegava ao provider determinístico que acumulava a Selic diária, produzindo um Sharpe de `-5e15`; corrigido com semântica de taxa por período e teste de regressão.
- Usuário era deslogado ao recarregar a página: o efeito duplo do React StrictMode disparava dois `/auth/refresh`, o segundo caía na detecção de reuso e encerrava a sessão — resolvido com refresh *single-flight* e janela de graça de 30 s na rotação.
- Endpoints de mercado levavam 10–12 s com provedores ao vivo; agora respondem em milissegundos (stale-while-revalidate + chamadas concorrentes + `bisect` na série de preços).
- Quantidades e valores voltavam do banco com zeros à direita (`200.0000000000`); a borda HTTP normaliza os decimais.
- Página de login não exibia o wordmark (reveal sem a classe de ativação), navegação aparecia para visitante deslogado e o menu lateral duplicava o header.
- Erros de domínio não vazam mais para o cliente: tudo sai como RFC 9457 com `code` estável e `X-Request-ID`.

### Segurança

- Senhas com Argon2id (parâmetros configuráveis), documento mascarado em respostas e logs, refresh token guardado apenas como digest SHA-256, cookies `httpOnly` + `SameSite=Lax` com escopo restrito.
- CI com `gitleaks` e `pip-audit`; Dependabot semanal; segredos exclusivamente por variáveis de ambiente (`.env` ignorado).
