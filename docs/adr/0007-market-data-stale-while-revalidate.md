# ADR 0007 — Dados de mercado com stale-while-revalidate

- Status: aceito
- Data: 2026-09-22
- Contexto: com provedores ao vivo habilitados, a primeira medição mostrou `/portfolios` em 12,5 s, `/market/overview` em 12,7 s e `/performance` em 10 s — cada cotação esperava timeout e retry do provedor antes de cair no fallback.

## Decisão

Provedores externos nunca bloqueiam a resposta:

1. a requisição responde imediatamente com a série determinística (seed);
2. uma tarefa de background busca o valor real (brapi, Yahoo, BCB) e atualiza o cache TTL;
3. a próxima leitura já é ao vivo — o painel mostra `ao vivo` quando a origem não é o seed.

Complementos: chamadas de lote e histórico rodam concorrentes (`asyncio.gather` com semáforo de 6), timeout de 5 s com 2 tentativas, e a série de valuation usa `bisect` sobre fechamentos ordenados em vez de varrer todas as datas por símbolo.

## Consequências

- Medido após a mudança: `/portfolios` 26 ms, `/market/overview` 13 ms, `/performance` 0,7 s, `/allocation` 0,2 s (a primeira chamada após o boot ainda paga warmup de conexão).
- A plataforma funciona offline: sem rede, tudo vem do provider determinístico, com preços estáveis entre execuções.
- Trade-off aceito: o primeiro carregamento mostra preço de seed e o valor ao vivo aparece na revalidação seguinte (o frontend revalida o overview a cada 60 s).
