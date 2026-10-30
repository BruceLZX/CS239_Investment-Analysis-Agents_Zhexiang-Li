"""The workflow records as tool arguments: the evidence matrix, the research plan, the thesis table, the
scenario analysis, the red-team review and the investor review.

The playbooks keep them as _work/*.md files created from templates; here each is a
typed tool argument, so a bot fills the same fields and the server stores them in the case file. The field
descriptions are what the bots see.
"""
from pydantic import BaseModel, Field

from .qa.check_evidence import GATE_ITEMS, PLAN_FIELDS


class EvidenceRow(BaseModel):
    """One row of a section's Deep Evidence Table."""
    source_ids: str = Field(description='The registered source IDs behind the row, e.g. "S3, S7".')
    source_type: str = Field(description='primary, near-primary, independent, company-provided, market data or OCR.')
    finding: str = Field(description='The finding or fact, with its figure.')
    mechanism: str = Field(description='The economic or strategic mechanism the evidence shows.')
    benchmark: str = Field(description='The peer, benchmark, base rate or history it is compared with.')
    weakens: str = Field(description='What weakens or contradicts it.')
    implication: str = Field(description='What it means for the investor: invest, pass, wait, price lower, add a '
                                         'condition or diligence further.')
    confidence: str = Field(description='high, medium or low, and why.')
    follow_up: str = Field(description='The diligence question it leaves open.')


class SectionPlan(BaseModel):
    """The internal section plan: never copied into the report."""
    decision_question: str = Field(description=PLAN_FIELDS['decision_question'])
    thesis_sentence: str = Field(description='The final-report thesis sentence: one judgement on the company.')
    why_different: str = Field(description=PLAN_FIELDS['why_different'])
    mechanism: str = Field(description=PLAN_FIELDS['mechanism'])
    comparison_set: str = Field(description=PLAN_FIELDS['comparison_set'])
    counter_evidence: str = Field(description=PLAN_FIELDS['counter_evidence'])
    visual: str = Field(description='The component or table that carries the section\'s key evidence.')
    prohibited: str = Field(description=PLAN_FIELDS['prohibited'])


class Spine(BaseModel):
    spine: str = Field(description='An analysis spine from report_strategy_playbook.md, e.g. "Public equity".')
    must_answer: str = Field(description='The question this spine says the report must answer.')


class ThesisRow(BaseModel):
    component: str = Field(description='Customer pain, Product advantage, Market timing, GTM scalability, Unit '
                                       'economics, Team execution, Valuation fit, Exit path; for a listed company also '
                                       'Current price vs. intrinsic value, Earnings quality, Free cash flow conversion, '
                                       'Balance-sheet health, Consensus/guidance delta, Catalysts and timing, Position sizing.')
    belief: str = Field(description='The current belief.')
    evidence: str = Field(description='The evidence for it, with source IDs.')
    counter_evidence: str = Field(description='The evidence against it.')
    confidence: str = Field(description='high, medium or low.')
    change: str = Field(description='What would change the belief.')


class Scenario(BaseModel):
    case: str = Field(description='Bull, Base or Bear.')
    probability: str = Field(description='e.g. "25%"; the three add up to 100%.')
    driver: str = Field(description='The specific driver or failure mode.')
    evidence: str = Field(description='Why it is plausible, with source IDs.')
    outcome: str = Field(description='The financial or milestone outcome: price, return, MOIC or milestone.')
    implication: str = Field(description='What the investor does in this case.')


class Assumption(BaseModel):
    assumption: str
    confidence: str = Field(description='high, medium or low.')
    disproof: str = Field(description='What would disprove it.')
    impact: str = Field(description='Impact on value if wrong, e.g. "-25% EV".')
    early_warning: str = Field(description='The early warning sign to watch.')


class Consensus(BaseModel):
    consensus: str = Field(description='What the market, comparable investors or the company pitch assume.')
    our_view: str = Field(description='Our view, or that the thesis is consensus.')
    evidence: str = Field(description='The evidence for the difference, or why there is no edge.')
    proof_event: str = Field(description='The event that would prove or disprove the view.')


class OneQuestion(BaseModel):
    question: str = Field(description='The single answerable diligence question that would most change the decision.')
    why: str = Field(description='Why its answer would change the decision.')


class RedTeamAnswers(BaseModel):
    most_damaging_fact: str = Field(description='What fact, if wrong, would most damage the thesis?')
    company_only_claims: str = Field(description='Which positive claims rely only on company-provided materials?')
    generic_section: str = Field(description='Which section is generic or lacks a source-backed mechanism?')
    unpriced_risk: str = Field(description='Which risk is mentioned but not priced into the recommendation?')
    first_challenge: str = Field(description='What would a skeptical investment committee partner challenge first?')
    downside_survival: str = Field(description='Does the conclusion survive the downside assumptions (market 50% '
                                               'smaller, CAC 2x, revenue 30% lower, financing 6 months late; listed: '
                                               'multiples compress, FCF 30% lower, refinancing costs rise)?')
    ocr_claims: str = Field(description='Are all OCR-derived claims checked or corroborated? Say so if there are none.')


class ReviewItem(BaseModel):
    severity: str = Field(description='Critical (must be fixed before delivery, with new evidence or a stated '
                                      'limitation), Important (should be fixed; if not, listed as further diligence) '
                                      'or Minor.')
    sections: list[str] = Field(description='The section keys it concerns, e.g. ["financials"]; each goes to its owner.')
    issue: str = Field(description='The issue, specifically: what is missing, wrong or unverified.')
    action: str = Field(description='The fix, e.g. the search to run or the comparison to add.')
    evidence_request: str = Field(default='', description='Evidence the team has not gathered, as a question for the '
                                                          'section owner; empty when none.')


def gate_items(numbers: list[int]) -> list[str]:
    """The section-gate items checked, from their numbers (1-9)."""
    return [GATE_ITEMS[n - 1] for n in dict.fromkeys(numbers) if 1 <= n <= len(GATE_ITEMS)]
