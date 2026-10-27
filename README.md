# Investment Analysis Agents

CS 239 (UCLA, Fall 2026) final project by Zhexiang Li. Three AI agents on [Rakazo](https://github.com/elie222/rakazo) turn a company into an evidence-backed investment memo, the way a small research desk would:
- a **Lead Analyst** owns the request and the memo;
- a **Research Analyst** gathers evidence from SEC filings, prices and the web;
- an **IC Reviewer** challenges every draft before anything ships.

The app is a multi-agent version of the [investment-analysis skill](https://github.com/BruceLZX/investment-analysis-skill), and its policies come from that skill's evidence and QA standards.

**Phase 1** (this version) runs without a safety-enforcing framework: the policies are prompt instructions, and the traces show where the agents kept them and where they broke them. In **Phase 2** the same scenarios run with the course's policy-assurance framework enforcing the policies.

## Where everything is

| Deliverable | Where |
|---|---|
| What the app does and the tasks it supports | [`app.md`](app.md) |
| Policies, P1–P29, by agent: permission, capability, lifecycle, information flow and isolation | [`policy.md`](policy.md) (the guidelines' name; [`policies.md`](policies.md) is the same file under the course page's name) |
| Each tool's inputs and outputs | [`tools.md`](tools.md) |
| Each agent: the three LLM agents' tools and exact system prompts, and the scripted Scenario Runner's logic | [`agents/`](agents/) |
| Example episodes, one per scenario, with the policies involved | [`episodes/`](episodes/) |
| Requirements: what the app does and must never do (N1–N9), and how they map to policies | [`requirements.md`](requirements.md) |
| Phase 1 source code, with setup and run instructions | [`src/`](src/) and [`src/README.md`](src/README.md) |
| Test cases | [`tests/`](tests/) and [`tests/README.md`](tests/README.md) |
| Phase 1 traces, and which policies each scenario triggered | [`traces/phase1/`](traces/phase1/) and [`traces/README.md`](traces/README.md) |
| Phase 2 source and traces | to come (Phase 2 starts 2026-11-12) |
| Demo script for the class presentation | [`DEMO.md`](DEMO.md) |
| Five-minute demo video | YouTube link to be added |

The course's submission archives are built from this repository; see [Submission archives](#submission-archives).

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

## Submission archives

`make_submission.sh` builds the two archives the course's submission guidelines ask for, from the last commit, into `dist/` (gitignored):
- `{name}-{appName}-{uid}-requirements.tar.gz`: `app.md`, `policy.md`, `tools.md`, `agents/` and `episodes/`, under `{appName}/`;
- `{name}-{appName}-{uid}-whole.tar.gz`: the whole repository.

```bash
bash make_submission.sh <your UID>
```

The name and app name default to `ZhexiangLi` and `Investment-Analysis-Agents`; pass them as the second and third arguments to change them.

## License

[MIT](LICENSE).
