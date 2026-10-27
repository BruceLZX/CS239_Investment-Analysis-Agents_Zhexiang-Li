# Investment Analysis Agents

**Purpose.** A team of three AI agents turns a company into an evidence-backed investment memo, the way a small research desk would:
- the **Lead Analyst** owns the request and the memo;
- the **Research Analyst** gathers the evidence;
- the **IC (investment committee) Reviewer** challenges each draft before anything ships.

It is a multi-agent version of the [investment-analysis skill](https://github.com/BruceLZX/investment-analysis-skill), and its rules are that skill's own evidence and QA standards. The users are professional investors, such as a fund's research associates or a venture firm's deal team.

**Supported tasks**
- **Memo on a US-listed company.** Financials for the last three fiscal years come from SEC 10-K filings. The memo adds price context (exchange, currency, timestamp) and web research on competitors, news and counter-evidence. The rating is Buy, Add, Hold, Reduce, Sell, Watchlist or Hold-off.
- **Diligence on a private company from the documents the client attaches,** such as a confidential pitch deck. The team checks the company's claims against independent sources without exposing the deck's non-public content, marks each claim's verification status, and rates the company Invest, Wait or Pass.
- **Follow-up questions** about a delivered memo, answered from the case file.
- **Holding to the evidence and review standards under pressure,** such as a user who asks to skip the review, or a document that hides instructions aimed at AI tools.

**Not supported:** placing trades or orders, personal financial advice, handling client money or accounts, non-US filings, and real-time market data.

**How a request flows**
1. The user sends a request, with any documents, to the Lead Analyst. This is the only entry point.
2. The Lead Analyst briefs the Research Analyst.
3. The Research Analyst gathers SEC filings, prices and web sources, registers every source, saves an evidence packet and replies with a summary.
4. The Lead Analyst writes the memo, runs the memo check and asks the IC Reviewer to review that version.
5. The IC Reviewer approves the version or returns must-fix items.
6. The Lead Analyst either revises (one re-review at most) or delivers the approved version and replies to the user.

**Coordination:** centralized. Every message goes through the Lead Analyst, and the other two agents only answer its requests. In unattended runs a scripted [Scenario Runner](agents/scenario-runner.md) stands in for the user and the Rakazo operator. The workflow is fixed, with one revision loop. All shared state lives in one case file per request: client documents, the source register, evidence packets, memo versions, reviews and deliveries.

**Runtime:** each agent is a [Rakazo](https://github.com/elie222/rakazo) bot (a pinned build) running on DeepSeek. One MCP server provides the research, case-file and memo tools. Phase 1 has no safety-enforcing framework: the policies in [policy.md](policy.md) are prompt instructions, and the tool lists are role design.

**More:** [agents/](agents/) (each LLM agent's tools and exact prompt, and the Scenario Runner's logic), [tools.md](tools.md), [episodes/](episodes/), [requirements.md](requirements.md), [src/README.md](src/README.md) (setup and running).
