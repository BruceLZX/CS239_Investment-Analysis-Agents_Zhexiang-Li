# Playbooks

These are the reference files of the investment-analysis skill, copied unchanged from
[BruceLZX/investment-analysis-skill](https://github.com/BruceLZX/investment-analysis-skill) (MIT) at commit
`fb5ae3466aa6e9391cd0f7195633de08c4e54936`. They are the analysis standards the agent team works to.

The bots read them at run time with the `read_playbook` tool, one heading at a time, because together they are far
longer than Rakazo's 20,000-character limit on a bot's instructions. Each bot's prompt names the playbooks and
headings it reads before it researches or writes.

Where a playbook talks about the skill's own machinery, the team uses its counterpart:

| In the playbooks | In this app |
|---|---|
| `_work/research_plan.md`, `profile_requirements.md`, `thesis_table.md`, `scenario_analysis.md`, `red_team_review.md`, `investor_review.md` | records in the run's case file, written with `save_research_plan`, `save_profile_requirements`, `save_thesis_table`, `save_scenario_analysis`, `save_red_team_review` and the review tools |
| `_work/source_register.md` | the source register (`register_source`; data tools register what they retrieve) |
| `_work/evidence_matrix.md` | one evidence block per section (`save_evidence_block`) |
| `run_analysis_harness.py gate`, `loop`, `final-check` | `get_gate`, `get_memo_check` and the final check inside `deliver_memo` |
| `templates/report_template.html`, `generate_pdf.py`, `clean_output.py` | the server renders each memo version with the same template (`src/tools/templates/`) and writes the delivery folder |
| a single analyst | nine bots, each owning the sections and lenses in its prompt |

[`../prompts/sections.md`](../prompts/sections.md) lists where the app departs from the playbooks and why.
