# Added enforcement

## Permission to set scope

Records: Before set_case_scope, reads the query-selected caller, fixed role membership including nested groups, action grants and active case ID.

Rules: This branch requires lead_role membership, Can for set_case_scope on case, and an observed case ID. Missing role or case evidence prevents this Allow. Missing Can for any configured action scope explicitly denies, overriding any Allow.
Scope can be set only while absent. Invalid company_type still reaches original validation. Passing this check only permits an attempt subject to other denials and original checks.

## Lead permission to save sections

Records: Before save_memo_part, reads the query-selected caller, fixed role membership including nested groups, action grants and active case ID.

Rules: This branch requires lead_role membership, Can for save_memo_part on report_sections, and an observed case ID. Missing role or case evidence prevents this Allow. Missing Can for any configured action scope explicitly denies, overriding any Allow.
The configured section ownership requirement also applies. Passing this check only permits an attempt subject to other denials and original checks.

## Researcher permission to save sections

Records: Before save_memo_part, reads the query-selected caller, fixed role membership including nested groups, action grants and active case ID.

Rules: This branch requires researcher_roles membership, Can for save_memo_part on report_sections, and an observed case ID. Missing role or case evidence prevents this Allow. Missing Can for any configured action scope explicitly denies, overriding any Allow.
The configured section ownership requirement also applies. Passing this check only permits an attempt subject to other denials and original checks.

## Permission to save versions

Records: Before save_memo_version, reads the query-selected caller, fixed role membership including nested groups, action grants and active case ID.

Rules: This branch requires lead_role membership, Can for save_memo_version on report, and an observed case ID. Missing role or case evidence prevents this Allow. Missing Can for any configured action scope explicitly denies, overriding any Allow.
Section presence and authorship, workflow evidence, the three completion requirements and the review lock also apply. Passing this check only permits an attempt subject to other denials and original checks.

## Permission to start reviews

Records: Before start_review, reads the query-selected caller, fixed role membership including nested groups, action grants and active case ID.

Rules: This branch requires reviewer_role membership, Can for start_review on reviews, and an observed case ID. Missing role or case evidence prevents this Allow. Missing Can for any configured action scope explicitly denies, overriding any Allow.
Review-start evidence, existing verdicts, review serialization and the round limit also apply. Starting needs no current approval. Passing this check only permits an attempt subject to other denials and original checks.

## Permission to save review passes

Records: Before save_review_pass, reads the query-selected caller, fixed role membership including nested groups, action grants and active case ID.

Rules: This branch requires reviewer_role membership, Can for save_review_pass on reviews, and an observed case ID. Missing role or case evidence prevents this Allow. Missing Can for any configured action scope explicitly denies, overriding any Allow.
Review ID, pass number, finished status, item contents and proposed item count remain original-app checks; this permission adds no such refusal. Passing this check only permits an attempt subject to other denials and original checks.

## Permission to approve reviews

Records: Before finish_review, reads the query-selected caller, fixed role membership including nested groups, action grants and active case ID.

Rules: This branch requires reviewer_role membership, Can for finish_review on reviews, and an observed case ID. Missing role or case evidence prevents this Allow. Missing Can for any configured action scope explicitly denies, overriding any Allow.
The permission rule does not distinguish verdicts. The original app normalizes and validates them. Saved passes, existing verdicts and approval findings also constrain this branch. Passing this check only permits an attempt subject to other denials and original checks.

## Permission to request revision

Records: Before finish_review, reads the query-selected caller, fixed role membership including nested groups, action grants and active case ID.

Rules: This branch requires reviewer_role membership, Can for finish_review on reviews, and an observed case ID. Missing role or case evidence prevents this Allow. Missing Can for any configured action scope explicitly denies, overriding any Allow.
The permission rule does not distinguish verdicts. The original app normalizes and validates them. Saved passes and existing verdicts also constrain this branch. Passing this check only permits an attempt subject to other denials and original checks.

## Permission to reject reviews

Records: Before finish_review, reads the query-selected caller, fixed role membership including nested groups, action grants and active case ID.

Rules: This branch requires reviewer_role membership, Can for finish_review on reviews, and an observed case ID. Missing role or case evidence prevents this Allow. Missing Can for any configured action scope explicitly denies, overriding any Allow.
The permission rule does not distinguish verdicts. The original app normalizes and validates them. Saved passes and existing verdicts also constrain this branch. Passing this check only permits an attempt subject to other denials and original checks.

## Permission to deliver memos

Records: Before deliver_memo, reads the query-selected caller, fixed role membership including nested groups, action grants and active case ID.

Rules: This branch requires lead_role membership, Can for deliver_memo on report, and an observed case ID. Missing role or case evidence prevents this Allow. Missing Can for any configured action scope explicitly denies, overriding any Allow.
Selected-version approval, later verdicts, nonapproved final rounds and stored findings also constrain delivery. Passing this check only permits an attempt subject to other denials and original checks.

## Permission to tell the user

Records: Before tell_user, reads the query-selected caller, fixed role membership including nested groups, action grants and active case ID.

Rules: This branch requires lead_role membership, Can for tell_user on user_messages, and an observed case ID. Missing role or case evidence prevents this Allow. Missing Can for any configured action scope explicitly denies, overriding any Allow.
The message-length alternatives also apply. This role check does not control message bodies, model contexts, direct user threads, automatic replies or message_bot. Passing this check only permits an attempt subject to other denials and original checks.

## Permission to leave notes

Records: Before leave_note, reads the query-selected caller, fixed role membership including nested groups, action grants and active case ID.

Rules: This branch requires researcher_roles membership, Can for leave_note on case_notes, and an observed case ID. Missing role or case evidence prevents this Allow. Missing Can for any configured action scope explicitly denies, overriding any Allow.
The trimmed note-length requirement also applies. Passing this check only permits an attempt subject to other denials and original checks.

## Set scope once

Records: Before set_case_scope, reads scope from the locked active case. The original setter persists scope after a clean return.

Rules: Any saved scope other than None explicitly denies another set_case_scope, including an empty dictionary or an identical request. Absence passes only this restriction; scope-setting permission still applies. Failed case capture raises.
This check does not require scope before other actions or a brief, and does not inspect message or turn boundaries.

## Save only owned sections

Records: Before save_memo_part, resolves the section argument against configured keys, numbered aliases or case-insensitive titles after trimming; reads its configured owner and caller.

Rules: Require a resolved section and caller equal to its configured owner, plus a permitted save role. Otherwise no save Allow exists and an explicit denial follows, shown as POLICY_BLOCKED. Lead owns executive_summary, thesis, scoring; Company owns company_overview, team; Product owns technology_product, strategy.
Market owns market, competition; Fundamentals owns business_model, financials; Valuation owns funding_valuation, exit; Regulatory owns esg; Red Team owns risk. These names designate the corresponding Analyst identities. Lead has no ownership override.
This governs tool saves, not existing imported revisions. The framework limits each encoded parameter to 4096 UTF-16 code units, which can reject markdown below the original normalized 9000-character limit; it adds no section-content validation.

## Require every current section

Records: Before save_memo_version, reads the latest revision of each configured section from the active case, associated with this request.

Rules: Require all 15 current sections: executive_summary, company_overview, team, technology_product, market, competition, business_model, financials, funding_valuation, strategy, risk, thesis, exit, esg, scoring. Any missing section prevents Allow and triggers the combined prerequisite denial.
Earlier saved-version references cannot substitute. This tests presence, not nonempty markdown, passed revision checks, depth, QA cleanliness or resolved edits. The original readiness refuse-once exception cannot bypass this conjunction; other version requirements still apply.

## Require each section owner as author

Records: Before save_memo_version, reads each current section’s configured owner and saved revision author. save_memo_part records the caller as author when saving; imported revisions can also supply attribution.

Rules: For every required current section, its owner and author must both exist and match on that same section. Owners may differ across sections; use the configured section ownership mapping. Any missing or mismatched author prevents version Allow and triggers the combined prerequisite denial.
Stored attribution does not establish research, content origin or correctness. This check does not verify content against saved hashes or require requested revisions to be resolved; it adds no lock against editing approved content.

## Require a thesis table

Records: Before save_memo_version, reads the current thesis_table workflow dictionary stored by save_thesis_table; workflow lists are skipped.

Rules: Require a thesis_table workflow record associated with this request; an empty dictionary qualifies. Missing evidence prevents version Allow and triggers the combined prerequisite denial. Other version requirements still apply.
This tests existence, not author, content or validation success. save_thesis_table has no added gate and can store a record while returning validation failures; its access checks remain delegated to the original app.

## Require scenario analysis

Records: Before save_memo_version, reads the current scenario_analysis workflow dictionary stored by save_scenario_analysis; workflow lists are skipped.

Rules: Require a scenario_analysis workflow record associated with this request; an empty dictionary qualifies. Missing evidence prevents version Allow and triggers the combined prerequisite denial. Other version requirements still apply.
This tests existence, not author, content or validation success. save_scenario_analysis has no added gate and can store a record while returning validation failures; its access checks remain delegated to the original app.

## Require red-team authorship

Records: Before save_memo_version or start_review, reads the current red_team_review workflow object, its author recorded by save_red_team_review, and fixed red_team_role membership.

Rules: Saving a version requires that stored review object with an author in red_team_role. Missing evidence prevents version Allow and triggers the combined prerequisite denial. The initial review-start alternative also needs this object; the prior-verdict alternative can proceed without it.
The check uses stored workflow state, not a completion event. save_red_team_review has no added gate and may store validation failures. Answers, actual attack work and linkage to the selected memo version are unchecked.

## Run QA in the version interval

Records: After run_qa_loop returns normally, records an applied completion event with caller, case ID and pre-call saved-draft count. Before save_memo_version, reads that evidence and the current saved-draft count.

Rules: Require an applied run_qa_loop event for the same caller and case, with its pre-call draft count equal to the current count. Missing evidence prevents version Allow and triggers the combined prerequisite denial. All three operation requirements must hold, in any order.
A newly appended version requires fresh evidence at the new count. Evidence remains reusable at the same count after content edits. Returned validation or quality failures still count as completion; original refusal or an exception does not. Other version requirements still apply.

## Save a plan in the version interval

Records: After save_research_plan returns normally, records an applied completion event with caller, case ID and pre-call saved-draft count. Before save_memo_version, reads that evidence and the current saved-draft count.

Rules: Require an applied save_research_plan event for the same caller and case, with its pre-call draft count equal to the current count. Missing evidence prevents version Allow and triggers the combined prerequisite denial. All three operation requirements must hold, in any order.
A newly appended version requires fresh evidence at the new count. Evidence remains reusable at the same count after content edits. Returned validation or quality failures still count as completion; original refusal or an exception does not. Other version requirements still apply.

## Save profile requirements in the version interval

Records: After save_profile_requirements returns normally, records an applied completion event with caller, case ID and pre-call saved-draft count. Before save_memo_version, reads that evidence and the current saved-draft count.

Rules: Require an applied save_profile_requirements event for the same caller and case, with its pre-call draft count equal to the current count. Missing evidence prevents version Allow and triggers the combined prerequisite denial. All three operation requirements must hold, in any order.
A newly appended version requires fresh evidence at the new count. Evidence remains reusable at the same count after content edits. Returned validation or quality failures still count as completion; original refusal or an exception does not. Other version requirements still apply.

## Block versions during unfinished reviews

Records: Before save_memo_version, reads every case review and each non-None verdict. start_review initializes no verdict; finish_review stores the normalized verdict.

Rules: Explicitly deny saving if any review lacks all three exact verdicts approve, revise and reject. Missing, None, empty or unrecognized verdicts trigger the denial, regardless of the review’s version. No reviews causes no denial here. This overrides a positive version branch.

## Require evidence to start a review

Records: Before start_review, resolves memo_version against the locked case, with 0 selecting the latest saved version; reads all case reviews, current risk section and current red-team workflow evidence.

Rules: Require case ID and a real selected saved version, plus either any case review with any non-None verdict, or the red-team authorship requirement with current risk owner and author both equal to that same red-team author. Neither alternative yields Allow when the version is missing; no full start Allow explicitly denies.
The prior verdict may be empty or unrecognized and concern any version. Current risk and red-team evidence need not belong to the selected saved version. Starting permission and all review denials still apply; an unfinished same-version review can restart and lose its passes.

## Keep finished-version verdicts

Records: Before start_review, resolves the selected version; before finish_review, resolves the requested review ID to its saved version. Both calls read all case review versions and non-None verdicts.

Rules: Explicitly deny either call if any review of that same resolved version has any verdict fact, even on another review ID. Empty and unrecognized verdicts count; None does not. This overrides any positive start or finish branch.

## Keep open reviews on one version

Records: Before start_review, reads the resolved target version and every case review’s saved version and non-None verdict.

Rules: Explicitly deny if any review of a different observed version lacks each of the exact verdicts approve, revise and reject. Missing, empty or unknown verdicts qualify. A review without an observed version cannot match this denial.
An unfinished same-version review does not trigger this restriction and can reset if the review-start evidence, permission and other denials permit it.

## Stop starts after a finished third round

Records: Before start_review, reads stored numeric review rounds and non-None verdicts. The original start assigns a new round as finished-review count plus 1; a reset retains its round.

Rules: Explicitly deny if any review has round >= 3 and any verdict fact, regardless of selected version or verdict recognition. An open round 3 with no verdict does not trigger this rule. Missing round also does not trigger it.
This compares stored round numbers, not the number of finished reviews: one imported round-3 verdict can block, while three low-numbered reviews need not. Other start requirements still apply.

## Require all five review passes

Records: Before finish_review, resolves the requested review and its saved version, then reads every review’s saved pass keys as integers. save_review_pass stores those keys when saving a pass.

Rules: Require one review of that resolved version containing all pass numbers 1, 2, 3, 4 and 5. Extra keys qualify; pass order and content are unchecked. Missing review/version or required keys prevents finish Allow and explicitly denies. Another same-version review can supply this evidence.
The original callback separately requires all five keys on the requested review and validates critical/nonapproval items. Nonnumeric keys raise during capture. Added rules do not require exact section/document reads, substantive review or resolved findings; original coarse read checks depend on policy mode.

## Block approval with saved rule findings

Records: Before finish_review, reads the raw verdict argument and rule_findings from the check stored with the requested review’s saved memo version; these findings were captured when that version was saved.

Rules: Explicitly deny when the raw verdict equals approve exactly and any saved rule finding exists, regardless of rule or severity. A valid empty list avoids this denial. Missing or malformed check/finding data raises; missing saved version prevents finish Allow.
The original app trims and lowercases verdicts, so APPROVE or whitespace variants evade this denial unless its enforce-mode approval check blocks them. Overall failed checks, report/depth/evidence/PDF failures and incomplete findings alone do not trigger this rule; other finish requirements remain.

## Require unsuperseded version approval

Records: Before deliver_memo, resolves version, with 0 selecting the latest, and reads all case reviews’ versions, list positions and non-None verdicts. finish_review stores verdicts in case state.

Rules: Require an observed review position and exact approve for the selected saved version. Missing version, review, approval or another delivery Allow requirement explicitly denies. Any qualifying approval with any later-position verdict-bearing review also explicitly denies, even across versions or despite a newer qualifying approval.
An open later review with None does not supersede. Permission and other delivery denials still apply. Approval covers stored version numbers, not final rendered bytes: source/client files and rendering can change. Current draft edits alone do not block; delivery uses saved revision references.

## Block delivery after a nonapproved third round

Records: Before deliver_memo, reads numeric rounds and non-None verdicts from every stored case review, including older reviews and reviews of other memo versions.

Rules: Explicitly deny if any review has round >= 3 and a verdict other than exact approve, even when the selected version later gained approval. Empty or unknown verdicts count. Missing round or verdict does not trigger this denial. Other delivery requirements still apply.

## Block delivery with saved rule findings

Records: Before deliver_memo, reads rule_findings from the resolved selected version’s saved check. The original version save obtains and stores this finding list from memo checks.

Rules: Explicitly deny before delivery filesystem work if any selected-version rule finding exists, regardless of approval, rule, severity or count. A valid empty list avoids this denial; missing or malformed check data raises. Delivery permission and approval requirements still apply.
This does not require overall passed checks, complete QA success, PDF creation or user receipt. Final rendering/checking occurs after permission; the original callback records a delivery even when final checks fail, without an added denial or rollback.

## Limit user messages with state exceptions

Records: Before tell_user, counts Unicode code points in the original untrimmed message and reads local delivery versions plus every review’s version, round and non-None verdict.

Rules: With tell_user permission, allow length 0–300 inclusive, or any nonnegative length if a local delivery and an exact approve review share a version, or any nonnegative length if any review has round >= 3 and a verdict other than exact approve. No full alternative Allow explicitly denies; all other gates remain.
Exceptions need no latest review/version, message meaning, passed final check, PDF or receipt; older approval plus delivery survives later disapproval. Empty messages qualify; spaces count before trimming. Each encoded parameter still has a 4096 UTF-16-code-unit cap. Missing verdict cannot establish final failure.
No added content classifier checks status, internal material, ratings or figures. Original content/status rules can still refuse; content enforcement depends on enforce mode and original exception tests differ. Direct user threads, automatic replies, message_bot and model contexts are outside these added gates.

## Limit trimmed notes and replies

Records: Before leave_note, counts Unicode code points after trimming the actual note argument. The original tool also stores trimmed text.

Rules: Require trimmed length 1–600 inclusive and note permission for both new notes and replies using answers. No exception depends on section or sources. Missing a complete leave_note Allow explicitly denies.
Per-brief note quotas, source IDs, recipients and answer validity remain original-app checks. The added rules do not enforce note counts or item-routing counts.
