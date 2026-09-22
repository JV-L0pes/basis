# ADR 0008 — Sessão com access token curto e refresh rotativo

- Status: aceito
- Data: 2026-09-21
- Contexto: uma SPA precisa manter o usuário logado sem guardar credenciais de longa duração em `localStorage`, onde qualquer XSS as lê.

## Decisão

- **Access token** JWT de 15 minutos, mantido **apenas em memória** no frontend.
- **Refresh token** opaco (não JWT), 14 dias, rotativo, persistido como digest SHA-256 e entregue em cookie `httpOnly` + `SameSite=Lax`, com caminho restrito a `/api/v1/auth`.
- Rotação com **detecção de reuso**: token revogado apresentado novamente encerra a família de sessões; dentro de uma janela de graça de 30 s o reuso é tratado como corrida de cliente (recusado, sessão preservada).
- Refresh **single-flight** no cliente: chamadas concorrentes compartilham uma requisição.
- Senhas com Argon2id (parâmetros configuráveis) e tempo de login equalizado para e-mail inexistente.

## Consequências

- XSS não entrega o refresh token; senha nunca trafega em cookie de sessão.
- O efeito duplo do React StrictMode (e duas abas) não desloga mais o usuário — foi exatamente o bug encontrado na demonstração: dois `/auth/refresh` em paralelo, o segundo caía na detecção de reuso e matava a sessão.
- Trocar a senha revoga todas as sessões; mudar `BASIS_SECRET_KEY` invalida os access tokens e força re-login.
