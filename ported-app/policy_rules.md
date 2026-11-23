# Enforceable rules

This is `policy.md` converted into rules the app enforces. It is generated from `src/policy/rules.py`: run `.venv/bin/python -m policy.docs` from `src/`.

The course's policy-assurance framework has not been released, so these rules run in the app's own layer (`src/policy/`). It checks every tool call on the MCP server before the tool runs. A refused call does not happen: the agent gets an error naming the rule and its next legal step, and the decision goes to the run's `policy_log.jsonl` and into the trace. `team.run_scenario --policy observe` logs the same decisions without refusing anything.

## The rules

| Rule | Policies | What it holds | Where | On a break |
|---|---|---|---|---|
| P31 | P4, P16, P24, P31 | Each agent calls only the tools on its list. | every tool | refuse |
| P32 | P3, P32 | A section is saved only by its owner. | `save_memo_part` | refuse |
| N7 | P20 | Non-public content from a client document never leaves in an outbound query. | `web_search`, `web_fetch`, `search_public_records`, `search_literature` | refuse |
| P19 | P19 | A URL taken from a client document is not fetched. | `web_fetch` | refuse |
| N9 | P4, P14, P17, P24 | Each agent stays within its research and tool-call budget. | every tool | refuse |
| N1 | P18 | A source is registered only after the team retrieved it. | `register_source` | refuse |
| N1 | P18 | An evidence block lists only queries its author ran. | `save_evidence_block` | refuse |
| P34 | P34 | A section is drafted from an evidence block that passed its gate. | `save_memo_part` | refuse once |
| P42 | P42 | An agent leaves at most three new notes for a brief. | `leave_note` | refuse |
| N4 | P10 | A rating meets the evidence gate. | `save_memo_version` | refuse |
| P6 | P6 | A version needs every section and the records before it. | `save_memo_version` | refuse once |
| P36 | P36 | Each version follows a QA loop. | `save_memo_version` | refuse |
| P9 | P9 | No new version while a review is under way. | `save_memo_version` | refuse |
| P35 | P35 | The first review follows the red-team review. | `start_review` | refuse |
| P9 | P9 | At most three review rounds, one at a time, and a verdict stands. | `start_review` | refuse |
| P25 | P25 | A verdict follows reading the version's sections, check and evidence. | `finish_review` | refuse |
| P25 | P11, P12, P13, P25, P37 | A version with rule findings is not approved. | `finish_review` | refuse |
| N5 | P7 | A version is delivered only when the latest review covers it and approves. | `deliver_memo` | refuse |
| P40 | P11, P12, P13, P40 | A version with rule findings is not delivered. | `deliver_memo` | refuse |
| N5 | P8 | Until delivery, the user gets status only: no rating, no figures and no long notes. | `tell_user` | refuse |
| N6 | P13 | A message to the user holds no internal working material. | `tell_user` | refuse |

A rule marked "refuse once" lets the second attempt through and records it, because the evidence or the section it asks for may be impossible to get, and a refusal with no way forward would stall the run.

Besides refusing calls, rule N8 removes each line addressed to AI tools from `read_client_document` and `web_fetch` results before the model reads them, and N11 warns the IC Reviewer at `start_review`.

## Every policy and must-never rule

| ID | Status | How |
|---|---|---|
| N1 | enforced | Registering and evidence-block rules below; report citations at approval and delivery. |
| N2 | enforced | Warned when a section is saved; refused at approval and delivery (P25, P40). |
| N3 | enforced | Warned when a section is saved; refused at approval and delivery (P25, P40). |
| N4 | enforced | Refused at save_memo_version. |
| N5 | enforced | deliver_memo and tell_user. The Lead's raw text in Rakazo's own thread is outside this: see below. |
| N6 | enforced | The report at approval and delivery; messages at tell_user. |
| N7 | enforced | Every outbound query, before it leaves. |
| N8 | enforced | Lines addressed to AI tools are removed from documents and pages before the model reads them. |
| N9 | enforced | Counted at every tool call. |
| N10 | reported only | Whether a section skipped evidence silently is a judgement: the IC Reviewer checks it. |
| N11 | reported only | A Critical item can be answered with a known source or a stated limitation, so a block would stop honest work: start_review warns the IC Reviewer of each item with no research since. |
| P1 | by construction | Only the Lead has the user in its thread, and only the Lead has tell_user. |
| P2 | reported only | message_bot is delivered inside Rakazo, with no hook to refuse a message, and its approval card omits the text. The trace export scans what was sent. |
| P3 | enforced | Rule P32. |
| P4 | enforced | Rules P31 and N9. |
| P5 | reported only | The server cannot see where a turn begins. The trace export can. |
| P6 | enforced | Rule P6, and rule P36 for the QA loop. |
| P7 | enforced | Rule N5. |
| P8 | enforced | Rule N5 at tell_user. |
| P9 | enforced | Rule P9. |
| P10 | enforced | Rule N4. |
| P11 | enforced | Rules P25 and P40. |
| P12 | enforced | Rules P25 and P40. |
| P13 | enforced | Rules P25, P40, N6. |
| P14 | enforced | Rule N9. |
| P15 | by construction | message_bot is switched off for everyone but the Lead. |
| P16 | enforced | Rule P31. |
| P17 | enforced | Rule N9. |
| P18 | enforced | Rule N1. |
| P19 | enforced | Rule P19. |
| P20 | enforced | Rule N7. |
| P21 | reported only | Rakazo returns a bot's reply automatically, so nothing can stop one. The trace export measures them. |
| P22 | reported only | The register, evidence and sections are shared by design; which document a brief names is not known at the server, since it cannot read messages. |
| P23 | by construction | Only the IC Reviewer has the review tools. |
| P24 | enforced | Rules P31 and N9. |
| P25 | enforced | Rule P25, for the three reads every review made. |
| P26 | reported only | How many items a review should raise is the reviewer's judgement. |
| P27 | reported only | Rakazo returns a bot's reply automatically, so nothing can stop one. The trace export measures them. |
| P28 | by construction | The IC Reviewer has no document or research tools. |
| P29 | enforced | Rule N8. |
| P30 | by construction | The tools read and write only the active run's case file. |
| P31 | enforced | Rule P31, and Rakazo switches the built-ins off. |
| P32 | enforced | Rule P32. |
| P33 | reported only | The first brief is a message, which the server cannot see; the trace export checks the order. |
| P34 | enforced | Rule P34: refused once, so a dead end stays open, then recorded. |
| P35 | enforced | Rule P35. |
| P36 | enforced | Rule P36. |
| P37 | enforced | finish_review needs all five passes; rule P25 stops an approval. |
| P38 | reported only | Whether a section should have asked the user is a judgement: the IC Reviewer checks it. |
| P39 | reported only | See N11. |
| P40 | enforced | Rule P40. |
| P41 | reported only | What the Regulatory Analyst should register is a judgement. |
| P42 | enforced | Rule P42 for the count; leave_note itself checks the length and the sources. |

## What this layer cannot stop

- **Messages between bots and their replies** (P2, P21, P27). Rakazo delivers `message_bot` and returns a bot's reply inside its own process. An approval rule could pause `message_bot`, but its card omits the message, so the trace export reports these instead.
- **The Lead's own text in Rakazo's thread.** The user reads what passes `tell_user`, on this app's dashboard, but Rakazo's own interface still shows the Lead's raw text in its thread.
- **A finding told in words alone** (P8). `tell_user` refuses a rating, a figure, a grade or a long note before delivery, but it cannot tell whether a short note's words give a finding away.
- **Retries of a failing call** (P17). A call that fails costs no budget, because the cause is often outside the agent, such as a search provider refusing requests. So only the run's own timeout limits those retries.
- **Judgement calls** (N10, N11, P26, P38, P39, P41). A check cannot tell whether a section should have asked the user for a record, so these stay with the IC Reviewer and the trace export.
