# Investment Analysis Agents

CS 239 (UCLA, Fall 2026) final project by Zhexiang Li. Nine AI agents on [Rakazo](https://github.com/elie222/rakazo) turn a company into a decision-grade investment report, the way a research desk would:
- a **Lead Analyst** owns the request and the research plan, writes the thesis, the scoring and the executive summary, and delivers the approved report;
- six analysts research in parallel and write the sections they researched: the **Company**, **Product**, **Market**, **Fundamentals**, **Valuation** and **Regulatory Analysts**;
- a **Red Team Analyst** attacks the thesis before review and writes the risk section;
- an **IC Reviewer** reviews every version in five passes before anything ships, and sends each Critical or Important item to the section's owner.

Its policies come from the evidence and QA standards the report is held to: the playbooks in [`src/team/playbooks/`](src/team/playbooks/) and the checks in [`src/tools/qa/`](src/tools/qa/).

**Phase 1** (submitted as the tag `phase1`) ran with a four-agent team and without a safety-enforcing framework: the policies were prompt instructions, and the traces show where the agents kept them and where they broke them.

**Phase 2** (this branch) ports the nine-bot app to the course's framework, PolicyWeave: its translator turned [`policy.md`](policy.md) into Datalog rules enforced at the app's tool calls ([`ported-app/`](ported-app/)), and ten scenarios ran ten times each on the original and the ported app. [Phase 2 with PolicyWeave](#phase-2-with-policyweave) below has the details and [`report.md`](report.md) the results. Before the framework was released, the app gained its own rule layer ([`src/policy/`](src/policy/)); in the Phase 2 runs it only records what it would refuse, so every difference between the two apps comes from PolicyWeave.

## Where everything is

| Deliverable | Where |
|---|---|
| What the app does and the tasks it supports | [`app.md`](app.md) |
| **Phase 2:** the report (translation and enforcement summaries, match counts, the three questions) | [`report.md`](report.md) |
| **Phase 2:** the ported app, its back-translation and the review judgments | [`ported-app/`](ported-app/), [`ported-app/back-translation/`](ported-app/back-translation/), [`ported-app/review.json`](ported-app/review.json) |
| **Phase 2:** the ten scenarios, the harness and its PolicyWeave translation, the saved cases the scenarios start from | [`test_cases.json`](test_cases.json), [`run.py`](run.py), [`translated_harness.py`](translated_harness.py), [`test_inputs/`](test_inputs/) |
| **Phase 2:** every run's result, and the ported app's trajectories | [`runs/`](runs/) |
| **Phase 2:** running PolicyWeave on an arm64 Mac | [`phase2-env/`](phase2-env/README.md) |
| Policies, P1–P42, by agent: permission, capability, lifecycle, information flow and isolation | [`policy.md`](policy.md) (the guidelines' name; [`policies.md`](policies.md) is the same file under the course page's name) |
| The policies as enforced rules, and what happens to each policy | [`policy_rules.md`](policy_rules.md) |
| Each tool's inputs and outputs | [`tools.md`](tools.md) |
| Each agent: the nine LLM agents' tools and exact system prompts, and the scripted Scenario Runner's logic | [`agents/`](agents/) |
| Example episodes from Phase 1, one per scenario, with the policies involved | [`episodes/`](episodes/) |
| Requirements: what the app does and must never do (N1–N11), and how they map to policies | [`requirements.md`](requirements.md) |
| Source code, with setup and run instructions | [`src/`](src/) and [`src/README.md`](src/README.md) |
| Test cases | [`tests/`](tests/) and [`tests/README.md`](tests/README.md) |
| Phase 2 traces, one compliant run and two with violations intercepted, and which policies each triggered | [`traces/phase2/`](traces/phase2/) and [`traces/README.md`](traces/README.md) |
| The same scenarios before enforcement | [`traces/phase2-baseline/`](traces/phase2-baseline/README.md) |
| Phase 1 traces, and which policies each scenario triggered | [`traces/phase1/`](traces/phase1/) and [`traces/README.md`](traces/README.md) |
| Five-minute demo video (Phase 1) | [youtu.be/5v6sdI-pl0E](https://youtu.be/5v6sdI-pl0E) |

## Phase 2 with PolicyWeave

**The original app** is this repository at `4717518`: the nine-bot app of the `phase2` branch, with `policy.md` condensed for translation.
- **The condensed policy:** each of P1–P42 keeps its number and its enforceable core, about 45 sentences in place of 153. PolicyWeave's binding plan of the full text did not come back valid, and the full text is at `9ecf2bd`.
- **The translation checkout:** a clean clone of that commit, with two local commits that leave out what is not the agents' runtime:
  - `traces/` (108 MB of recorded runs);
  - the seed case `src/fixtures/seeds/` (1 MB of test data);
  - the dashboard, the trace export and check tools, the model-connection and cost scripts, and their tests.

  The harness's original side runs this repository itself, whose runtime code is the same.

**Environment.**
- **Machine:** macOS 27 on Apple silicon, with Docker Desktop 29.
- **PolicyWeave:** `thaddywu/CS239-Phase2` at `cbeaf6f` (framework `d3ba0dcb`). It ran through an arm64 Linux host container, set up as [`phase2-env/`](phase2-env/README.md) describes, with two planning limits raised (`phase2-env/planning-bound.patch`).
- **Translator model:** OpenAI `gpt-6.1-sol` with medium reasoning, for the translation, the harness translation and Inspector QA.
- **The app's agents:** DeepSeek through Rakazo, as in Phase 1 (`deepseek-flash`, thinking max, the IC Reviewer capped at high).
- **Harness Python:** a Python 3.13 venv with `src/requirements.txt` and PolicyWeave installed without its `mcp` extra; the app uses mcp 2.1.1 and PolicyWeave's extra pins 1.30.0.
- **Soufflé:** 2.5 from Homebrew, with [`phase2-env/prlimit`](phase2-env/prlimit) on `PATH`.
- **Certificates:** `SSL_CERT_FILE` points at certifi's bundle for OpenAI calls, because python.org's macOS build has no certificate store of its own.

**Running the harness.** It needs:
- Rakazo running, with the DeepSeek key entered once in its UI;
- a Rakazo session;
- `src/.env`;
- a network that reaches `api.deepseek.com`. The UCLA Health network intercepts it, and every agent run there fails with a connection error.

```bash
src/infra/setup-rakazo.sh start
(cd src && .venv/bin/python -m team.login --local-test)
python run.py --case S01 --output_dir runs --sample 1
python translated_harness.py --side original --output_dir runs --sample 10
python translated_harness.py --side ported --output_dir runs --sample 10
python phase2-env/trajectories.py unpack runs
policyweave inspect --traj runs/S01/ported/sample-1/trajectory.jsonl --connection ~/.config/policyweave/connection.yaml
```

`run.py` is the harness as written for the original app; `translated_harness.py` is PolicyWeave's translation of it, which adds `--side`. The committed runs were made one scenario at a time (`--case S01 --sample 10`, and so on), ten original samples and then ten ported ones for each scenario, so that both apps met the same network and model conditions.

**One scenario was resumed.** The runs started at 19:48 PT on 2026-11-22 and ran unattended. The Mac slept with its lid closed from 23:31 to 04:02, during S08's ported samples 3 and 4; `caffeinate` cannot stop a lid-close sleep on battery.
- Every other sample ran while the Mac was awake.
- Those two samples were set aside unused, and S08's ported samples 3 to 10 were run again with [`phase2-env/resume_samples.py`](phase2-env/resume_samples.py).
- That script calls the runner's own `run_case` for each sample, as `--sample 10` does, but it starts at sample 3.

Each sample takes three steps:
1. It starts the app's MCP server inside the harness process.
2. It configures the nine Rakazo bots and opens a case from a saved seed in [`test_inputs/seeds/`](test_inputs/seeds/), with the app's own rule layer set to observe.
3. It sends the scenario's request and waits for the scenario's deciding event, then stops the bots.

Four scenarios, S02 to S05, replace the Lead Analyst's instructions with an attacker's, as declared in `test_cases.json`. The Lead's own prompt refuses those requests, so without the replacement the rules would never see the violation. Results go to `runs/<case>/<side>/sample-<n>/result.json`. The app's per-run files stay in each sample's `artifacts/` and are not committed.

**Trajectories.** Each ported sample's `trajectory.json` and `trajectory.jsonl` are committed packed with xz, as `trajectory.json.xz` and `trajectory.jsonl.xz`, beside its `gate-*.json`.
- **Why packed:** the ported app records the whole case file before and after every tool call. The unpacked files take 0.1 to 218 MB each and 4.4 GB in all, past GitHub's 100 MB limit per file. Packed, each is at most 0.3 MB, 25 MB in all.
- **Before opening one in PolicyWeave-Inspector**, unpack them (standard library only; `xz -dk` does the same):

```bash
python phase2-env/trajectories.py unpack runs
```

- **What Inspector cannot open:** 7 of the 100 trajectories are over its 64 MiB limit:
  - `runs/S02/ported/sample-9` (171.0 MiB);
  - S08's ported samples 1, 5, 6, 8, 9 and 10 (64.8 to 78.3 MiB).

  Their `gate-1.json` files hold the same decisions with their facts. No event in any trajectory is over Inspector's 1 MB limit per event.

**The client document** of S06 and S07, the Vantelle deck, is read by both apps from [`test_inputs/documents/`](test_inputs/documents/), a copy of the app's `src/fixtures/vantelle_deck.pdf`. PolicyWeave's generated `ported-app/` left out 25 of the original's files, among them both decks, 17 of the offline tests' 50 recorded responses in `tests/fixtures/` (the SEC pages and arXiv feeds), `policy.md` and `src/infra/setup-rakazo.sh`.

**The saved cases** in [`test_inputs/seeds/`](test_inputs/seeds/):
- **Where they come from:** `apple_before_v1` is the app's own fixture (`src/fixtures/seeds/`). The other three are cut from the compliant Phase 2 trace [`public-equity-memo`](traces/phase2/public-equity-memo.md), run `20261031-161226-ef6c`, at the moment each scenario needs. `apple_v3_unreviewed` adds a version 3 that copies version 2 and was never reviewed.
- **Replayed records:** in `apple_v1_in_review`, the research plan, the profile requirements, the scenario analysis and the red-team review are the saves in place when R1 started. The run saved each again later, and its case file keeps only the latest save, so the earlier ones were replayed from the run's tool log through the app's own tools.
- **Omitted text:** each seed keeps the text of every section's latest revision and of every revision a saved version uses. Older revisions keep their record (author, hash, length, check) but not their text, which no tool reads. Without that, a case file is 0.9 to 1.3 MB, while PolicyWeave-Inspector refuses any trajectory event over 1 MB, and the ported app writes the whole case file as one event.

**Manual inputs:**
- the DeepSeek key, in Rakazo's UI;
- the OpenAI key, in `~/.config/policyweave/connection.yaml`;
- a network that reaches DeepSeek;
- the review judgments, saved as `ported-app/review.json` in the format of PolicyWeave's review panel.

## Quick start

Everything runs from `src/`; [`src/README.md`](src/README.md) has the full instructions.

A live run needs:
- Docker;
- Python 3.13;
- a DeepSeek API key, entered once into the local Rakazo.

The tests and the dashboard's replay of a recorded run work offline.

```bash
cd src
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest ../tests
```

## License

[MIT](LICENSE).
