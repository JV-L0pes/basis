import type { components } from "@basis/contracts"
import { HttpResponse, http } from "msw"
import { setupServer } from "msw/node"

import { env } from "@/shared/config/env"

const api = (path: string) => `${env.apiUrl}${path}`

const USER: components["schemas"]["UserResponse"] = {
  id: "01920000-0000-7000-8000-000000000001",
  email: "ana@basis.dev",
  display_name: "Ana Souza",
  role: "admin",
  is_active: true,
  created_at: "2026-06-01T12:00:00Z",
}

export const CLIENT: components["schemas"]["ClientResponse"] = {
  id: "01920000-0000-7000-8000-000000000101",
  name: "Ana Souza",
  email: "ana.souza@basis.dev",
  tax_id_masked: "***.***.247-25",
  tax_id_kind: "cpf",
  suitability: "aggressive",
  suitability_score: 95,
  status: "active",
  notes: "Private banking",
  created_at: "2026-06-01T12:00:00Z",
  updated_at: "2026-06-01T12:00:00Z",
}

const CLIENT_LIST: components["schemas"]["ClientListResponse"] = {
  items: [CLIENT],
  next_cursor: null,
}

const MACRO: components["schemas"]["MacroPointResponse"] = {
  code: "selic",
  label: "SELIC",
  unit: "% a.a.",
  date: "2026-06-01",
  value: "10.75",
}

const QUOTE: components["schemas"]["QuoteResponse"] = {
  symbol: "PETR4",
  price: "38.72",
  currency: "BRL",
  as_of: "2026-06-01T17:00:00Z",
  source: "seed",
  change_percent: 1.25,
}

const BOOK: components["schemas"]["BookOverviewResponse"] = {
  portfolio_count: 2,
  total_market_value: "168000.00",
  currency: "BRL",
  allocation: [
    { asset_class: "equity", value: "100000.00", weight: 0.5952 },
    { asset_class: "real_estate", value: "68000.00", weight: 0.4048 },
  ],
}

const PORTFOLIO: components["schemas"]["PortfolioResponse"] = {
  id: "01920000-0000-7000-8000-000000000201",
  client_id: CLIENT.id,
  name: "Carteira Ana",
  base_currency: "BRL",
  status: "active",
  targets: [{ asset_class: "equity", weight_bps: 6000, weight_percent: 60 }],
  position_count: 2,
  transaction_count: 3,
  created_at: "2026-06-01T12:00:00Z",
  updated_at: "2026-06-10T12:00:00Z",
  valuation: {
    base_currency: "BRL",
    invested: "10000.00",
    market_value: "12000.00",
    unrealized_gain: "2000.00",
    realized_gain: "0.00",
    income: "150.00",
    costs: "20.00",
    net_result: "2130.00",
    return_percent: 21.3,
    unpriced_symbols: [],
    positions: [
      {
        symbol: "PETR4",
        asset_class: "equity",
        currency: "BRL",
        quantity: "200",
        average_cost: "35.15",
        cost_basis: "7030.00",
        market_price: "38.72",
        market_value: "7744.00",
        unrealized_gain: "714.00",
        unrealized_gain_percent: 10.16,
        realized_gain: "0.00",
        income: "150.00",
        costs: "20.00",
        weight: 0.6453,
      },
    ],
  },
}

export const PERFORMANCE: components["schemas"]["PerformanceResponse"] = {
  portfolio_id: PORTFOLIO.id,
  currency: "BRL",
  start: "2026-01-01",
  end: "2026-06-01",
  initial_value: "10000.00",
  final_value: "12000.00",
  net_contributions: "10000.00",
  twr: 0.2,
  xirr: 0.185,
  volatility: 0.22,
  annualized_return: 0.19,
  max_drawdown: -0.08,
  sharpe: 0.85,
  beta: 0.92,
  var_95: -0.021,
  benchmark_symbol: "^BVSP",
  benchmark_return: 0.11,
  risk_free_annual: 0.1,
  equity_curve: [
    { date: "2026-01-01", value: "10000.00" },
    { date: "2026-03-01", value: "11000.00" },
    { date: "2026-06-01", value: "12000.00" },
  ],
}

const ALLOCATION: components["schemas"]["AllocationAnalysisResponse"] = {
  portfolio_id: PORTFOLIO.id,
  currency: "BRL",
  total_value: "12000.00",
  exposures: [{ asset_class: "equity", value: "12000.00", weight: 1 }],
  drift: [
    {
      asset_class: "equity",
      current_value: "12000.00",
      target_value: "7200.00",
      current_weight: 1,
      target_weight: 0.6,
      delta_value: "-4800.00",
      drift_bps: 4000,
    },
  ],
  plan: [{ asset_class: "equity", action: "sell", amount: "4800.00", drift_bps: 4000 }],
  unpriced_symbols: [],
  has_targets: true,
}

export const handlers = [
  http.post(api("/api/v1/auth/refresh"), () =>
    HttpResponse.json({
      user: USER,
      token: { access_token: "test-access-token", token_type: "bearer", expires_in: 900 },
    }),
  ),
  http.get(api("/api/v1/auth/me"), () => HttpResponse.json(USER)),
  http.post(api("/api/v1/auth/login"), () =>
    HttpResponse.json({
      user: USER,
      token: { access_token: "test-access-token", token_type: "bearer", expires_in: 900 },
    }),
  ),
  http.get(api("/api/v1/clients"), ({ request }) => {
    const url = new URL(request.url)
    const query = url.searchParams.get("query")?.toLowerCase()
    if (query && !CLIENT.name.toLowerCase().includes(query)) {
      return HttpResponse.json({ items: [], next_cursor: null })
    }
    return HttpResponse.json(CLIENT_LIST)
  }),
  http.get(api("/api/v1/portfolios"), () =>
    HttpResponse.json({ items: [PORTFOLIO], next_cursor: null }),
  ),
  http.get(api("/api/v1/portfolios/:portfolioId"), () => HttpResponse.json(PORTFOLIO)),
  http.get(api("/api/v1/portfolios/:portfolioId/transactions"), () => HttpResponse.json([])),
  http.get(api("/api/v1/analytics/portfolios/:portfolioId/performance"), () =>
    HttpResponse.json(PERFORMANCE),
  ),
  http.get(api("/api/v1/analytics/portfolios/:portfolioId/allocation"), () =>
    HttpResponse.json(ALLOCATION),
  ),
  http.get(api("/api/v1/analytics/book"), () => HttpResponse.json(BOOK)),
  http.get(api("/api/v1/market/overview"), () =>
    HttpResponse.json({
      macro: [MACRO],
      quotes: [QUOTE],
      gainers: [QUOTE],
      losers: [],
    }),
  ),
  http.get(api("/api/v1/market/macro/:code"), () => HttpResponse.json([MACRO])),
  http.get(api("/api/v1/instruments"), () =>
    HttpResponse.json({
      items: [
        {
          id: "01920000-0000-7000-8000-000000000301",
          symbol: "PETR4",
          name: "Petrobras PN",
          asset_class: "equity",
          currency: "BRL",
          mic: "BVMF",
          isin: "BRPETRACNPR6",
          cfi: "ESVUFR",
          is_active: true,
        },
      ],
      next_cursor: null,
    }),
  ),
  http.get(api("/api/v1/instruments/:symbol/quote"), () => HttpResponse.json(QUOTE)),
  http.get(api("/api/v1/instruments/:symbol/history"), () =>
    HttpResponse.json([
      { date: "2026-05-01", close: "35.10", currency: "BRL" },
      { date: "2026-06-01", close: "38.72", currency: "BRL" },
    ]),
  ),
]

export const server = setupServer(...handlers)

export type { components }
