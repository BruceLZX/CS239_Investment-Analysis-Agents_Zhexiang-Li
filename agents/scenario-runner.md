# Scenario Runner

**Type:** scripted, not LLM-based. It is the Python program [`src/team/run_scenario.py`](../src/team/run_scenario.py), and it stands in for the user and the Rakazo operator so that a scenario can run unattended. The dashboard's **Start live run** button runs the same program.

**Job:** sends a scenario's request to the team as the user, decides what to do with Rakazo's approval cards, and decides when a run is over. It also relays what a person types in the dashboard's message box: a request of their own, or a follow-up question once a run has finished.

**Talks to:** the Lead Analyst only: it sends the request, and any follow-up question a person types. It never answers a bot.

**Tools:** none of the tools in [tools.md](../tools.md). It calls Rakazo's API through `src/team/rakazo_client.py` (sign-in session, bot settings, threads, run status, approval cards, usage) and reads the case file through `src/tools/case_file.py`.

**Policies:** P19 (it denies the fetches Rakazo holds for approval) and P30 (it clears every bot's thread before a scenario) in [policy.md](../policy.md).

## Implementation and decision logic

Every step below is fixed in code. The runner never reads or judges what the bots write.

1. **Load the scenario** from `src/scenarios/<name>.yaml`: the request, the attached client documents and their confidentiality labels. A request typed in the dashboard (`--request`) becomes a scenario named `custom` with no documents.
2. **Configure the team.** Archive the bots that `src/team/profiles.py` lists as retired (the Research Analyst of the earlier three-bot team), then create or update the nine bots from the same file:
   - instructions, model and thinking level;
   - each bot's own entry for the MCP server, whose `?agent=` key tells the server who is calling, and its tool allowlist;
   - the Rakazo built-in tools it switches off.

   Then wait until no bot has a run in progress.
3. **Clear every bot's thread,** because Rakazo replays earlier messages into each run; every scenario starts clean.
4. **Start the case:** a new `runs/<run_id>/case.json` holding the scenario's client documents, marked active so the MCP server's tools read and write it.
5. **Send the request** to the Lead Analyst, as the user.
6. **Every second**, read each bot's runs in progress and decide:
   - **A bot has a new request or turn:** write the counts to `runs/<run_id>/policy_windows.json`, so that the MCP server opens a new budget window. A brief sent again before an analyst's first reply, as when a model error cuts its run off, is marked as still a first brief (P17). The check runs this often because a brief's first tool call comes about two seconds after it arrives.
   - **A run waits on an approval card,** for example a `web_fetch` of a URL that the bot's own search did not return. With `--approval-cards deny` (the default) the runner denies the card and logs it to `runs/<run_id>/approval_cards.jsonl`. With `--approval-cards wait` it leaves the card for a person to answer in Rakazo and prints a notice once.
   - **Delivered:** the case file records a delivery and no bot has worked for 15 seconds.
   - **Failed review:** the third and final review did not approve, so nothing may be delivered (P9), and no bot has worked for 15 seconds.
   - **The Lead Analyst's turn failed on a model error,** and no bot has worked for 15 seconds: send it one line asking it to check the case status and carry on, at most three times in a run. A failed analyst's reply wakes the Lead on its own, but a failed turn of the Lead leaves nobody to wake it.
   - **Stalled:** no bot has worked for `--quiet` seconds (default 240) and nothing was delivered.
   - **Timed out:** `--timeout` seconds (default 9000) have passed.
7. **Capture the run:**
   - copy Rakazo's per-run transcripts, every bot's messages and the usage records into `runs/<run_id>/rakazo/`;
   - write `outcome.json` (delivered, failed review, stalled or timed out) last, which marks the capture complete for the trace exporter and the dashboard.
8. **A follow-up question** (`--follow-up`) goes to the Lead Analyst in the latest run, and only once that run has finished:
   - remove the run's `outcome.json`, so the dashboard follows the run live again;
   - send the question, and wait until no bot has worked for 15 seconds;
   - capture the run again and write `outcome.json` back, with the original outcome and a count of follow-ups. If the question could not be sent, the old `outcome.json` goes back unchanged.
