# Investment Analysis Agents

**Purpose.** A team of four AI agents turns a company into an evidence-backed investment memo, the way a small research desk would:
- the **Lead Analyst** owns the request and the memo;
- the **Fundamentals Analyst** gathers the numbers: financial statements, price and valuation, funding and round terms;
- the **Market Analyst** gathers evidence on the business: customers, competitors, market size, news and regulation;
- the **IC (investment committee) Reviewer** challenges each draft before anything ships, and names any evidence an analyst still has to find.

It is a multi-agent version of the [investment-analysis skill](https://github.com/BruceLZX/investment-analysis-skill), and its rules are that skill's own evidence and QA standards. The users are professional investors, such as a fund's research associates or a venture firm's deal team.

**Supported tasks**
- **Memo on a US-listed company.** Financials for the last three fiscal years come from SEC 10-K filings. The memo adds price context (exchange, currency, timestamp) and web research on competitors, news and counter-evidence. The rating is Buy, Add, Hold, Reduce, Sell, Watchlist or Hold-off.
- **Diligence on a private company from the documents the client attaches,** such as a confidential pitch deck. The team checks the company's claims against independent sources without exposing the deck's non-public content, marks each claim's verification status, and rates the company Invest, Wait or Pass.
- **Follow-up questions** about a delivered memo, answered from the case file.
- **Holding to the evidence and review standards under pressure,** such as a user who asks to skip the review, or a document that hides instructions aimed at AI tools.

**Not supported:** placing trades or orders, personal financial advice, handling client money or accounts, non-US filings, and real-time market data.

**How a request flows**
1. The user sends a request, with any documents, to the Lead Analyst. This is the only entry point.
2. The Lead Analyst briefs both analysts at once.
3. The two analysts research in parallel: the Fundamentals Analyst from SEC filings, prices and the web, the Market Analyst from the web. Each registers every source, saves an evidence packet and replies with a summary.
4. Once both packets are in, the Lead Analyst writes the memo, runs the memo check and asks the IC Reviewer to review that version.
5. The IC Reviewer approves the version or returns must-fix items, and names any evidence the packets lack and which analyst should find it.
6. On a revise, the Lead Analyst sends each named analyst one follow-up brief, revises once the new evidence is in (or straight away if none was requested) and asks for one re-review. On an approve, it delivers that version and replies to the user.

Until a memo is delivered, the Lead Analyst tells the user only what the team is doing: no rating or findings before they have passed review.

**Coordination:** centralized. Every message goes through the Lead Analyst, and the other three agents only answer its requests; the two analysts never talk to each other. In unattended runs a scripted [Scenario Runner](agents/scenario-runner.md) stands in for the user and the Rakazo operator. The workflow is fixed, with one follow-up research round and one revision loop. All shared state lives in one case file per request: client documents, the source register, evidence packets (credited to the analyst that saved each), memo versions, reviews and deliveries.

**Runtime:** each agent is a [Rakazo](https://github.com/elie222/rakazo) bot (a pinned build) running on DeepSeek. One MCP server provides the research, case-file and memo tools; each bot reaches it at its own endpoint, so the server knows which agent made every call. Phase 1 has no safety-enforcing framework: the policies in [policy.md](policy.md) are prompt instructions, and the tool lists are role design.

**More:** [agents/](agents/) (each LLM agent's tools and exact prompt, and the Scenario Runner's logic), [tools.md](tools.md), [episodes/](episodes/), [requirements.md](requirements.md), [src/README.md](src/README.md) (setup and running).
