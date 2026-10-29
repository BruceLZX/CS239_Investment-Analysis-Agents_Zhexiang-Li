"""The workflow records, ported from the skill's scripts/check_workflow_docs.py: the research plan, the profile
requirements, the thesis table, the scenario analysis, the red-team review and any open rewrite plan.

The skill keeps these as _work/*.md files; here they are case-file records the Lead and the Red Team write with
tools, and the constants below are the skill's templates (scripts/run_analysis_harness.py).

Fixed here:
- The thesis table failed a Confidence cell of "High" (8-character minimum on every cell); confidence needs a level.
- The scenario table skipped any row that mentioned the word "scenario", and a bare "30%" probability failed the
  length rule; probabilities are read as numbers and must add up to 100%.
- "## The One Question" passed on the unfilled template; the question itself is checked now.
- The profile checklist passed with 4 of codex's 9 items done; SKILL.md says to complete it, so every item counts.
"""
import re

from .terms import has_placeholder

# run_analysis_harness.py's research-plan gates, with the skill's file names replaced by the app's tools.
RESEARCH_GATES = (
    'Confirm company identity, legal entity, geography, stage, and business model.',
    'Choose 1-3 report spines from report_strategy_playbook.md.',
    'Decide whether the geographic market context lens is material; if yes, map home, revenue, expansion, supplier, '
    'comparable-company, capital, exit markets and the investor perspective.',
    'Decide whether the policy and geopolitics lens is material; if yes, map jurisdictions and perspective.',
    'Inventory the client documents.',
    'Complete the profile requirements before drafting.',
    'Build the source register with source type, date, confidence, claims and a link or file/page reference.',
    'Use visible source IDs such as [S1] as citations in the report.',
    'Complete the evidence matrix for all material sections before drafting.',
    'Run the pre-draft evidence gate and fix failures.',
    'Draft the report from evidence, not from outline memory.',
    'Run the red-team pass and rewrite weak sections.',
    'Run final QA, print the PDF, and verify the delivery folder.',
)
MIN_GATES = 8
# The app's profile: run_analysis_harness.py's codex requirements (the skill's default profile) plus its
# claude-code-deepseek-ocr requirements, since the team runs on DeepSeek and may read scanned decks.
PROFILE_ITEMS = (
    'Use web and data tools for fresh facts whenever a company, market, price, policy, filing, funding, or executive '
    'fact may have changed.',
    'For each major section, record targeted search strings, opened sources, source IDs, and why the selected sources '
    'are decision-grade rather than merely convenient.',
    "Use the server's checks for deterministic QA, extraction, citation checks and the delivery folder; do not rely on "
    'a one-shot narrative draft.',
    'Do not generate repeated filler paragraphs such as per-section original-document priority, citation-anchor blocks, '
    'or repeated metric-card copy; each section must contain content-specific analysis.',
    'Before drafting, write a section distinctness plan: the unique decision question, mechanism, comparison set, '
    'counter-evidence, and best visual artifact for each section.',
    'For each section, draft one final-report thesis sentence that directly analyzes the company; never copy internal '
    'plan labels or rubric language into the report.',
    'Remove repeated visible scaffolds such as "Economic mechanism", "Comparison and benchmark", "Counter-evidence and '
    'risk" and "Investor implication"; keep the scaffold internal.',
    'Use a verdict strip, compact decision cards, selected tables, and at most a few KPI strips; do not repeat the same '
    'card, grid or dashboard pattern in every section.',
    'Before writing the executive briefing, summarize the non-consensus or consensus view and the exact evidence that '
    'changes the decision.',
    'Treat OCR as a pipeline: inventory files, OCR scan- or slide-heavy material, and keep page, slide or table '
    'references for every extracted claim.',
    'Check every page holding numbers, TAM, valuation, customers, clinical or regulatory claims, policy claims, '
    'financing terms or team credentials before relying on it.',
    'Mark OCR-derived claims low confidence until checked or corroborated; use ranges for OCR-derived financial inputs.',
    'Build a claim verification table for material company-provided claims: verified, partially verified, unverified, '
    'contradicted, or not publicly disclosed.',
)
MIN_PROFILE_EVIDENCE = 240
# analysis_core.md "Deal Thesis Workflow": the thesis table's rows, and the rows a listed company adds.
THESIS_COMPONENTS = ('Customer pain', 'Product advantage', 'Market timing', 'GTM scalability', 'Unit economics',
                     'Team execution', 'Valuation fit', 'Exit path')
THESIS_PUBLIC_COMPONENTS = ('Current price vs. intrinsic value', 'Earnings quality', 'Free cash flow conversion',
                            'Balance-sheet health', 'Consensus/guidance delta', 'Catalysts and timing', 'Position sizing')
MIN_THESIS_ROWS = 6
# The red-team review's questions (run_analysis_harness.py red_team_review.md).
RED_TEAM_QUESTIONS = {
    'most_damaging_fact': 'What fact, if wrong, would most damage the thesis?',
    'company_only_claims': 'Which positive claims rely only on company-provided materials?',
    'generic_section': 'Which section is generic or lacks source-backed mechanism?',
    'unpriced_risk': 'Which risk is mentioned but not priced into the recommendation?',
    'first_challenge': 'What would a skeptical investment committee partner challenge first?',
    'downside_survival': 'Does the conclusion survive downside assumptions: market 50% smaller, CAC 2x higher, revenue '
                         '30% lower, financing delayed 6 months (listed: multiples compress, free cash flow 30% lower, '
                         'refinancing costs rise)?',
    'ocr_claims': 'Are all OCR-derived claims visually checked or independently corroborated?',
}
MIN_RED_TEAM_CHARS = 600


def _probability(text: str) -> float | None:
    match = re.search(r'(\d{1,3}(?:\.\d+)?)\s*%', str(text))
    return float(match.group(1)) if match else None


def check_research_plan(plan: dict | None) -> list[str]:
    if not plan:
        return ['no research plan']
    failures = []
    checked = [gate for gate in plan.get('gates') or [] if gate in RESEARCH_GATES]
    if len(checked) < MIN_GATES:
        failures.append(f'research plan: {len(checked)} of the 13 gates done; needs {MIN_GATES}')
    spines = plan.get('spines') or []
    if not 1 <= len(spines) <= 3 or not all(str(s.get('must_answer', '')).strip() for s in spines):
        failures.append('research plan: choose 1-3 report spines, each with the question it must answer')
    if not str(plan.get('hypothesis', '')).strip():
        failures.append('research plan: no current decision hypothesis')
    return failures


def check_profile(profile: dict | None) -> list[str]:
    if not profile:
        return ['no profile requirements']
    failures = []
    done = [item for item in profile.get('items') or [] if item in PROFILE_ITEMS]
    if len(done) < len(PROFILE_ITEMS):
        failures.append(f'profile requirements: {len(done)} of {len(PROFILE_ITEMS)} done')
    if len(str(profile.get('evidence', '')).strip()) < MIN_PROFILE_EVIDENCE:
        failures.append(f'profile requirements: the evidence of completion needs {MIN_PROFILE_EVIDENCE} characters')
    return failures


def check_thesis_table(table: dict | None, listed: bool) -> list[str]:
    if not table:
        return ['no thesis table']
    rows = table.get('rows') or []
    argued = [row for row in rows
              if all(len(str(row.get(f, '')).strip()) >= 8 for f in ('belief', 'evidence', 'counter_evidence', 'change'))
              and re.search(r'high|medium|low|高|中|低', str(row.get('confidence', '')), re.I)]
    failures = []
    if len(argued) < MIN_THESIS_ROWS:
        failures.append(f'thesis table: {len(argued)} fully argued rows; needs {MIN_THESIS_ROWS}')
    names = {str(row.get('component', '')).strip().lower() for row in rows}
    wanted = THESIS_COMPONENTS + (THESIS_PUBLIC_COMPONENTS if listed else ())
    missing = [c for c in wanted if c.lower() not in names]
    if missing:
        failures.append('thesis table: no row for ' + ', '.join(missing))
    return failures


def check_scenario_analysis(analysis: dict | None) -> list[str]:
    if not analysis:
        return ['no scenario analysis']
    failures = []
    by_case = {str(s.get('case', '')).strip().lower(): s for s in analysis.get('scenarios') or []}
    probabilities = []
    for case in ('bull', 'base', 'bear'):
        row = by_case.get(case)
        if not row or any(len(str(row.get(f, '')).strip()) < 8 for f in ('driver', 'evidence', 'outcome', 'implication')):
            failures.append(f'scenario analysis: the {case} case is missing or too thin')
        probability = _probability(row.get('probability', '')) if row else None
        if row and probability is None:
            failures.append(f'scenario analysis: the {case} case has no probability')
        probabilities.append(probability or 0)
    if all(probabilities) and abs(sum(probabilities) - 100) > 2:
        failures.append(f'scenario analysis: probabilities add up to {sum(probabilities):g}%, not 100%')
    least = {'assumption': 8, 'disproof': 8, 'impact': 3, 'early_warning': 6}
    assumptions = [a for a in analysis.get('assumptions') or []
                   if all(len(str(a.get(f, '')).strip()) >= n for f, n in least.items())]
    if not 3 <= len(assumptions) <= 5:
        failures.append(f'scenario analysis: {len(assumptions)} fully stated key assumptions; needs 3-5')
    consensus = analysis.get('consensus') or {}
    if any(len(str(consensus.get(f, '')).strip()) < 12 for f in ('consensus', 'our_view', 'evidence', 'proof_event')):
        failures.append('scenario analysis: the consensus / non-consensus view is incomplete')
    question = analysis.get('one_question') or {}
    if str(question.get('question', '')).count('?') + str(question.get('question', '')).count('？') != 1:
        failures.append('scenario analysis: the one question must be exactly one question')
    if len(str(question.get('why', '')).strip()) < 40:
        failures.append('scenario analysis: say why the answer to the one question would change the decision')
    return failures


def check_red_team(review: dict | None) -> list[str]:
    if not review:
        return ['no red-team review']
    answers = review.get('answers') or {}
    failures = [f'red-team review: "{question}" is unanswered' for key, question in RED_TEAM_QUESTIONS.items()
                if len(str(answers.get(key, '')).strip()) < 20]
    written = sum(len(str(answer).strip()) for answer in answers.values())
    if written < MIN_RED_TEAM_CHARS:
        failures.append(f'red-team review: {written} characters of analysis; needs {MIN_RED_TEAM_CHARS}')
    return failures


def check_workflow_docs(case: dict, listed: bool, stage: str = 'version') -> dict:
    """The workflow records for a stage: 'draft' (before analysts draft: the plan and profile) or 'version' (before
    a version goes to review: every record, and no open rewrite plan)."""
    workflow = case.get('workflow') or {}
    failures = check_research_plan(workflow.get('research_plan')) + check_profile(workflow.get('profile_requirements'))
    if stage == 'version':
        failures += check_thesis_table(workflow.get('thesis_table'), listed)
        failures += check_scenario_analysis(workflow.get('scenario_analysis'))
        failures += check_red_team(workflow.get('red_team_review'))
        open_items = [item for item in workflow.get('rewrite_plan') or [] if not item.get('resolved')]
        if open_items:
            failures.append(f'rewrite plan: {len(open_items)} items unresolved after a failed QA loop')
    text = ' '.join(str(record) for record in workflow.values())
    if has_placeholder(text):
        failures.append('placeholder text (TODO, TBD, xxx) remains in the workflow records')
    return {'failures': failures, 'passed': not failures}
