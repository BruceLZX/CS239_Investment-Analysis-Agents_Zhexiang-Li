# Analysis Core

Use this file for every full investment report. It defines the evidence gate, section writing contract, and red-team standard.

## Contents

- Core Method
- Mandatory Evidence Gate
- Section Writing Contract
- Deal Thesis Workflow
- Red-Team Pass
- Writing Standard

## Core Method

Start with a testable investment thesis:

```text
If [market/customer need] is real, and [company capability] is defensible, and [go-to-market/unit economics] can scale, then [investment outcome] is attractive at [valuation/terms], unless [killer risks] materialize.
```

For each major section, answer:

1. What is the concrete claim?
2. What evidence supports it?
3. What evidence weakens or contradicts it?
4. What mechanism explains why it matters economically?
5. How does it compare with peers, substitutes, base rates, or benchmarks?
6. What is the investor implication: invest, pass, wait, price lower, or diligence further?

Do not write a section as a list of facts. Convert facts into judgement.

## Mandatory Evidence Gate

Do not draft the final report until every material section has an evidence packet in `_work/evidence_matrix.md`. Evidence may include public web sources, user-provided files, filings, databases, industry reports, patents, job posts, media interviews, customer/procurement records, or clearly labelled analyst estimates.

Minimum evidence packet per section:

| Required item | Minimum standard |
| --- | --- |
| Search work | 3-6 targeted queries unless user-provided materials are sufficient. |
| Sources opened | At least 2 independent sources; 3+ for market, competition, team, funding, financials, and risk when public data exists. |
| Source IDs | At least 2 distinct source IDs per section in `_work/evidence_matrix.md`; the final HTML should usually show 3+ distinct source IDs per major section. |
| Primary/source-of-truth check | At least 1 primary or near-primary source where available: filing, company page, registry, patent, investor announcement, regulatory record, official report, customer/procurement record. |
| Mechanism | Explain how the evidence changes economics, adoption, pricing power, risk, financing need, valuation, or exit probability. A fact without mechanism is not analysis. |
| Public-equity source-of-truth | For listed companies, use primary filings or company IR for financial statements and record market data timestamp, exchange, currency, latest price, market cap, and enterprise value if available. |
| Public-equity financial analysis | For listed companies, analyze income statement, balance sheet, cash flow statement, notes/accounting quality, valuation, peer comparison, and stock-price context before making a recommendation. |
| Company-claim verification | Mark material pitch-deck claims as verified, partially verified, unverified, contradicted, or not publicly disclosed. |
| Quantification | At least 2 numbers, ranges, or proxies for measurable sections; if unavailable, state what evidence is missing. |
| Comparison | At least 1 competitor, benchmark, base rate, industry norm, or historical comparable. |
| Counter-evidence | At least 1 contradicting source, weakness, adverse case, or reason the thesis may fail. |
| Investor implication | A decision-relevant conclusion: invest, pass, wait, lower valuation, add condition, or request diligence. |

The `_work/evidence_matrix.md` table is a hard gate. Each section's `Deep Evidence Table` must contain source IDs, source type, finding/fact, mechanism, benchmark or peer context, weakening evidence, investor implication, confidence, and follow-up. Do not mark a section complete by checking boxes unless those cells contain section-specific content.

Evidence gate failure rules:

- If a section has only company-provided material, write it as low-confidence and do not make a strong positive claim.
- If no independent source can verify a claim, explicitly say `未独立验证`.
- If a section lacks counter-evidence, add a red-team paragraph with the most plausible failure mode.
- If a section lacks quantification, state which metric is missing and how it affects investment confidence.
- If a section lacks peer/benchmark context, do not score it above 7/10.
- For a public-equity report, do not issue Buy/Add/Sell/Reduce before analyzing latest price/valuation, income statement quality, margin drivers, cash flow conversion, working capital, capex, balance-sheet health, accounting notes, debt/liquidity, capital allocation, and downside risk. If financial statements or price data cannot be obtained, make that the central limitation and use Watchlist/Hold off unless the user only asked for a preliminary screen.

## Section Writing Contract

Each final section must cover the full analytical logic, but it should read like an investment memo, not a compliance checklist. Use judgement, evidence, mechanism, comparison, counter-evidence, investor implication, confidence, and diligence questions as the internal reasoning scaffold. Do not force every section to show the same subheadings such as `判断 / 证据 / 机制 / 对标 / 反证 / 投资含义 / 待验证问题`.

The final report should not become pure black text on a white background. Use visual hierarchy and compact evidence displays to make dense analysis readable, while avoiding repetitive card stacks.

Internal workflow language must not appear in the final report. Never write sentences that explain how the section should be written, such as `本节要把证据等级...放在同一条逻辑链`, `不能被写成`, `而不是把材料拆成孤立事实`, or `source ID只用于锁定证据来源`. The final report should analyze the company, not describe the report-writing rubric.

Preferred section shape:

1. Start with a short thesis sentence that states the section-level judgement.
2. Explain the evidence in narrative paragraphs, weaving in source confidence, dates, and specific numbers.
3. Show why the evidence matters economically or strategically.
4. Compare with peers, substitutes, base rates, or historical analogs where it changes the decision.
5. Bring the main weakness or contrary evidence into the same discussion rather than isolating it mechanically.
6. End with the investor implication and the most decision-relevant open questions.

Use tables, KPI strips, risk matrices, scenario tables, or short callout cards when they improve scanability. Use explicit micro-headings only when they fit the section's content, not as a repeated template. Good micro-headings are content-specific, for example `现金流质量比利润表弱`, `监管路径是估值折扣的来源`, or `客户验证仍停留在试点阶段`.

Recommended readable section pattern:

- 1 short opening judgement paragraph.
- 2-4 analytical paragraphs, each with a clear point and evidence.
- 1 compact visual element when useful: KPI dashboard, mini table, risk matrix, timeline, scenario table, or source/confidence callout.
- 1 short closing sentence or small callout for investor implication/open question.

Use visual components selectively:

- Use a KPI/dashboard strip for numbers that need comparison.
- Use a table for peers, financial trends, milestone gates, or scenario assumptions.
- Use warning/danger callouts for decision-changing risks, not every weakness.
- Use source/confidence tags inline or at paragraph ends to preserve credibility without interrupting flow.
- Use bullets only for short lists; avoid long bullet walls.

Avoid rigid writing patterns:

- Do not write `{section name}判断`, `{section name}的机制`, `{section name}的benchmark`, `{section name}原件优先级`, `{section name}决策门槛`, or `{section name}决策清单`.
- Do not repeat the same seven labels in every section.
- Do not make each section a stack of independent bullet cards.
- Do not replace structured cards with unbroken long paragraphs.
- Do not put evidence in one box and interpretation in another when a paragraph would read better.
- Do not add a token "对标" or "反证" sentence just to satisfy the form; integrate comparison and counter-evidence into the argument.
- Do not hide the recommendation until the end of a long fact list.
- Do not append the same `投资人读法`, `来源/Source`, `数字锚点`, `仍需确认`, or generic transaction-structure paragraph to every section. If a reader would recognize the paragraph from another section, rewrite it as section-specific analysis or delete it.
- Put full citations in one `数据来源与引用 / Source Appendix` module. Inline source/confidence tags should support the most important claims, not repeat the same source list in every paragraph.

Avoid shallow claims unless evidence-backed:

- "Market space is large."
- "Team background is strong."
- "Technology has barriers."
- "Business model is scalable."
- "Competition is intense."
- "Risks are controllable."

Rewrite them into concrete questions: which market segment, which team achievement, which moat type, which scaling constraint, which competitor, and which risk-mitigation milestone.

## Deal Thesis Workflow

Use `_work/thesis_table.md` to structure the 5-minute briefing and final recommendation:

| Thesis component | Current belief | Evidence | Counter-evidence | Confidence | What would change it |
| --- | --- | --- | --- | --- | --- |
| Customer pain | | | | | |
| Product advantage | | | | | |
| Market timing | | | | | |
| GTM scalability | | | | | |
| Unit economics | | | | | |
| Team execution | | | | | |
| Valuation fit | | | | | |
| Exit path | | | | | |

For public equities, add rows for:

| Thesis component | Current belief | Evidence | Counter-evidence | Confidence | What would change it |
| --- | --- | --- | --- | --- | --- |
| Current price vs. intrinsic value | | | | | |
| Earnings quality | | | | | |
| Free cash flow conversion | | | | | |
| Balance-sheet health | | | | | |
| Consensus/guidance delta | | | | | |
| Catalysts and timing | | | | | |
| Position sizing | | | | | |

## Red-Team Pass

Before finalizing, answer:

- What fact, if wrong, would most damage the thesis?
- Which claim relies only on company-provided material?
- Which section is mostly generic and needs more evidence?
- Which risk is mentioned but not priced into the recommendation?
- What would a skeptical investment committee partner challenge first?
- Is the conclusion still defensible if the market is 50% smaller, CAC is 2x higher, revenue is 30% lower, or financing takes 6 months longer?
- For public equities: is the conclusion still defensible if valuation multiples compress, free cash flow is 30% lower, refinancing costs rise, receivables/inventory require a write-down, or the balance sheet cannot support the bear case?

If the red-team pass finds a shallow section, go back to search. Do not solve it by adding longer wording without new evidence.

## Writing Standard

Use this paragraph pattern:

```text
Claim -> evidence -> interpretation -> investor implication -> confidence / open question.
```

The report should feel like an investment committee memo, not an encyclopedia entry.

## Citation and Source Reliability Standard

Every delivered HTML/PDF report must include a consolidated source appendix with source ID, name, link or local `sources/` path, source type, confidence, and the claims supported. Treat source reliability hierarchically: filings, regulators, company IR, official registries, and primary documents are strongest; company pitch materials are useful but should be marked as company-provided; reputable media, industry databases, app stores, patent records, and product registries are corroborating evidence; reposts, aggregators, and unsourced summaries require caution. If a material claim cannot be traced to a source ID, downgrade confidence or remove the claim.
