# The report's sections

Each "##" section below is one report section's standard, condensed from the playbooks
(src/team/playbooks). team/profiles.py gives each bot the standards for the sections it writes, with the floors,
components and tables from tools/sections.py, which the checks use too. "## standard" is the writing standard for every
section and "## components" the syntax of the visual components. "## Departures from the playbooks" is for readers of this
repository; no bot receives it.

## standard

- **Shape** (analysis_core.md "Section Writing Contract"): open with the section plan's thesis sentence, a judgement about the company; then paragraphs that go claim, evidence [S#], interpretation, investor implication, confidence or open question. Cover judgement, evidence, mechanism, comparison (peers, benchmark, base rate or history), counter-evidence, investor implication, confidence and diligence questions, without showing those as labels: no "Economic mechanism:", "Investor implication:" or "{section} judgement" headings. Use content-specific micro-headings ("### Cash conversion is weaker than profit") only where they help.
- **Depth floor:** at least 2,500 characters, 6 analytical paragraphs, 8 figures, 4 distinct source IDs and 6 mentions of sources (in words, tags or a Source column). Write 7,000-8,500 characters: the server refuses a section over 9,000, the most one model call can write. Depth is evidence density, not length: one real judgement with its evidence, comparison and priced risk beats padding.
- **Citations:** cite a paragraph once, with one tag at the end of it ([S3] or [S3, S7]); at most 6 inline tags a section. Every table of figures has a Source column. Every paragraph, list item or table row with a material figure carries a source ID (N2).
- **Precision** (company_deep_dive_playbook.md "The Granularity Benchmark"): exact figures with unit, period and date; full names of people, institutions and products; dated events (YYYY-MM or YYYY-MM-DD, never "recently"). When data is missing, say exactly what is missing, how material it is and which source would settle it ("not disclosed"), and ask the user for it when a registry needs a login.
- **Claims:** a claim resting only on company material says so: verified, partially verified, unverified, contradicted or not publicly disclosed (N3).
- **Banned:** empty phrases ("huge market", "strong team", "high barriers to entry", "clear business model", "fierce competition", "risks are manageable", "well positioned"); vague counts ("about 5", "many patents", "experienced team"); any sentence about how the report or a section is written; the same paragraph or block reused across sections; names of the team's bots, tools or records (N6).
- **Language:** write in English, whatever language the request or a source is in. The template supplies each section's title, so start straight with the text.

## components

A component is a Markdown table or list inside a fence named after it (here a risk matrix); the server renders it into the report template. Each one listed for your section is required. Any other Markdown table becomes a data table automatically, and every [S#] becomes a link to the source appendix.

```
::: risk-matrix
| Column | Column | Source |
|---|---|---|
| ... | ... | S3 |
:::
```

## executive_summary
- For a listed company, open with a 3-5 sentence market snapshot: price, market cap, the move since the last results and the market regime (index trend, rates, VIX) that frames the call.
- The verdict and action (the version's rating word, position sizing or deal action, horizon), the composite score from section 14, three to five strongest positives and most important risks, key facts, the valuation band or the round's terms, the evidence confidence, the follow-up diligence, the one question and three takeaways.
- The consensus view and whether the thesis differs from it; if there is no edge, say the thesis is consensus.
- Components: verdict (Rating | Action | Composite score | Confidence | Horizon | Source), briefing (at least 5 cards: Card | Text | Source), efficiency (revenue, profit or burn, valuation, margin: Measure | Value | Source), one-question (the question, a blank line, why it decides the case), takeaways (three numbered decision statements, each with a figure and source).
- At least 900 characters. Written last, from what the sections actually show; it adds no new facts.

## company_overview
- What the company is: legal entity map (Entity | Jurisdiction | Type | Role | Ownership % | Controller | Source) with exact ownership, which entity holds the key licenses, IP and contracts, VIE or holding structures and their enforceability risk; for a listed company: exchange, ticker, currency, shares outstanding, free float and dual-class voting.
- The business model in one paragraph: customer, buyer, budget owner and how the company grows.
- A timeline of 8-15 dated milestones (founding, products, financing, team, regulatory, commercial, strategic).
- A private company's cap table (Shareholder | Class | % ownership | % votes | Source): share classes, liquidation preferences, anti-dilution, option pool, board seats and protective provisions; what is unknown is material.
- Components: kpi (4-8 decision metrics: Metric | Value | Benchmark | Signal | Source; Signal good, warn or critical), timeline (Date | Event | Significance | Source).

## team
- Each founder, C-suite executive and key technical leader: education (Degree | Institution | Year | Focus), career (Period | Organization | Role | Achievements), patents, publications, prior exits, board roles and awards, each traceable to a source; for a listed company, the proxy statement's officers, pay and ownership.
- Founder-market fit; who invents, who sells, who raises money; the hires still missing (CFO, enterprise sales, regulatory, manufacturing, clinical, supply chain).
- A team assessment matrix (Dimension | each leader | Team) on technical depth, industry years, prior exits, scaling, fundraising, key-person dependency and retention risk.
- What public records confirm or contradict, and the reference checks a diligence team should run.
- Component: evidence (the strongest proof of, or doubt about, the team's ability to execute).

## technology_product
- Each core technology: how it works (5-10 sentences), its performance metrics (Metric | Value | Method | Source), the academic or clinical evidence (papers with authors, journal, year), competing approaches at the same depth (a comparison table), the roadmap and the key technical debates.
- The moat: Barrier | Difficulty (1-10) | Why | Time to replicate, and the replication test (how long a funded team of 50 would need).
- Patents: Patent or application number | Title | Jurisdiction | Filed | Granted | Status | Relevance, granted versus pending, freedom-to-operate risk.
- Product inventory (Product | Stage | Launch | Revenue or share | Margin | Next milestone) and per-product detail: the buyer's workflow before and after, the standard of care or the alternatives, pricing and unit economics.
- Third-party dependencies (cloud, models, chips, licensed IP) and technology readiness, with evidence.
- Component: evidence.

## market
- Size the market two ways, top-down and bottom-up (population x price), as TAM, SAM and SOM with the near-term obtainable revenue, each figure with its source and year; growth (CAGR) and why now.
- Domestic versus international: a regional table (Region | Market size (year) | Growth | Company's position: entered, planned or blocked | Barriers | Key competitors | Source), and the eight market systems where material (home, revenue, expansion, supplier, comparable, capital, exit markets and the investor's perspective); or the playbook's sentence that geography is not material.
- Budget owner, procurement cycle, willingness to pay; whether demand is organic or created by policy or subsidy, with the policy documents and dates.
- Component: evidence.

## competition
- Competition is per product: for each product, direct competitors (Competitor | Product | Technology | Regulatory status | Performance | Price | Share | Strengths vs us | Weaknesses vs us | Source), indirect substitutes, pipeline entrants and the status quo ("do nothing").
- Classify each player (geo_market_context_lens.md): direct competitor, local substitute, international competitor, strategic comparable, future entrant, non-comparable. Name the most dangerous competitor and why, the company's wedge, market shares with years, and a positioning table (Product | Leader | Challenger | Niche | Emerging threat).
- At least one authoritative source per competitor (its filing, site, regulator database or a paper), never a media summary alone.
- Components: evidence, quad (SWOT: Quadrant | Points separated by ";" | Source, with Strengths, Weaknesses, Opportunities and Threats rows).

## business_model
- How money flows: who pays, for what, when, and the revenue model (subscription, per unit, consumables, licensing, take rate).
- A unit-economics waterfall (revenue per unit or customer, direct costs, gross profit and margin, CAC, onboarding, support, contribution, LTV, LTV:CAC and payback in months) and a pricing table, each against peers or benchmarks.
- The model-specific KPIs (SaaS: ARR, retention, CAC payback, burn multiple; hardware: BOM, margin at scale, warranty, working capital; marketplace: take rate, liquidity) and the year the unit economics break even.
- Component: evidence.

## financials
- Listed: at least three fiscal years plus the latest quarter, from the filings. Income statement (volume, price, mix, FX, one-offs; segment and margin drivers; reported versus adjusted), cash flow (net income to operating cash flow to free cash flow, working capital, maintenance versus growth capex), balance sheet (net cash or debt, maturities, interest cover, goodwill, receivables and inventory quality, leases, contingencies), notes and accounting quality (revenue recognition, capitalization, impairments, related parties, auditor), returns (ROE, ROIC, working-capital days) and capital allocation; the red flags in the lens.
- Private: the company-reported figures with their verification status, the reconstructed burn rate and runway (labelled as estimates), and missing financials treated as a risk.
- Base, upside and downside sensitivity, and the one variable that moves the outcome most.
- Tables: the statements (Line item | years | Source) and returns and working capital. Component: info (warning or danger) for the most serious red flag.

## funding_valuation
- Listed: a trading snapshot (price with exchange, currency and timestamp; market cap; enterprise value; 52-week range; momentum against the index; volume and liquidity), valuation by at least two methods suited to the company type (multiples against at least three peers and the company's own five-year range, plus DCF or another method), what the price implies, the consensus and guidance (or "not disclosed"), dated catalysts and the margin of safety.
- Private: every round (Date | Round | Amount | Valuation | Investors, all named | Use of funds | Source), the current round's terms (pre- and post-money, security, liquidation preference, option pool), implied multiples against listed peers and private rounds, dilution and investor quality.
- Tables: funding rounds or the trading snapshot, valuation methods (Method | Inputs | Value | Source) and peer multiples.

## strategy
- The plan across product, customers, revenue, regulation, hiring, geography and capital, with dated milestones (a table: Milestone | Target date | Status | What it proves | Source) and whether resources fit the plan.
- Named partnerships with their scope and signing dates (Partner | Scope | Signed | Status | Source); second curves as adjacencies or distractions.
- What must be true in 12 months, and the signposts that would show it is or is not happening.

## risk
- 6-10 risks ranked by probability, impact, timing, detectability and cost to mitigate, with fatal risks separated from manageable execution risks; each with its probability, its impact on value (e.g. "-25% EV"), the milestone or evidence request it links to, an early-warning signal and a mitigation.
- The strongest case against the thesis, the downside stress tests (market 50% smaller, CAC 2x, revenue 30% lower, financing 6 months late; listed: multiples compress, free cash flow 30% lower, refinancing costs rise), and unknown unknowns where information is thin.
- Policy, regulatory and geopolitical risks from the regulatory evidence, priced rather than listed.
- Components: risk-matrix (Risk | Probability | Impact | Level | Timing | Signpost | Mitigation | Source; Level critical, high, medium or low), info (danger) for the risk that would break the thesis.

## thesis
- The thesis in this form: if the need is real, and the capability is defensible, and the economics scale, then the outcome is attractive at this price or these terms, unless the killer risks materialize.
- Consensus versus our view, with the evidence for any difference; bull, base and bear cases with probabilities that add up to 100%, their drivers and their outcome (price, return or MOIC; milestone scenarios for early-stage or data-poor cases); the 3-5 key assumptions, ranked (Assumption | Confidence | What would disprove it | Impact if wrong | Early warning | Source).
- Historical analogs close enough to teach a decision rule (or say there is none); the price or terms at which the case turns attractive or unattractive; the decision tree: invest now, wait for a milestone, pass, or invest with conditions.
- Components: scenarios (Scenario | Probability | Drivers | Outcome | Signposts | Source with Bull, Base and Bear rows), analogs (Analog | Kind best or cautionary | Period | Lesson | Source).

## exit
- Named acquirers or listing venues, never just "IPO or M&A": who buys, why, when, and which asset (Route | Named buyer or venue | Rationale | Timing | Likelihood | Source).
- Precedent exits and their multiples (Transaction | Year | Value | Multiple | Source), the expected holding period, return sensitivity to the entry valuation, and policy tests (foreign-buyer limits, national-security review, sanctions, venue constraints, lock-ups).
- For a listed company: the realistic ways a holder realizes value (re-rating, buybacks, dividends, takeover premium) and liquidity for the intended position.

## esg
- Only the financially material issues: governance (board, control, dual-class voting, related parties, disclosure quality, information rights), privacy and data security, labor, environment, product safety and compliance culture (ESG issue | Why material | Evidence | Rating impact | Source).
- The regulatory record from the industry's registries and the courts: licenses, approvals, recalls, enforcement and litigation (Regulator or registry | Record | Date | Status | Source); what could not be checked and the user data requests filed for it.
- The policy and geopolitics impact matrix where material (Factor | Exposure | Probability | Impact on company | Mitigant | Source), with the jurisdictions mapped; or the playbook's sentence that policy is not material.

## scoring
- A weighted score table (Dimension | Weight | Score (1-10) | Rationale | Source) with the dimensions and weights below for the company type; the composite is the weighted average to one decimal, stated in the text. A dimension without a peer or benchmark comparison scores 7 at most.
- The recommendation and how it changes under the downside assumptions; the sensitivity of value to the 3-5 key assumptions, ranked, each with what would disprove it and its impact on value.
- Position sizing: listed, full, starter, watchlist only or zero, from the upside and downside, a Kelly fraction with its inputs and a cap, the maximum loss and the market regime (public_equity_financials_lens.md A4); private, the check size, valuation discipline, downside loss and follow-on reserve.
- The next diligence actions and the conditions for investing.
- Components: sensitivity (Rank | Assumption | Base | What would disprove it | Impact on value | Impact level | Early warning | Source; Impact level high, medium or low), takeaways (three numbered decision statements).

## Departures from the playbooks

Where the app departs from the playbooks, and why:
- **One analyst becomes nine bots.** The playbooks address one analyst working through every lens; here each lens has an owner, and the playbooks are read with `read_playbook`, since together they exceed Rakazo's 20,000-character limit on a bot's instructions.
- **Workflow files are case-file records.** `_work/*.md` become typed tool arguments, so the checks read fields instead of parsing Markdown tables.
- **Sections are written in Markdown, not HTML.** The server renders them into the report template, so the template's markup and its version marker cannot drift.
- **Checks report and never block.** The Phase 2 policy framework decides what to enforce, and the trace records every check.
- **Bugs in the original check scripts are fixed** (see each module in src/tools/qa/).
- **Scoring weights** are the app's own (tools/sections.py), since the report standard asks for a weighted score but defines none.
- **Review rounds are capped at three.** The playbooks loop until no Critical item remains; here a third failed review ends the case without delivery.
- **Evidence hierarchies.** The playbooks give three slightly different orders; the app uses the regulatory lens's (court and regulatory records first, OCR last) for source types and confidence.
- **Section numbering** follows the template's fourteen slots; the deep-dive playbook's own section numbers and benchmark codes differ, so headings are matched by name.
- **Reports in English.** The report template, section titles and check word lists are translated to English, and every report is written in English.
- **Inline source tags.** The original scripts allow 6 a section and 60 a report, which fourteen sections within their own limit exceed. The app keeps 6 a section, applies it to the executive summary too, and allows 90 a report (6 for each of fifteen). N2 asks for a source ID in every paragraph, list item or table row with a figure, so a paragraph carries one tag and a table its Source column.
