# Investment Analysis Agents: source code

This folder holds the application: nine Rakazo bots that turn a company into a decision-grade investment report, and the MCP server their tools run on.
- **The bots:** a Lead Analyst; six analysts (Company, Product, Market, Fundamentals, Valuation, Regulatory); a Red Team Analyst; and an IC Reviewer.
- **What the app does:** [`../app.md`](../app.md).
- **The agents and their exact prompts:** [`../agents/`](../agents/).
- **The tools:** [`../tools.md`](../tools.md).
- **The policies:** [`../policy.md`](../policy.md).

Run every command below from this folder (`src/`).

## Layout

```
team/          bot prompts and profiles, Rakazo client, scenario runner, trace export and checks, the agents' exchanges, replay
team/playbooks the research playbooks; the bots read them with read_playbook
policy/        the rule table (rules.py), and the engine that applies it to every tool call
tools/         the MCP server: web search and fetch, SEC statements, filing text, prices, valuation, source register, case file, workflow records,
               report sections, versions, reviews and delivery
tools/qa/      the QA checks: depth, report completeness, citations, evidence, register, workflow, output
tools/templates the HTML report template; tools/report.py renders it and tools/pdf.py prints it
dashboard/     a local web page that shows a run live or replays a captured one
infra/         setup-rakazo.sh: installs and runs a pinned Rakazo build with Docker
scenarios/     the five research scenarios (request, attached documents, what to watch for)
fixtures/      fictional client documents the scenarios attach, and the saved case compromised-lead starts from
runs/          created at run time and gitignored: per-run case files, tool logs, Rakazo transcripts
../tests/      offline tests (see ../tests/README.md)
../traces/     exported traces and what each scenario showed
```

## External requirements

- **Machine:** macOS or Linux, Docker Desktop (or Docker Engine with Compose), Python 3.13, Pango for the PDF (`brew install pango`, or `apt-get install libpango-1.0-0 libpangocairo-1.0-0`), and a network connection.
- **[Rakazo](https://github.com/elie222/rakazo):** the agent runtime, run locally in Docker. `infra/setup-rakazo.sh` downloads a pinned build (commit `b445fe9`, with a checksum check) and raises Rakazo's bot-to-bot hop limit to 31, which the red-team pass, three review rounds, two revision rounds and the Lead's follow-up sends (a section sent back before review, a cross-section correction, a resent brief) need, and retries a broken model stream up to three times. It keeps Rakazo's generated secrets in `../../rakazo-runtime/`, next to the repository rather than inside it. Rakazo serves its web UI at http://127.0.0.1:5174.
- **DeepSeek API key:** the bots run on DeepSeek (`deepseek-flash` with thinking `max`). You give the key to Rakazo once with `team.connect_model`; Rakazo stores it encrypted, and it never enters this repository. The Phase 1 runs (on `deepseek-v4-pro`) cost $0.25–0.85 each and the four-bot Phase 2 baseline $0.29–0.61; a nine-bot run of the full report is estimated at $1.5–2.5 at DeepSeek's peak rate and half that off-peak. Traces and the dashboard price each call for the hour it was made (`team/model_costs.py`), since Rakazo's own estimate always uses the peak rate.
- **SEC EDGAR:** free. SEC's fair-access policy requires a contact in the User-Agent (`SEC_USER_AGENT`).
- **Yahoo Finance's chart endpoint:** price context, used at low volume; no key needed.
- **Web search:** `web_search` on the MCP server scrapes DuckDuckGo's HTML form; no key needed.

## Environment

`.env` (gitignored) is created from `.env.example`:

| Variable | Meaning |
|---|---|
| `RAKAZO_URL` | Rakazo's web origin, `http://127.0.0.1:5174` |
| `SEC_USER_AGENT` | your contact for SEC requests, e.g. `Your Name you@example.com`; `team.connect_model` asks for it |
| `MODEL_ID`, `THINKING_LEVEL` | the bots' model and thinking level (defaults `deepseek-flash`, `max`) |
| `REVIEWER_THINKING_LEVEL` | the most thinking the IC Reviewer gets (default `high`): at `max`, its reasoning over the whole memo can use up Rakazo's 32,768-token output limit before it writes a review |
| `MCP_HOST`, `MCP_PORT` | where the MCP server listens (`127.0.0.1`, `8766`) |
| `MCP_ENDPOINT` | the address Rakazo's containers use to reach it (`http://host.docker.internal:8766/mcp`); each bot gets this address with its own `?agent=` key |
| `RAKAZO_TEST_EMAIL`, `RAKAZO_TEST_PASSWORD` | written by `team.login --local-test`; never printed |

## Install and configure

```bash
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env
bash infra/setup-rakazo.sh start
.venv/bin/python -m team.login --local-test
.venv/bin/python -m team.connect_model
```

- **`team.login --local-test`** creates a test account that exists only in the local Rakazo, and keeps its generated password in `.env`. To use your own account instead, run `team.login` without the flag.
- **`team.connect_model`** asks for your DeepSeek key (input hidden) and sends it straight to Rakazo. It also asks for the contact SEC requires.

## Running it

Start the MCP server and leave it running in its own terminal:

```bash
.venv/bin/python -m tools.server
```

Then run a scenario, export its trace and check it. For example:

```bash
.venv/bin/python -m team.run_scenario public-equity-memo
.venv/bin/python -m team.export_trace
.venv/bin/python -m team.check_trace ../traces/phase2/public-equity-memo.json
```

- **`run_scenario <name>`** runs one of `public-equity-memo`, `confidential-startup`, `manipulated-deck`, `rushed-call` or `compromised-lead`, which replaces the Lead's instructions with an attacker's and starts from a saved case. It creates or updates the nine bots (and archives the Research Analyst from the earlier three-bot team), clears their threads, sends the scenario's request to the Lead Analyst, waits for the report (expect 60–95 minutes; the runner gives up after 150), and copies Rakazo's transcripts into `runs/<run_id>/`. Each version's HTML, PDF and Markdown are in `runs/<run_id>/versions/`, and the delivered report folder in `runs/<run_id>/delivery/`. Instead of a scenario name:
  - `--request "…"` runs a request of your own, with no attached documents (scenario name `custom`);
  - `--follow-up "…"` asks the Lead Analyst a question about the latest run once it has finished; the run is captured again afterwards, so the question and answer join its record.

  Options:
  - `--policy observe` logs what the rules would refuse and refuses nothing (the default is `enforce`);
  - `--narrate` prints the conversation between the bots as it happens;
  - `--approval-cards wait` leaves Rakazo's approval cards for you to answer (the default denies them, so unattended runs don't stall).
- **`export_trace [run_id]`** turns a run (default: the latest) into `../traces/phase2/<scenario>.json` and `.md`. Use `--out` to write somewhere else (the Phase 1 traces are in `../traces/phase1/`).
- **`check_trace`** confirms that a trace holds everything the course asks for: each agent's thoughts, tool calls with arguments, tool results and inter-agent messages.

To watch a run in the browser instead, start the dashboard and open http://127.0.0.1:8770:

```bash
.venv/bin/python -m dashboard.server
```

It starts a scenario and follows the team live:
- who is working and what they're doing, and where the case is in its steps (plan, briefs, evidence and sections, red team, version, review, delivery);
- the messages between the bots, and what they did with each other's work through the case file: sections read, sources cited, notes left, review items routed (dashed arrows on the team diagram and the trace);
- the source register, the fourteen sections, versions and reviews (items by severity);
- the latest version as the rendered HTML report, with its PDF;
- at the end, rule observations and cost.

Below the conversation, a message box talks to the Lead Analyst: **New request** starts a run with what you typed, and **Ask a follow-up** asks about the latest run once it has finished. Both run `team.run_scenario` (with `--request` or `--follow-up`) and show the team working live.

It can also replay any captured run at 10–80× speed; a replay needs neither Rakazo nor a network. A replay also draws the run's trace as a timeline, one lane per agent: its thoughts, tool calls, tool results and messages in time order, each of which opens to its full text.

Stop Rakazo with `bash infra/setup-rakazo.sh stop`; its data is kept.

## Tests

```bash
.venv/bin/python -m pytest ../tests
```

The tests run offline, so they spend no tokens. They use recorded SEC and Yahoo responses and a captured run in Rakazo's transcript format. [`../tests/README.md`](../tests/README.md) describes each test file.

## Phase 1 and Phase 2

Phase 1 ran with no safety-enforcing framework: the policies existed only as instructions in the bots' prompts. Phase 2 enforces them. Every tool call passes the rule table in `policy/rules.py` before it runs, and a call that breaks a rule is refused: the agent is told the rule and its next legal step, and the decision goes to the run's `policy_log.jsonl` and into its trace. [`../policy_rules.md`](../policy_rules.md) lists every rule, and says what happens to each policy, including those the layer cannot stop. The course's own framework has not been released; `policy/engine.py`'s `before` and `after` are the only entry points, for it to take over.

Run `.venv/bin/python -m policy.docs` after changing the rule table.

## Data

- **Fiction:** every company, person and figure in `fixtures/` is fictional. Apple and Tesla are real listed companies, researched from public data.
- **Privacy:** traces redact real email addresses, and they leave out Rakazo user ids and system prompts.
