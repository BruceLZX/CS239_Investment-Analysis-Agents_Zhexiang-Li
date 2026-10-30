"""The rewrite plan, ported from scripts/diagnose_report.py: after a failed QA loop, what each section's
owner must rewrite, and the report-level root causes.

The original writes _work/rewrite_plan.md with unchecked boxes that block the next gate until ticked. Here the plan is a
case-file record, and an item is resolved by the work itself rather than by ticking a box: a section item when its
section is saved again (still_failing says whether that revision passes its check), a report item when a later QA
loop or version checks the whole report again, which reports the problem afresh if it is still there. An open plan
is never an item of its own: the first runs had a failed loop's open item fail every later loop.
"""
OPEN_PLAN = 'rewrite plan:'  # how check_workflow_docs.py words an open plan
from .. import sections

# diagnose_report.py "Required Fixes", in the app's terms.
REQUIRED_FIXES = (
    'Keep the template: the server renders it, so never paste HTML or template text into a section.',
    'Delete any sentence about how the report should be written or what a section must contain.',
    "Rewrite each failing section from its evidence block, starting from that block's final-report thesis sentence.",
    'Replace repeated mechanism, benchmark, risk and implication blocks with section-specific analysis.',
    'Cite per paragraph (at most six inline tags a section) and put row-level sources in a table\'s Source column.',
    'Use tables and components only where they carry the decision; one KPI dashboard, not one per section.',
    'Save the section again and read its check; then run the QA loop again.',
)


def rewrite_plan(section_failures: dict[str, list[str]], report_failures: list[str], saved_at: str) -> list[dict]:
    """One item per failing section (for its owner) and one per report-level failure (for the Lead)."""
    items = []
    for key, failures in section_failures.items():
        if failures:
            section = sections.BY_KEY[key]
            items.append({'id': f'W{len(items) + 1}', 'section': key, 'owner': section.owner,
                          'problems': failures[:8], 'created_at': saved_at, 'resolved': False})
    for failure in report_failures:
        if failure.startswith(OPEN_PLAN):
            continue
        items.append({'id': f'W{len(items) + 1}', 'section': None, 'owner': sections.LEAD, 'problems': [failure],
                      'created_at': saved_at, 'resolved': False})
    return items


def resolve(items: list[dict], latest: dict[str, dict], checked_at: str | None = None) -> list[dict]:
    """Mark items resolved: a section item once its section has a revision saved after the item, a report item once
    the report is checked again after it (checked_at: when a QA loop or a version's check is starting)."""
    for item in items:
        if item.get('resolved'):
            continue
        if item['section']:
            revision = latest.get(item['section'])
            if revision and revision['saved_at'] >= item['created_at']:
                item.update(resolved=True, still_failing=not revision.get('passed'))
        elif checked_at and checked_at >= item['created_at']:
            item['resolved'] = True
    return items
