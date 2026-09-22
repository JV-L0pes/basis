# ADR 0005 — Identificadores de mercado por padrões internacionais

- Status: aceito
- Data: 2026-09-21
- Contexto: o catálogo legado era uma lista fixa de sete ativos com nome, tipo e risco em texto livre. Sem identificadores, não há como integrar provedores nem distinguir dois ativos com o mesmo ticker em mercados diferentes.

## Decisão

Instrumentos e valores usam padrões abertos, validados no domínio:

| Padrão | Uso |
|---|---|
| ISO 4217 | moedas (`BRL`, `USD`) com expoente de menor unidade |
| ISO 8601 / RFC 3339 | datas e timestamps, sempre UTC; `Clock` injetado |
| ISO 6166 (ISIN) | identificação do ativo, com dígito verificador Luhn sobre a expansão alfanumérica |
| ISO 10962 (CFI) | classificação do instrumento (formato) |
| ISO 10383 (MIC) | mercado (`BVMF` para a B3) |
| CPF/CNPJ (mod-11) | documento do cliente, com dígitos verificadores e máscara segura |
| UUIDv7 (RFC 9562) | identificadores internos ordenados por tempo |

## Consequências

- Cotações podem ser buscadas por ISIN ou ticker + mercado sem ambiguidade.
- Dados inválidos (ISIN com Luhn errado, MIC mal formado) são barrados na borda do domínio.
- FIGI fica como evolução caso seja necessário mapear instrumentos internacionais.
