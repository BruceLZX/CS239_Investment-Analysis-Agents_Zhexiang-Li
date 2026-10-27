# Tests

69 offline tests. They spend no tokens and need neither Rakazo nor a network:
- **SEC and Yahoo:** recorded responses in `fixtures/` stand in for the live services.
- **The trace exporter, replay and dashboard:** a captured run in Rakazo's transcript format, built in `test_export_trace.py`.

Run them from `src/`:

```bash
.venv/bin/python -m pytest ../tests
```

| File | What it checks |
|---|---|
| `test_sec_edgar.py` | SEC EDGAR parsing: the CIK is padded and unknown tickers are rejected; annual figures come from 10-K values under the current revenue concept, capped at the requested years; filings are filtered by form; requests need a contact User-Agent. |
| `test_prices.py` | The price summary states exchange, currency and timestamp; skips missing closes; rejects unknown periods; reports API errors. |
| `test_case_file.py` | Starting a run creates the case file and marks it active; reads without an active run explain how to start one; registering a location again reuses its source ID; the status summary leaves out bulky content. The review gate needs an approving review of that exact version (P7), and tool calls are logged only during a run. |
| `test_memo.py` | The memo check, rule by rule: unregistered source IDs (N1); numbers without sources, ignoring dates, years, list numbers, filing names and URLs (N2); unlabelled company claims (N3); the rating evidence gate for listed and private companies (N4); internal working material and production wording (N6); the disclaimer and data-as-of date. Also, the citation pattern is the skill's. |
| `test_server.py` | The MCP server: every tool is listed with text-only results; calls are logged to the active run; error messages reach the model; ratings and verdicts are validated; client documents carry their confidentiality label; `deliver_memo` records the review gate and the memo check but never blocks (Phase 1). A memo that fits one tool result comes back whole, a longer one is refused, and other long results are cut where Rakazo would cut them. |
| `test_scenarios.py` | Each scenario file is complete and its documents exist; every must-never rule N1–N9 is exercised by some scenario. |
| `test_rakazo_client.py` | Signing in again replaces the saved Rakazo session. |
| `test_run_scenario.py` | `--narrate` prints each delivery once, in time order. |
| `test_replay.py` | `team.replay` prints a captured conversation and what was delivered. |
| `test_export_trace.py` | A captured run becomes a complete trace. Rule observations catch planted breaks of N1, N5, N7 and N9. Runs resumed after an approval card are merged, and approval cards appear as platform-guard events. Replayed history and duplicate replies are dropped, and private details stay out. Usage is summed per agent, the Markdown reads as a timeline, and `check_trace` names what is missing. |
| `test_dashboard.py` | The dashboard: a captured run shows each delivery once with its rule observations; a run counts as finished only once its outcome is written; each tool call is credited to the bot that could make it. A live run reads conversation, status and cost from Rakazo and says when Rakazo can't be read. Only this machine can reach the server, and a run starts once, only from a JSON request. |
| `test_deliverables.py` | The submission files match the code: each file in `../agents/` holds its bot's exact instructions; `../tools.md` lists every tool a bot can call, once, and each one is implemented; `../policy.md` is consecutively numbered paragraphs; every policy ID mentioned in the other documents exists. |
