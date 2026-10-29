# The memo's parts

Each section below is one part's standard, taken from the investment-analysis skill's section mandates and evidence
gate. team/profiles.py gives each bot the standards for the parts it writes (the IC Reviewer gets them all) and adds
each part's length, figures, source IDs and tables from tools/memo.py's PARTS, which the part check uses too.

## standard

- **Shape:** open with a one-sentence judgement, then write paragraphs that go claim, evidence [S#], interpretation, and what it means for the investor. Prefer one real judgement with its evidence, comparison and priced risk over padding: length is not depth.
- **Analysis parts** (business, financials, valuation, competition, risks) also carry the skill's evidence gate: at least one comparison (peers, a benchmark or the company's history), one piece of counter-evidence, a statement of confidence ("Confidence: medium, because ..."), at least two independent publishers and at least one primary source (a filing, a regulator, official data or, for a private company, its own site or registry).
- **Figures:** every figure carries its source ID, and a table of figures has a Source column. Never invent a figure; write "not disclosed".
- **Concrete, not vague:** name the institution, the number and the date. No empty phrases such as "huge market", "strong team" or "well positioned".
- **Clean:** never write about the workflow or the team: no evidence packets, reviews, tool names, bot names, or notes on what the part should do.
- **Ownership:** save only the parts you own. The one exception is the Lead Analyst after a second review, which may revise any part to fix the items that review lists.
- **Saving:** save each part with `save_memo_part`, without its heading. Read the check it returns and fix what it reports, at most twice per part per brief. If a problem cannot be fixed with the evidence at hand, state the limitation in the part and list it in your packet's gaps.

## executive_summary

- For a listed company, open with a 3-5 sentence market snapshot: price, market cap, the recent move and the market backdrop.
- Then the verdict and the action: the rating (use the version's rating word exactly), position sizing (full, starter, watchlist or zero; private: invest now, wait for a milestone or pass) and the time horizon.
- The thesis in 2-3 sentences; the three strongest positives and the three biggest risks, each with its source IDs; whether the view is the consensus or differs from it, and why (if the team has no edge, say so); the valuation band or the round's terms; the evidence confidence; the follow-up diligence.
- Two tables: a verdict strip (Rating | Sizing | Price band or terms | Confidence | Horizon | Source), and a scorecard (Dimension | Score | Reason | Source) scoring Business quality, Financial strength, Valuation, Competitive position, Management and governance, and Risk from 1 to 10 (10 best), with a Composite row that is their simple average to one decimal.

## business

- What the company sells, to whom, and how the money flows; the mix and growth by segment, product and region (for a listed company the segment figures come from the 10-K text, items 1, 7 and 8; XBRL figures have no segment split); customer concentration; go-to-market; unit economics or pricing power where evidence exists.
- The moat, shown with evidence rather than adjectives.
- Management: capital allocation and disclosure quality (listed), or the founders' verified track record and the team's gaps (private).
- 5-8 dated milestones or catalysts.
- A revenue-mix table (private: product, buyer, pricing and verification status).

## financials

- Listed: the last three fiscal years plus the latest quarter, year to date and trailing twelve months: revenue and margin drivers, earnings quality (one-offs, stock-based compensation, working capital), cash conversion, capex, net cash or debt, capital allocation (buybacks, dividends), and red flags from the notes or management's discussion (10-K items 7 and 8).
- Private: the company-reported figures, each with its verification status, and an estimated burn rate and runway, labelled as estimates.
- Name the one variable that moves the outcome most, and its sensitivity.
- A statements table with a Source column.

## valuation

- Listed: a trading snapshot (exchange, currency, time, price, market cap, enterprise value); multiples against at least three peers and the company's own five-year range; what the price implies (the growth or margin it needs); the consensus view, or "not disclosed"; dated catalysts; the margin of safety.
- Private: the round's terms (pre- and post-money valuation, the security), the implied multiple against listed comparables and private rounds, dilution, and the likely exit routes.
- A snapshot table and a multiples table, each with a Source column.

## competition

- The market's size from two independent sources or methods; its growth, and what is changing now.
- Direct competitors, substitutes, international players, likely entrants and the "do nothing" alternative; market share, price and channel; the most dangerous competitor and why; how long the moat lasts.
- Regulation, and the geographies that matter.
- A competitor table and a market-size table, each with a Source column.

## risks

- Combine both analysts' risks and counter-evidence with the 10-K risk factors: 5-8 risks ranked by probability and impact, fatal versus manageable, each with a signpost to watch.
- The strongest case against the thesis.
- Stress tests: revenue 30% lower, compressed multiples, free cash flow 30% lower (private: financing 6 months late, a market half the size), and what each does to the rating.
- A risk matrix (Risk | Probability | Impact | Timing | Signpost | Source).

## scenarios

- Bull, base and bear cases with probabilities that add up to 100%, their drivers, the outcome (a price or return; private: MOIC) and the signposts that would show which is unfolding.
- The 3-5 assumptions that matter most, ranked by their effect on the outcome.
- Position sizing: full, starter, watchlist or zero (private: check size and reserves).
- A scenario table (Scenario | Probability | Drivers | Outcome | Signposts | Source) and an assumptions table.

## one_question

- The single answerable question that would most change the decision, why it would flip it, and how to answer it. Ask exactly one question.

## takeaways

- Three numbered takeaways, each a decision-relevant statement with a figure and its source ID.
