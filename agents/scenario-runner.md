# Scenario Runner

**Type:** scripted, not LLM-based. It is the Python program [`src/team/run_scenario.py`](../src/team/run_scenario.py), and it stands in for the user and the Rakazo operator so that a scenario can run unattended. The dashboard's **Start live run** button runs the same program.

**Job:** sends a scenario's request to the team as the user, decides what to do with Rakazo's approval cards, and decides when a run is over.

**Talks to:** the Lead Analyst only, once: it sends the scenario's request. It never answers a bot.

**Tools:** none of the tools in [tools.md](../tools.md). It calls Rakazo's API through `src/team/rakazo_client.py` (sign-in session, bot settings, threads, run status, approval cards, usage) and reads the case file through `src/tools/case_file.py`.

**Policies:** P19 (it denies the fetches Rakazo holds for approval) and P30 (it clears every bot's thread before a scenario) in [policy.md](../policy.md).

## Implementation and decision logic

Every step below is fixed in code. The runner never reads or judges what the bots write.

1. **Load the scenario** from `src/scenarios/<name>.yaml`: the request, the attached client documents and their confidentiality labels.
2. **Configure the team.** Archive the bots that `src/team/profiles.py` lists as retired (the Research Analyst of the earlier three-bot team), then create or update the four bots from the same file:
   - instructions, model and thinking level;
   - each bot's own entry for the MCP server, whose `?agent=` key tells the server who is calling, and its tool allowlist;
   - the Rakazo built-in tools it switches off.

   Then wait until no bot has a run in progress.
3. **Clear every bot's thread,** because Rakazo replays earlier messages into each run; every scenario starts clean.
4. **Start the case:** a new `runs/<run_id>/case.json` holding the scenario's client documents, marked active so the MCP server's tools read and write it.
5. **Send the request** to the Lead Analyst, as the user.
6. **Every 5 seconds**, read each bot's runs in progress and decide:
   - **A run waits on an approval card,** for example a `web_fetch` of a URL that the bot's own search did not return. With `--approval-cards deny` (the default) the runner denies the card and logs it to `runs/<run_id>/approval_cards.jsonl`. With `--approval-cards wait` it leaves the card for a person to answer in Rakazo and prints a notice once.
   - **Delivered:** the case file records a delivery and no bot has worked for 15 seconds.
   - **Failed review:** the re-review did not approve, so nothing may be delivered (P9), and no bot has worked for 15 seconds.
   - **Stalled:** no bot has worked for `--quiet` seconds (default 150) and nothing was delivered.
   - **Timed out:** `--timeout` seconds (default 1800) have passed.
7. **Capture the run:**
   - copy Rakazo's per-run transcripts, every bot's messages and the usage records into `runs/<run_id>/rakazo/`;
   - write `outcome.json` (delivered, failed review, stalled or timed out) last, which marks the capture complete for the trace exporter and the dashboard.
