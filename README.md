# Agent team: multi-agent investment research on Rakazo

This folder turns the investment-analysis skill into a three-bot team running on [Rakazo](https://github.com/elie222/rakazo). It was built for the CS 239 final project. Given a company (a listed ticker, or a private company's pitch deck), the team produces an evidence-backed investment memo, and every run is exported as a trace of each bot's thoughts, actions, messages and observations.

| Bot | Job |
|---|---|
| **Lead Analyst** | Talks to the user, briefs the analyst, writes and revises the memo, delivers only an approved version. |
| **Research Analyst** | SEC filings, price data and web research; registers every source and saves an evidence packet. |
| **IC Reviewer** | Reviews each memo version like a skeptical investment committee partner; approves it or returns must-fix items. |

What the app must never do (rules N1–N9, each taken from the skill's own evidence and QA standards) is in [`requirements.md`](requirements.md).

## Layout

```
requirements.md      Phase 1 requirements and the must-never rules
infra/               setup-rakazo.sh: installs a pinned Rakazo build with Docker
tools/               the MCP server: SEC EDGAR, prices, source register, case file, memo checks
team/                bot prompts and profiles, Rakazo client, scenario runner, trace export and checker
scenarios/           the four research scenarios
fixtures/            fictional client documents the scenarios attach
tests/               offline tests (recorded SEC and Yahoo responses; no tokens spent)
traces/              exported traces (JSON and Markdown) and what each scenario showed
```

## Running it

You need macOS or Linux, Docker Desktop (or Docker Engine with Compose), Python 3.13 and a DeepSeek API key. Run the commands from this folder.

```bash
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env
bash infra/setup-rakazo.sh start
```

Rakazo then runs at http://127.0.0.1:5174. Its generated secrets live in `../rakazo-runtime/`, outside the repository.

```bash
.venv/bin/python -m team.login --local-test
.venv/bin/python -m team.connect_model
```

- **`team.login --local-test`** creates a test account that exists only in the local Rakazo, and keeps its generated password in `.env`. To use your own account instead, run `team.login` without the flag.
- **`team.connect_model`** asks for your DeepSeek key (input hidden) and sends it straight to Rakazo, which stores it encrypted. It also asks for the contact SEC requires on automated requests (`Your Name you@example.com`).

Start the MCP server and leave it running in its own terminal:

```bash
.venv/bin/python -m tools.server
```

Then run a scenario, export its trace and check it:

```bash
.venv/bin/python -m team.run_scenario public-equity-memo
.venv/bin/python -m team.export_trace
.venv/bin/python -m team.check_trace traces/phase1/public-equity-memo.json
```

- **`run_scenario`** creates or updates the bots, clears their threads, sends the scenario's request, waits for the memo, and copies Rakazo's transcripts into `runs/<run_id>/`.
- **`export_trace`** turns the latest run into `traces/phase1/<scenario>.json` and `.md`.
- **`check_trace`** confirms the trace holds everything the course spec asks for.

Stop Rakazo with `bash infra/setup-rakazo.sh stop`; its data is kept.

## Tests

```bash
.venv/bin/python -m pytest
```

The tests run offline on recorded SEC and Yahoo responses and on a captured run in Rakazo's transcript format, so they spend no tokens.

## Phase 1 and Phase 2

Phase 1 runs **without** a safety-enforcing framework: the rules exist only as instructions in the bots' prompts. The memo check and the review-gate record observe and log, but never block. Exported traces list possible rule breaks under "Rule observations". In Phase 2 the same scenarios are replayed with the course's policy-assurance framework enforcing the rules; `requirements.md` names where each rule can be checked.

## Cost and data

- **Cost:** each scenario run costs roughly $1–2 in DeepSeek tokens; the exact figure is in its trace.
- **Data:** every company, person and figure in `fixtures/` is fictional; Apple and Tesla are real listed companies, researched from public data.
- **Privacy:** traces redact real email addresses, and they leave out Rakazo user ids and system prompts.
