# Public Equity Financials Lens

Use this lens for listed companies, liquid secondary-market targets, tickers/security codes, or any request asking whether a stock is worth buying. Integrate it into the report; do not append it as a generic finance checklist. The purpose is professional financial statement analysis, not only debt or balance-sheet screening.

## Core Question

Decide whether the current share price misprices future cash flow, asset value, risk, or catalysts — **in the context of the current market regime, macro environment, and policy landscape.**

The report must answer:

1. What is the stock, exchange, currency, latest price, trading date/time, market cap, and enterprise value if available?
2. **What is the current market regime, and how does it affect this stock?** (bull/bear, sector rotation, risk appetite, liquidity, rates)
3. **How does the current international situation and policy landscape affect this company?** (trade policy, sanctions, geopolitical tensions, currency movements, capital controls)
4. What financial statements are the source of truth, and what period do they cover?
5. Are revenue, earnings, and cash flow improving for durable reasons or temporary reasons?
6. What do the income statement, balance sheet, cash flow statement, and notes reveal when read together?
7. Is the balance sheet healthy enough to survive the bear case?
8. Is valuation attractive relative to growth, quality, cyclicality, leverage, and peers?
9. What catalyst or evidence would make the market re-rate the stock?
10. What position size is justified by downside risk, evidence confidence, and macro exposure?

---

## Part A: Market Regime & Macro Overlay (Mandatory for All Public Equities)

This section must appear in the investment report before the financial statement analysis. It frames *when* and *under what conditions* the stock is being evaluated — a great company at the wrong macro moment can destroy as much capital as a bad company.

### A1. Current Market Regime Assessment

Capture the state of the market in which the stock trades:

| Dimension | What to Check | Why It Matters |
|-----------|--------------|----------------|
| **Broad index trend** | S&P 500 / SSE Composite / HSI / Nikkei level, YTD return, distance from 52W high/low | Context for beta and sentiment |
| **Market phase** | Bull market / correction / bear market / bottoming / topping | Determines whether fundamentals or liquidity dominate |
| **Sector rotation** | Is capital flowing into or out of this sector? Check sector ETF flows, relative strength vs. broad index | A stock can beat estimates and still fall if its sector is being rotated out of |
| **VIX / fear gauge** | Current VIX or equivalent, trend, percentile rank | High VIX = options premium matters, low VIX = complacency risk |
| **Interest rate environment** | Central bank policy rate, latest decision/guidance, 2Y/10Y yield, curve shape | Discount rate for DCF; growth vs. value preference |
| **Credit spreads** | IG and HY spreads, trending wider or tighter | Leading indicator of stress; affects leveraged companies |
| **Liquidity conditions** | Fed/ECB/PBOC balance sheet direction, reverse repo, MLF/LPR, SHIBOR | Drives multiple expansion or contraction |
| **Currency regime** | USD/CNY, DXY, relevant cross rates, FX volatility | Directly affects companies with foreign revenue/costs/debt |
| **Commodity pulse** | Oil, copper, lithium, steel — whichever inputs/outputs are material to the company | Input cost and end-demand signal |

**Output:** A 3-5 sentence "Market Snapshot" paragraph at the beginning of the executive briefing, e.g.:

> *As of 2026-07-10, the Hang Seng Index trades at 21,400 (-8% from its 52W high of 23,200), with the market in a consolidation phase following a 35% rally from Jan-Mar 2026. AI/semiconductor names continue to see inflows (+12% sector relative strength over 3M), while traditional consumption faces rotation pressure. The PBOC cut the 1Y MLF rate by 10bp in June, signaling continued accommodation. CNY has weakened 3.2% vs USD over the past quarter — a tailwind for exporters but a headwind for USD-denominated debtors.*

### A2. Stock Price & Trading Context

Go beyond "price = $X" and provide the trading narrative:

| Element | What to Capture |
|---------|----------------|
| **Price snapshot** | Last price, date/time, exchange, currency, market cap (local + USD), enterprise value |
| **Trading range** | 52W high/low, YTD high/low, distance from each; is the stock near a support/resistance zone? |
| **Price momentum** | 1M/3M/6M/1Y return vs. sector index vs. broad market — is this a leader or laggard? |
| **Volume profile** | Average daily volume (shares + USD), recent volume trend; is liquidity sufficient for the intended position size? |
| **Short interest** | % of float short, days to cover, trend (rising/falling) — potential squeeze risk or smart-money signal |
| **Insider trading** | Recent insider buys/sells (volume and direction over 3-6 months) — management conviction signal |
| **Institutional ownership** | % held by institutions, recent filings (13F for US, 季度报告 for CN mutual funds) — smart money tracking |
| **Analyst consensus** | Number of analysts, rating distribution (buy/hold/sell), consensus target price, estimate dispersion |
| **Earnings surprise history** | Last 4-8 quarters: beat/miss pattern, post-earnings drift direction |
| **Technical context** | Key moving averages (50D/200D), relative strength vs. sector, any obvious chart patterns (breakout, breakdown, range-bound) |

**Output:** A "Trading Snapshot" table early in the report:

```
| Metric | Value | Signal |
|--------|-------|--------|
| Last price | HK$ 385.20 (2026-07-10) | — |
| 52W range | HK$ 298 - 458 | Trading at 62nd percentile |
| YTD return | +14.3% vs. HSI -2.1% | Outperforming |
| Avg daily volume | HK$ 2.1B | Liquid for positions up to HK$ 500M |
| Short interest | 3.2% of float, 4.5 days to cover | Moderate, no squeeze signal |
| Insider trading (6M) | Net buyer (+HK$ 120M) | Mildly bullish |
| Consensus | 28 Buy / 6 Hold / 1 Sell; target HK$ 442 | 15% upside to consensus |
```

### A3. International Situation & Policy Impact

This is the "geopolitical and policy P&L" — map external forces to concrete financial impact on the company:

| Policy / Geopolitical Dimension | Assessment Framework |
|--------------------------------|---------------------|
| **Trade policy & tariffs** | Active tariffs on company's products/inputs? Pending investigations? Effective rate and revenue/cost exposure % |
| **Export controls / sanctions** | Is the company, its suppliers, or its customers on any entity list? Dual-use technology risk? Secondary sanctions exposure? |
| **Cross-border investment restrictions** | CFIUS/FIRRMA/inbound screening, outbound investment restrictions, capital controls — do any block the company's M&A, fundraising, or market access? |
| **Supply chain sovereignty** | Is the company's supply chain subject to "de-risking," "friend-shoring," or forced localization? Chips Act / IRA / EU Chips Act / China self-sufficiency policies — who benefits, who loses? |
| **Data & cybersecurity regulation** | GDPR / DSA / PIPL / data localization requirements, cross-border data transfer restrictions, algorithm audits |
| **Currency & capital flow** | FX exposure (revenue, cost, debt by currency), hedging policy, convertibility risk, capital control risk |
| **Geopolitical hotspots** | Taiwan Strait, South China Sea, Russia-Ukraine, Middle East — does the company have material assets, supply chains, or customers in affected regions? |
| **Election / policy calendar** | Upcoming elections, leadership transitions, policy reviews that could change the regulatory landscape materially |

**Output:** A "Policy & Geopolitics Impact Matrix" table:

```
| Factor | Exposure | Probability | Impact on Company | Mitigant |
|--------|----------|-------------|-------------------|----------|
| US Section 301 tariff (25% on [product]) | 18% of revenue from US | Active | -$4.5B annual revenue at risk | [Mitigant] |
| EU anti-subsidy investigation | 12% of revenue from EU | 30% in 12 months | -$3.0B if duties imposed | [Mitigant] |
| CNY depreciation (3-5% further) | 40% of COGS in USD | Medium | Margin compression 80-120bp | [Mitigant] |
| Taiwan Strait escalation | Factory in Kaohsiung (15% capacity) | 10% tail risk | Supply disruption 2-4 quarters | [Mitigant] |
```

### A4. Regime-Appropriate Strategy

Tie the macro assessment to investment action:

| Market Regime | Implication for This Stock | Position Approach |
|--------------|---------------------------|-------------------|
| Risk-on / bull market | High-beta stocks outperform; growth story gets rewarded | Can size up, focus on upside |
| Risk-off / bear market | Quality and low leverage outperform; cyclicals punished | Defensive sizing, focus on balance-sheet strength |
| Sector rotation in | Tailwind regardless of fundamentals | Time entries, can add on strength |
| Sector rotation out | Headwind — good results may not be rewarded | Reduce, wait for capitulation |
| High volatility (VIX > 25) | Options premium high; sharp reversals common | Scale in slowly, use limit orders |
| Policy uncertainty elevated | Multiple compression likely | Discount target multiple by 10-20% |

This regime assessment should directly inform the position sizing recommendation in the final scoring section.

## Source Priority

Use primary or near-primary sources first:

- US: SEC EDGAR 10-K, 10-Q, 8-K, DEF 14A, company IR releases.
- Mainland China A-share: 巨潮资讯/CNINFO, SSE/SZSE/BSE company announcements, annual/interim/quarterly reports.
- Hong Kong: HKEXnews, company annual/interim reports, announcements.
- Other markets: local exchange filings, regulator filings, company IR documents.
- Market data: exchange pages, reliable finance tools, broker/market-data terminals, or clearly cited finance aggregators. Record timestamp, currency, and exchange.

Do not rely only on media summaries or finance aggregator snippets for financial statements. Aggregators are acceptable for a first pass or market data, but material financial claims should trace back to filings or company IR.

## Required Workpapers

For public equities, `_work/evidence_matrix.md` must include dedicated rows for:

- Ticker / exchange / currency / latest price / market cap.
- Income statement: revenue, segment/product/geographic mix, gross margin, operating margin, net income, EPS, taxes, minority interests, and recurring vs. non-recurring items.
- Cash flow statement: operating cash flow, capex, free cash flow, FCF conversion, working-capital drivers, financing cash flow, dividends/buybacks/issuance.
- Balance sheet: cash, debt, net debt/cash, asset quality, leverage, liquidity, maturity profile, receivables, inventory, goodwill/intangibles, leases, provisions, contingent liabilities, and restricted/pledged assets where available.
- Notes and accounting quality: revenue recognition, capitalization policy, impairments, fair-value gains/losses, subsidies, related-party transactions, auditor opinion, restatements, and key estimates.
- Valuation: P/E, EV/EBITDA, EV/Sales, P/B, FCF yield, dividend/buyback yield when relevant.
- Peer comparison and historical trading range.
- Consensus, guidance, profit warning, order/backlog, or other expectation anchor where available.
- Catalysts, risks, and downside scenario.

If data is unavailable, write `未披露/未找到` and explain how that limits the conclusion.

## Professional Financial Statement Analysis

Analyze trends over at least 3 years when available, plus the latest interim/quarterly period.

Read the three statements and notes together. The analysis should explain economic reality, not only reproduce line items. Use common-size analysis, year-over-year and multi-year CAGR/trend analysis, peer comparison, and ratio analysis where data supports it.

Income statement:

- Separate volume, price, mix, FX, acquisition/disposal, one-off, and accounting effects where possible.
- Check gross margin and operating margin drivers rather than only reporting changes.
- Flag stock-based compensation, capitalization of expenses, fair-value gains, subsidies, asset sales, impairment reversals, and other non-operating items.
- Compare reported net income, adjusted/non-GAAP profit, operating profit, EBITDA, EPS, and tax rate; explain which profit measure is most decision-relevant and why.
- For segment disclosures, identify which segment creates value, which consumes capital, and whether mix shift improves or weakens quality.

Cash flow:

- Compare net income to operating cash flow and free cash flow.
- Identify working-capital pulls: receivables, inventory, payables, contract assets/liabilities, prepayments.
- For capex-heavy companies, distinguish maintenance capex from growth capex when possible.
- Treat earnings growth with weak cash conversion as lower quality unless there is a clear temporary reason.
- Reconcile CFO, capex, acquisitions/disposals, financing cash flows, dividends, buybacks, issuance, and debt repayment to the change in cash.
- Check whether free cash flow is structurally positive, cyclical, temporarily depressed, or dependent on working-capital release.

Balance sheet:

- Assess net cash/debt, debt maturity, interest coverage, refinancing risk, pledged assets, guarantees, off-balance-sheet commitments, lease liabilities, and contingent liabilities where disclosed.
- Assess asset quality: goodwill/intangibles, capitalized R&D, inventory age, receivable concentration/aging, related-party balances, investment property/fair value assets, restricted cash.
- Compare leverage and liquidity with peer norms and cyclicality.
- State whether assets and liabilities are healthy, stretched, or fragile under the bear case.
- Analyze equity quality: retained earnings, accumulated losses, minority interests, treasury shares, accumulated other comprehensive income, and dilution from options/convertibles.
- For banks/insurers/financials, replace industrial leverage metrics with capital adequacy, asset quality, NPL/credit cost, reserve coverage, duration/ALM, solvency, and regulatory capital metrics.

Notes and disclosures:

- Read accounting policies and key estimates before judging quality.
- Check revenue recognition, lease accounting, impairment testing, fair-value hierarchy, provisions, tax contingencies, related-party transactions, guarantees, pledges, restricted cash, commitments, and post-balance-sheet events.
- Flag auditor qualifications, emphasis of matter, material weakness, internal-control issues, delayed filings, restatements, regulator inquiries, or enforcement actions.

Return and efficiency:

- Calculate or discuss ROE, ROA, ROIC, asset turnover, working-capital turnover, inventory days, receivable days, payable days, cash conversion cycle, and incremental margins when relevant.
- Compare returns with cost of capital and peer ranges. A company that grows below its cost of capital may destroy value even if revenue grows.

Capital allocation:

- Review dividends, buybacks, issuance, M&A, related-party transactions, insider ownership, management incentives, and historical ROIC.
- Ask whether management compounds capital or dilutes/allocates poorly.

Forecast bridge:

- Build a compact bridge from historical results to bull/base/bear scenarios: revenue growth, margin, tax, capex, working capital, FCF, share count, and terminal/multiple assumption.
- Tie every forecast driver to evidence: backlog/order book, pricing, utilization, capacity, regulation, end-market demand, management guidance, consensus, or peer base rates.

## Market Data and Valuation

Always timestamp market data:

```text
Price as of [date/time timezone], exchange [exchange], currency [currency].
```

Use valuation methods appropriate to the company:

- Stable profitable company: P/E, EV/EBIT, FCF yield, DCF/sensitivity.
- Cyclical/industrial: mid-cycle earnings, EV/EBITDA, P/B, replacement value, downside book/asset value.
- Financials: P/B, ROE/COE, asset quality, capital adequacy, NIM, credit cost.
- Growth/software/platform: EV/Sales, gross profit multiple, FCF path, Rule of 40, retention if disclosed.
- Biotech/pre-revenue: cash runway, pipeline probability, milestone/risk-adjusted value.
- Distressed: liquidation/recovery value, liability stack, covenant/maturity wall.

Valuation must connect to fundamentals. Do not call a stock cheap only because the multiple is low; explain whether low multiple reflects cyclicality, leverage, governance, decline risk, accounting quality, or market neglect.

## Recommendation and Position Sizing

Use a clear public-equity action:

- Buy / Add / Hold / Watchlist / Reduce / Sell / Avoid.

Include:

- Current price context and valuation band.
- Bull/base/bear target or return range when data supports it.
- Downside drawdown or permanent-loss risk.
- Time horizon.
- Catalyst calendar.
- Evidence confidence.
- Position sizing guidance: full, starter, watchlist only, or zero position, with reasoning.

When evidence is incomplete, prefer `Watchlist` or `Hold off` over a false-precision Buy/Sell.

## Red Flags

Escalate these issues into risk and recommendation:

- Rising revenue with deteriorating cash conversion.
- Receivables/inventory growing much faster than revenue.
- High leverage with near-term maturity wall.
- Large goodwill/intangibles relative to equity.
- Repeated equity issuance or convertible dilution.
- Related-party transactions, guarantees, pledged shares, or restricted cash.
- Aggressive capitalization, subsidy dependence, fair-value gains, or non-recurring profit support.
- Auditor change, delayed filings, qualified opinions, restatements, enforcement actions.
- Management guidance misses or disclosure inconsistency.
