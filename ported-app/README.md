# Investment Analysis Agents

CS 239 (UCLA, Fall 2026) final project by Zhexiang Li. Nine AI agents on [Rakazo](https://github.com/elie222/rakazo) turn a company into a decision-grade investment report, the way a research desk would:
- a **Lead Analyst** owns the request and the research plan, writes the thesis, the scoring and the executive summary, and delivers the approved report;
- six analysts research in parallel and write the sections they researched: the **Company**, **Product**, **Market**, **Fundamentals**, **Valuation** and **Regulatory Analysts**;
- a **Red Team Analyst** attacks the thesis before review and writes the risk section;
- an **IC Reviewer** reviews every version in five passes before anything ships, and sends each Critical or Important item to the section's owner.

Its policies come from the evidence and QA standards the report is held to: the playbooks in [`src/team/playbooks/`](src/team/playbooks/) and the checks in [`src/tools/qa/`](src/tools/qa/).

**Phase 1** (submitted as the tag `phase1`) ran with a four-agent team and without a safety-enforcing framework: the policies were prompt instructions, and the traces show where the agents kept them and where they broke them. **This version** is the safe port. The team and the report are complete: an executive summary and fourteen sections, each researched and saved as evidence before it is drafted, challenged by the red team, reviewed in up to three rounds and rendered to HTML and PDF. The policies are now rules: every tool call passes a rule table before it runs, and a call that breaks one is refused. The course's policy-assurance framework has not been released, so this is the app's own enforcement layer ([`src/policy/`](src/policy/)), written so that its rule table can move to the framework.

## Where everything is

| Deliverable | Where |
|---|---|
| What the app does and the tasks it supports | [`app.md`](app.md) |
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
