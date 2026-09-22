# ADR 0001 — Monorepo com monolito modular

- Status: aceito
- Data: 2026-09-21
- Contexto: projeto de portfólio saindo de um case legado (Fastify + Prisma + Next.js) para uma plataforma de mercado financeiro com backend próprio, mantido por uma pessoa.

## Decisão

Monorepo poliglota com dois apps — `apps/api` (FastAPI) e `apps/web` (React/Vite) — e o backend como **monolito modular**: um único deploy, com bounded contexts separados por pastas e fronteiras garantidas por `import-linter` no CI. O gerenciamento de dependências usa `pnpm` workspaces para TypeScript e `uv` para Python; o Turborepo orquestra apenas as tarefas de JS/TS.

## Consequências

- Um checkout, um CI, lockfiles únicos por ecossistema (`pnpm-lock.yaml`, `uv.lock`).
- Extrair um contexto para serviço é mecânico: nenhum contexto importa as tabelas ou as entidades de outro.
- Custo: disciplina para não furar fronteiras — mitigada por 8 contratos automatizados.
- O Docker Compose roda banco, API e web sem depender de nenhuma plataforma de deploy.
