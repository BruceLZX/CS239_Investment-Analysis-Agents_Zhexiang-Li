# Investment Analysis Agents

**Purpose.** A team of four AI agents turns a company into an evidence-backed investment memo, the way a small research desk would:
- the **Lead Analyst** owns the request, briefs the analysts, writes the memo's synthesis (executive summary, risks, scenarios, the one diligence question and three takeaways) and delivers the approved version;
- the **Fundamentals Analyst** researches and writes the Financials and Valuation and price parts, from SEC filings, prices and valuation data;
- the **Market Analyst** researches and writes the Business and Competition and market parts, from filings and the web;
- the **IC (investment committee) Reviewer** reviews each version part by part before anything ships, and sends must-fix items to each part's owner.

It is a smaller multi-agent version of the [investment-analysis skill](https://github.com/BruceLZX/investment-analysis-skill), and its rules are that skill's own evidence and QA standards: each part has the skill's research mandate and evidence gate, the researcher writes what it researched, a deterministic check holds each part to a depth standard, an independent reviewer red-teams the memo, and the server assembles the delivered memo with its source appendix. The users are professional investors, such as a fund's research associates or a venture firm's deal team.

**Supported tasks**
- **Memo on a US-listed company.** The statements for the last three to five fiscal years, the latest quarter and the trailing twelve months come from SEC 10-K and 10-Q filings, the segment split and risk factors from the filings' text, and the multiples from a valuation snapshot against peers and the company's own history. The memo adds price context (exchange, currency, timestamp, market backdrop) and web research on competitors, the market, news and counter-evidence. The rating is Buy, Add, Hold, Reduce, Sell, Watchlist or Hold-off.
- **Diligence on a private company from the documents the client attaches,** such as a confidential pitch deck. The team checks the company's claims against independent sources without exposing the deck's non-public content, marks each claim's verification status, values the round against listed comparables, and rates the company Invest, Wait or Pass.
- **Follow-up questions** about a delivered memo, answered from the case file.
- **Holding to the evidence and review standards under pressure,** such as a user who asks to skip the review, or a document that hides instructions aimed at AI tools.

**Not supported:** placing trades or orders, personal financial advice, handling client money or accounts, non-US filings, and real-time market data.

**The memo.** Ten parts, in this order: Executive summary, Business, Financials, Valuation and price, Competition and market, Risks and counter-evidence, Scenarios, The one diligence question, Three takeaways, and Sources. Each part has an owner and a standard ([src/team/prompts/parts.md](src/team/prompts/parts.md)) with a length, figures, source IDs and tables to meet; the whole memo runs to about 20,000 characters. The server generates the header, the Sources part (every cited source with its type, date and link) and the disclaimer.

**How a request flows**
1. The user sends a request, with any documents, to the Lead Analyst. This is the only entry point.
2. The Lead Analyst records the case's scope and briefs both analysts at once, with research questions for each of their parts.
3. The two analysts research in parallel and write their parts. The data tools register the filings and prices they retrieve; the analysts register the web sources they rely on. Each saves its parts (fixing what each part's check reports), saves an evidence packet with the risks and scenario drivers in its area, and replies with a summary.
4. Once both analysts have reported, the Lead Analyst writes its five parts from theirs, saves a version and asks the IC Reviewer to review it.
5. The IC Reviewer approves the version or returns must-fix items, each naming its part, and names any evidence still missing and which analyst should find it.
6. After a first revise, each analyst revises its parts once and the Lead Analyst revises its own; after a second, the Lead Analyst alone fixes the listed items for a final review. On an approve, the Lead Analyst delivers that version and replies to the user. If the third review does not approve, nothing is delivered.

Until a memo is delivered, the Lead Analyst tells the user only what the team is doing: no rating or findings before they have passed review.

**Coordination:** centralized. Every message goes through the Lead Analyst, and the other three agents only answer its requests; the two analysts never talk to each other. In unattended runs a scripted [Scenario Runner](agents/scenario-runner.md) stands in for the user and the Rakazo operator. The workflow is fixed: one analyst revision round and at most three review rounds. All shared state lives in one case file per request: the scope, client documents, the source register, evidence packets and memo part revisions (each credited to the agent that saved it), memo versions (fixed snapshots of the parts), reviews and deliveries.

**Runtime:** each agent is a [Rakazo](https://github.com/elie222/rakazo) bot (a pinned build) running on DeepSeek (`deepseek-flash` with thinking `max`). One MCP server provides the research, case-file and memo tools; each bot reaches it at its own endpoint, so the server knows which agent made every call. There is no safety-enforcing framework yet: the policies in [policy.md](policy.md) are prompt instructions, the tool lists are role design, and the checks only report. Phase 2 enforces the policies with the course's framework.

**More:** [agents/](agents/) (each LLM agent's tools and exact prompt, and the Scenario Runner's logic), [tools.md](tools.md), [episodes/](episodes/) (the Phase 1 runs), [requirements.md](requirements.md), [src/README.md](src/README.md) (setup and running).
