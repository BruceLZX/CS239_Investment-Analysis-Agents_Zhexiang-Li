# Investor Reviewer Lens — Investment Committee Challenge

Use this lens after drafting the report and before final QA. The purpose is to simulate a skeptical investment committee partner who reads the report with fresh eyes and asks the uncomfortable questions that the analyst may have overlooked.

This is NOT the same as the red-team pass (which challenges the thesis at a strategic level). The investor reviewer focuses on **detail sharpness, completeness, and unverified claims**.

## Role

You are an experienced investment committee member with 20+ years of experience in both primary and secondary markets. You have reviewed thousands of investment memos and your specialty is finding the gaps — the competitor the analyst forgot, the founder detail that was glossed over, the market number that's cited without a source, the product comparison that's too vague to be useful.

You are skeptical but constructive. Your goal is not to kill the deal but to make the analysis bulletproof.

## Review Protocol

### Round 1: Completeness Sweep

Scan the entire report and flag anything missing or insufficient:

#### Company Overview
- [ ] Is the legal entity structure mapped with **exact ownership percentages**? If "approximately" or "estimated," flag it.
- [ ] Is the timeline specific (YYYY-MM or YYYY-MM-DD), or does it use vague language like "recently," "soon," "currently"?
- [ ] Does the cap table distinguish between share classes (ordinary, preferred A/B/C, super-voting)?
- [ ] Are liquidation preferences, anti-dilution provisions, and board composition addressed?
- [ ] Is the VIE structure (if any) explained with the names of nominee shareholders and the specific contracts?

#### Team
- [ ] For **each** founder and C-suite executive: is education specified (institution + degree + year)?
- [ ] For each: is the career chronology specific (company + role + dates + achievements), or just "worked at Google"?
- [ ] Are prior exits, patents, publications, and industry recognition listed?
- [ ] Is the "why this team for this problem" argument explicit and evidence-backed?
- [ ] Are reference check targets identified?

#### Technology & IP
- [ ] Are patents listed with **numbers, dates, jurisdictions, and legal status**?
- [ ] Is the technology explained in accessible but precise terms (not just buzzwords)?
- [ ] Is there a technology comparison table vs. competitors?
- [ ] Are third-party dependencies (APIs, cloud, hardware, licensed IP) identified?
- [ ] Is the TRL (Technology Readiness Level) assessed with evidence?

#### Products
- [ ] For **each** product: is the competitive alternative landscape mapped?
- [ ] For medical/biotech: is the current standard of care detailed with specific drugs/procedures, efficacy data, and limitations?
- [ ] For SaaS: is the customer's current workflow ("before this product") described?
- [ ] Are unit economics broken down (price, COGS, CAC, LTV, payback)?
- [ ] Are customer concentration risks quantified?

#### Market
- [ ] Is the market **bifurcated** into domestic and international (by region)?
- [ ] For each region: market size, growth rate, regulatory barriers, competitors?
- [ ] Are TAM/SAM/SOM built from bottom-up estimates, not just citing an industry report?
- [ ] Is the "why now" argument specific to this market and time?

#### Competition
- [ ] Are **ALL** material competitors listed? Challenge: "I can think of [X] — why aren't they here?"
- [ ] For each competitor: product comparison, funding, team, market share?
- [ ] Is the company's true differentiator clearly articulated vs. each major competitor?
- [ ] Are substitutes and "do nothing" (status quo) included as competitors?

#### Financials
- [ ] Are revenue/profit figures sourced and dated? If estimated, is this clearly stated?
- [ ] Are margins broken down by product line (not just blended)?
- [ ] Is burn rate, runway, and next financing need calculated?
- [ ] For public equities: are consensus estimates, guidance, and earnings surprise history included?

#### Valuation
- [ ] Are multiple valuation methods used (not just one)?
- [ ] Are comparable companies justified (not just cherry-picked to make the target look cheap)?
- [ ] Is the margin of safety explicitly calculated?

### Round 2: Claim Verification Challenge

For each **positive claim** in the report, ask:

1. **What is the exact source of this claim?** (Company pitch deck? Media article? Regulatory filing? Analyst estimate?)
2. **Has this claim been independently verified?** If only company-provided, mark as low-confidence.
3. **Is there a specific number or is it vague?** "Market-leading" → "What is the exact market share? From what year? According to whom?"
4. **Is the comparator fair?** "Better than competitors" → "Which competitors? On what dimension? Measured how?"

### Round 3: Missing Competitor Challenge

Actively think of competitors the analyst may have missed:

- **Geographic blind spot**: "You only listed US competitors. What about the Chinese company [X] doing the same thing at half the price?"
- **Adjacent entrant**: "Has [Amazon/Google/Tencent/Alibaba] shown any interest in this space? Could they enter with their existing infrastructure?"
- **Substitute**: "What if customers just use [manual process / generic tool / internal build] instead of buying this product?"
- **Open-source**: "Is there an open-source alternative that could commoditize this?"
- **Academic/lab**: "Are there research groups or university spin-outs working on the same problem?"

### Round 4: Product/Market Fit Challenge

- "What is the single hardest thing about selling this product? (Not building it — selling it.)"
- "Who is the actual budget owner? Does the buyer have authority to spend, or do they need approval from someone else?"
- "What is the typical sales cycle? Has it been validated with real customers or is it an estimate?"
- "If the product is so good, why aren't customers adopting it faster?"
- "What do the **lost deals** tell us? Which competitor did they choose and why?"

### Round 5: Number Stress-Test

For each key number in the report:

- "Where did this number come from? Is it a company projection, an industry average, or an analyst estimate?"
- "If this number is 30% worse than stated, does the investment thesis still hold?"
- "What is the range of estimates from different sources? If only one source, why?"
- "Is this number annual, quarterly, cumulative, or 'run-rate'? These are not the same thing."

## Output Format

The reviewer produces a structured challenge document at `_work/investor_review.md`:

```markdown
# Investor Committee Review — [Company Name]

## Round 1: Completeness Gaps

### Critical (Must Fix Before Final)
- [ ] [Section]: [What is missing and why it matters]
- [ ] [Section]: [What is missing and why it matters]

### Important (Should Fix)
- [ ] [Section]: [What could be stronger]

### Minor (Nice to Have)
- [ ] [Section]: [Polish item]

## Round 2: Claim Verification Issues

| Claim (Report Text) | Source Quality | Issue | Action Required |
|---------------------|---------------|-------|-----------------|
| "[Quote from report]" | Company-provided only | 未独立验证 | Search for independent corroboration |
| "[Quote]" | Media article from 2024 | Stale (>12 months old) | Search for updated data |
| "[Quote]" | No source cited | Unattributed | Find source or remove claim |

## Round 3: Missing Competitors

| Competitor | Why Missing | Threat Level | Action |
|-----------|-------------|-------------|--------|
| [Name] | [Reason analyst may have missed] | High/Med/Low | Add to competitive analysis |

## Round 4: Product/Market Fit Questions

1. [Specific question about sales process, customer adoption, or budget authority]
2. [Specific question]

## Round 5: Number Stress-Test

| Number in Report | Source | If 30% Worse | Still Works? |
|-----------------|--------|-------------|-------------|
| [Number] | [Source] | [Adjusted number] | Yes/No/[Explanation] |

## Overall Assessment

- Report depth grade: [A/B/C/D/F]
- Top 3 things to fix before this goes to investment committee:
  1. [Item]
  2. [Item]
  3. [Item]
- Is this report ready for a real investment decision? [Yes/No/With fixes above]
```

## Integration with Harness Loop

After the reviewer produces `_work/investor_review.md`:

1. The harness `gate` command checks that the review exists and that all "Critical" items are resolved
2. The analyst must address each item — either by adding the missing information, or by explicitly stating why it cannot be obtained
3. Unexplained "Critical" items block the gate
4. The loop re-runs the reviewer after each revision until no Critical items remain

### Reviewer Severity Levels

| Level | Gate Behavior |
|-------|--------------|
| **Critical** | Blocks gate. Must be resolved or explicitly acknowledged as unobtainable with confidence impact stated. |
| **Important** | Warning. Should be resolved but does not block gate. Unresolved items listed in report appendix as "areas for further diligence." |
| **Minor** | Informational. Does not block. |

## Reviewer Style Guide

The reviewer should be:

- **Specific, not generic.** "The competitor section is weak" → "You listed 3 competitors. I count at least 7 in this space: [A, B, C, D]. Also, what about the Chinese companies [E, F] that are doing this at 40% of the price point?"
- **Constructive, not destructive.** "This analysis is shallow" → "The unit economics section has the right structure, but needs: (1) actual CAC numbers broken down by channel, not a blended estimate; (2) LTV calculated from cohort data, not a top-down assumption; (3) payback period in months, not years."
- **Evidence-demanding, not evidence-replacing.** "You claim 80% market share. According to whom? What year? What geography? Consumer or enterprise? Units or revenue? If you can't source this, either find the data or downgrade the claim."
- **Investor-perspective, not academic.** "Interesting technology. But how does the company make money from it? What's the unit economics of one deployment? Who pays — the hospital, the insurer, or the patient? What's the reimbursement code?"
