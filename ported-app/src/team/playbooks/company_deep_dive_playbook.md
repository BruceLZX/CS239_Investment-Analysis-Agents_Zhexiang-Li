# Company Deep-Dive Playbook

Use this playbook for every company analysis. It raises the mandatory depth standard from "coverage" to "forensic detail." Every section must answer the deepening questions below. When information is unavailable, state it explicitly and explain what data would be needed and how it affects confidence.

This playbook is mandatory for all company types. For public equities, some sections (equity structure, financials) will have richer data sources; for early-stage startups, some sections will require more effort to source.

## The Granularity Benchmark

Professional investment analysis is defined by **specificity**, not length. A 200-page report that uses vague language is worse than a 50-page report where every claim has a number attached. The following standards are non-negotiable:

### Numbers Must Be Precise
- ❌ "approximately 45%" → ✅ "43.1373%" or "43.1%" (state source and confidence)
- ❌ "hundreds of patents" → ✅ "69 granted patents + 12 pending across US/CN/EP"
- ❌ "founded in 2023" → ✅ "2023-10-15" or "2023-10"
- ❌ "raised several hundred million" → ✅ "$75M Series B at $450M pre-money (2025-03-15)"
- ❌ "large facility" → ✅ "16,000 m², including GMP plants for Class II and III active medical devices"

### People Must Be Traceable
- ❌ "graduated from a well-known university" → ✅ "BS, University of Science and Technology of China, mechatronic engineering; MS, Hong Kong Polytechnic University, software engineering"
- ❌ "has worked at several companies" → ✅ each role: company + title + dates + specific achievements
- ❌ "industry veteran" → ✅ "69 peer-reviewed papers; previously head of clinical partnerships at Neuralink"
- Every founder bio must trace from undergraduate through highest degree
- Every key hire must have: institution + degree + year + prior employer + role + achievements

### Events Must Be Dated
- ❌ "recently completed funding" → ✅ "on 2026-06-26, phase 1 of the super factory was completed and began operating"
- ❌ "has partnerships with hospitals" → ✅ "joint laboratories with Huashan Hospital (Shanghai), Shanghai Mental Health Center and West China Hospital"
- ❌ "attended by investors" → ✅ "the ribbon cutting was attended by Ji Wei of Huaying Capital, Zhang Song of Qingsong Capital, Tang Qibo of Gobi Partners and Gu Jie of Fourier"

### If Data Is Unavailable
- State EXACTLY what is missing (e.g., "registered capital not disclosed" not "insufficient information")
- Explain how material the gap is to the investment decision
- List what source would resolve it (e.g., "needs the business registration file")
- NEVER fill the gap with vague language that sounds informative but conveys no data

---

## Section 1: Company Overview — Forensic Identity

### 1.1 Legal Entity Map

Map every legal entity in the corporate structure. This is not optional — investors must know exactly which entity they are investing in.

| Entity | Jurisdiction | Entity Type | Role | Ownership % | Ultimate Controller |
|--------|-------------|-------------|------|-------------|---------------------|
| [Holding Co] | Cayman/BVI | Ltd | IPO vehicle / top holding | 100% (top) | Founder(s) |
| [HK Co] | Hong Kong | Ltd | Intermediate holding | 100% by Holding Co | — |
| [WFOE] | Shanghai, China | Wholly foreign-owned enterprise | VIE anchor / operating license holder | 100% by HK Co | — |
| [VIE OpCo] | Beijing, China | Domestic limited company | Operating entity (holds ICP, licenses) | VIE controlled | Nominee shareholders |
| [Subsidiary 1] | [Location] | [Type] | R&D center | X% | — |
| [Subsidiary 2] | [Location] | [Type] | Sales entity | X% | — |

**Mandatory:**
- Distinguish VIE vs. non-VIE vs. red-chip architecture
- Identify which entity holds key licenses/assets/IP
- Flag nominee shareholder arrangements, contractual control gaps, and enforceability risk
- For public companies: specify listing venue, ticker, exchange, currency, shares outstanding, free float %

**If VIE architecture:**
- Who are the nominee shareholders? What is their relationship to the founder?
- What contracts bind the VIE (exclusive option, proxy, equity pledge, exclusive business cooperation)?
- Has any PRC court or arbitrator ruled on the enforceability of these specific VIE contracts?
- What happens to the VIE if the nominee shareholder dies, divorces, or goes bankrupt?

### 1.2 Complete Timeline

Build a timeline with **specific dates** (YYYY-MM or YYYY-MM-DD when available). Do not use "recently," "currently," or "soon."

| Date | Event | Significance | Source |
|------|-------|-------------|--------|
| YYYY-MM | Company founded by [Founder] at [Location] | Origin | [SX] |
| YYYY-MM | First product launched: [Product Name] | Product proof | [SX] |
| YYYY-MM | Series A: $X million at $Y valuation, led by [Investor] | Financing milestone | [SX] |
| YYYY-MM | Key hire: [Name] joined as [Role] from [Prior Company] | Team building | [SX] |
| YYYY-MM | FDA/CE/NMPA submission: [Product/Indication] | Regulatory milestone | [SX] |
| YYYY-MM | First paying customer / pilot launch | Commercial validation | [SX] |
| ... | ... | ... | ... |

**Minimum:** 8-15 dated milestones covering founding, product, financing, team, regulatory, commercial, and strategic events.

### 1.3 Equity & Cap Table

Build the most accurate cap table possible. Differentiate between **confirmed** (from filings, company disclosures) and **estimated** (from media, industry inference).

| Shareholder | Class | Shares | % Ownership | % Voting Rights | Investment Cost | Current Value (at latest round) | Return Multiple |
|-------------|-------|--------|-------------|-----------------|-----------------|--------------------------------|-----------------|
| Founder A | Ordinary / B-class (10:1) | X | ~45% | ~71% | $X | $X | Xx |
| Founder B | Ordinary | X | ~15% | ~12% | $X | $X | Xx |
| Investor 1 (Sequoia) | Preferred A | X | ~20% | ~8% | $X | $X | Xx |
| Investor 2 (Lightspeed) | Preferred B | X | ~10% | ~4% | $X | $X | Xx |
| ESOP (undistributed) | — | X | ~10% | 0% | — | $X | — |
| **Total** | | | **100%** | **100%** | | | |

**Mandatory:**
- **Share class breakdown**: ordinary vs. preferred, voting vs. non-voting, vested vs. unvested
- **Super-voting rights**: any founder with >50% voting power despite minority equity? Detail the mechanism.
- **Liquidation preferences**: multiple (1x, 1.5x, 2x), participating vs. non-participating, seniority stack
- **Anti-dilution**: full ratchet vs. weighted average
- **ESOP**: total pool size, allocated vs. unallocated, annual refresh rate
- **Drag-along / tag-along / ROFR / co-sale**: which investors have these rights?
- **Redemption rights**: any put options or mandatory redemption triggers?
- **Board seats**: who holds them? Founder-controlled, investor-controlled, or independent majority?
- **Protective provisions / veto rights**: what decisions require investor consent?

**If information is unavailable:** State which items are unknown and how material they are. For a pre-IPO company, the absence of liquidation preference data is highly material.

---

## Section 2: Founding Team & Core Personnel — Complete CVs

### 2.1 Per-Person Deep Dive

For **each** founder, C-suite executive, and key technical leader (VP-level and above), provide:

#### Template:

```
### [Name] — [Title/Role]

**Basic Information:**
- Born: [YYYY] (or approximate age: [X] years old)
- Nationality: [Country]
- Current Location: [City, Country]
- Joined Company: [YYYY-MM]

**Education:**
| Degree | Institution | Year | Thesis/Research Focus |
|--------|------------|------|----------------------|
| Ph.D., [Field] | [University], [Country] | YYYY | "[Thesis Title]" |
| M.S., [Field] | [University], [Country] | YYYY | — |
| B.S., [Field] | [University], [Country] | YYYY | — |

**Career Chronology:**
| Period | Company/Institution | Role | Key Achievements | Departure Reason |
|--------|-------------------|------|-----------------|-----------------|
| YYYY-YYYY | [Company A] | [Role] | [Specific achievement with quantifiable metrics] | [Why left] |
| YYYY-YYYY | [Company B] | [Role] | [Specific achievement] | [Why left] |
| YYYY-present | Current Company | [Role] | — | — |

**Key Accomplishments & Credentials:**
- Patents: [N] granted/pending. Key patent: [Patent #] — "[Title]" ([date])
- Publications: [N] peer-reviewed papers in [journals]. Most cited: "[Title]" ([citations])
- Awards/Honors: [List with years]
- Board seats / Advisory roles: [List]
- Prior exits: [Company] acquired by [Acquirer] for $[X] in [YYYY]; [founder's personal outcome]
- Speaking engagements: Keynote at [Conference] ([Year])
- Industry recognition: [e.g., Forbes 30 Under 30, IEEE Fellow]

**Relevance to Current Venture:**
- Why this person is uniquely qualified: [Specific skill/experience match to company's challenge]
- What gap they fill on the team: [Technical/commercial/operational]
- Network value: [Key relationships in industry/regulatory/customer ecosystem]

**Compensation (if available):**
- Salary: $[X]
- Equity: [X]% (vested/unvested schedule)
- Special terms: [sign-on bonus, relocation, etc.]

**Risk Factors:**
- Key-person dependency: [Criticality level: High/Medium/Low]
- Retention risk: [Compensation competitiveness, vesting schedule, reported satisfaction]
- Health/age considerations: [If material]
```

### 2.2 Team Assessment Matrix

| Dimension | Founder A | Founder B | CTO | CFO | Team Average |
|-----------|-----------|-----------|-----|-----|-------------|
| Technical depth | 9/10 | 7/10 | 9/10 | — | — |
| Industry experience (years) | 15 | 12 | 20 | 25 | — |
| Startup experience (prior exits) | 2 | 1 | 0 | 3 | — |
| Leadership / scaling experience | 7/10 | 6/10 | 5/10 | 9/10 | — |
| Fundraising track record | 8/10 | — | — | — | — |
| Key-person dependency | High | Medium | High | Low | — |
| Retention risk | Low | Medium | Medium | Low | — |

### 2.3 Founder Reference Check Framework

For primary-market deals, flag what a reference check should verify:

- Prior colleagues at [Company X]: Verify claimed role scope, leadership style, technical contribution
- Prior investors: Verify exit outcome, integrity, resilience under pressure
- Industry peers: Verify reputation, technical competence, deal-making fairness
- Public records: Verify education claims, patent inventorship, litigation history

---

## Section 3: Technology & IP — Patent-Level Detail

### 3.1 Core Technology Inventory — Academic-Level Deep Dive

**This is the most important section of the report.** Professional investment teams spend >40% of their research time on technology depth. The technology section must read like a well-researched survey paper, not a marketing brochure.

#### 3.1.1 Technology Mechanism — How It Actually Works

For EACH core technology, explain the mechanism in accessible but technically precise language. The reader should understand the underlying physics/biology/chemistry, not just what the product does.

**Mandatory structure for each technology:**

```
### Technology: [Name]

**1. Mechanism of Action (MOA) — The Physics/Biology**
[Explain in 5-10 sentences the underlying scientific principle. Use the actual physics/biology terms.
e.g., NOT "ultrasound stimulates the brain" BUT "transcranial focused ultrasound (tFUS) fires several ultrasound beams from a phased-array transducer that
form an interference focus at a chosen point inside the skull, where the mechanical (not thermal) effect modulates neuron membrane potential. The focus is ~2-3 mm³,
spatial resolution is sub-millimeter, and it passes through the intact skull with no craniotomy."]

**2. Key Performance Metrics**
| Metric | Value | Measurement Method | Source |
|--------|-------|-------------------|--------|
| Spatial resolution | Sub-millimeter (~0.5mm) | [How measured] | [Paper/Source] |
| Temporal resolution | 0.5-1.5s latency | [How measured] | [Paper/Source] |
| Brain coverage | 25% of whole-brain volume | [How measured] | [Paper/Source] |
| Penetration depth | Transcranial (skull intact) | [How measured] | [Paper/Source] |
| Energy efficiency | [X W/cm²] | [How measured] | [Paper/Source] |

**3. Academic & Clinical Evidence**
- Key papers: [Author(s), Title, Journal, Year, DOI if available]
- Total relevant publications in this field: [N] papers on PubMed
- Key finding 1: [What the seminal paper proved]
- Key finding 2: [What the most recent breakthrough is]
- Clinical evidence level: [Animal studies / First-in-human / RCT Phase I/II/III]

**4. Competitive Technical Approaches (Same Mechanism Level)**
For EACH major competing technical approach, provide the SAME level of mechanism detail:

| Technical Dimension | Our Technology | Neuralink (electrode) | Synchron (stentrode) | Blackrock (Utah array) |
|---------------------|---------------|----------------------|---------------------|------------------------|
| Physical principle | [e.g., mechanical effect of ultrasound] | [e.g., microelectrodes recording electric fields] | [e.g., endovascular electrodes] | [e.g., epidural electrode array] |
| Invasiveness | Non-invasive (transcranial) | Invasive (craniotomy implant) | Semi-invasive (endovascular) | Invasive (craniotomy implant) |
| Channel count | [N] (equivalent) | 1024 | 16-128 | 96-256 |
| Brain coverage | 25% of whole brain | 1.3‰ of cortex | Local, around the vessel | 1-2 mm² of cortex |
| Spatial resolution | Sub-millimeter | Single neuron (50μm) | Millimeter | Micrometer (single neuron) |
| Signal type | Indirect, blood flow (metabolic) | Direct, electric field (electrophysiology) | Direct, electric field (electrophysiology) | Direct, electric field (electrophysiology) |
| Surgical requirement | None | Craniotomy | Endovascular surgery | Craniotomy |
| FDA/NMPA status | [Status] | FDA HDE 2024 | FDA IDE 2023 | FDA IDE 2017 |

**5. Technology Evolution & Roadmap**
- Generation 1: [Current capability, year achieved]
- Generation 2: [Next milestone, target year]
- Generation 3: [Long-term vision, target year]
- Key bottleneck to overcome: [The single hardest unsolved problem]
- Who else is trying to solve it: [Research groups, competitors, open-source projects]

**6. Key Debates in the Field**
- Debate 1: [e.g., invasive vs non-invasive: which route wins in the end?]
  - Pro-invasive argument: [with evidence]
  - Pro-noninvasive argument: [with evidence]
  - Our assessment: [which is more likely and why]
- Debate 2: [Another major controversy in the field]

**7. Academic Literature Search Protocol**
For technology companies, the analyst MUST:
- Search PubMed/Google Scholar for: "[technology name] mechanism", "[technology name] clinical", "[technology name] review"
- Search arXiv for: "[technology name]" (for AI/engineering)
- Open and read at least 3-5 key papers' abstracts; 1-2 full papers for the most important ones
- Cite at least 2 specific papers with author, title, journal, year
- Compare company's claimed metrics against published literature benchmarks
```

#### 3.1.2 Technology Moat Assessment

Go beyond "strong IP" and analyze WHY the technology is hard to replicate:

```
**Replication Difficulty Assessment:**

| Barrier | Difficulty (1-10) | Why | Time to Replicate (Est.) |
|---------|------------------|-----|-------------------------|
| Scientific/Physics barrier | [X] | [Explanation — what law of physics or biology makes this hard] | — |
| Engineering barrier | [X] | [Explanation — what manufacturing/integration challenge exists] | [X] years |
| Data barrier | [X] | [Explanation — what proprietary data is needed] | [X] years |
| Regulatory barrier | [X] | [Explanation — what certification/approval creates moat] | [X] years |
| Ecosystem barrier | [X] | [Explanation — what partner/customer lock-in exists] | [X] years |
| **Composite Moat Score** | **[X]/10** | | **Minimum [X] years of lead time** |
```

**The replication test:** "If a well-funded team of 50 world-class engineers and scientists were given unlimited resources and all of this company's published patents, how long would it take them to build a competitive product?" This is the most honest measure of technology moat.

### 3.2 Patent Portfolio

Build a patent table with as much specificity as possible:

| Patent/App # | Title | Type | Jurisdiction | Filing Date | Grant Date | Expiry | Legal Status | Relevance |
|-------------|-------|------|-------------|-------------|------------|--------|-------------|----------|
| US 12,345,678 | "[Title]" | Invention | US | 2023-06-15 | 2025-01-20 | 2043-06-15 | Granted | Core platform |
| CN 202310123456.7 | "[Title]" | Utility Model | CN | 2023-03-01 | 2023-12-10 | 2033-03-01 | Granted | Manufacturing process |
| PCT/CN2024/XXXXXX | "[Title]" | PCT | WIPO | 2024-02-01 | — | — | Pending (national phase) | International filing |
| EP 24XXXXXX.X | "[Title]" | Invention | EP | 2024-05-01 | — | — | Under examination | EU market entry |

**Patent Analysis:**
- Total patents: [N] (granted) + [M] (pending) = [N+M] total
- By type: [X] invention patents, [Y] utility models, [Z] design patents
- By jurisdiction: US [X], China [Y], EU [Z], PCT [W], Others [V]
- Quality indicators: Average forward citations per patent, % granted vs. filed, geographic coverage breadth
- Key pending applications to watch: [List with expected decision dates]
- Freedom-to-operate risk: [Any known third-party patents that could block commercialization]
- Patent litigation/opposition history: [Past or ongoing disputes]

### 3.3 Technology vs. Competitor Comparison

| Technology Dimension | Company | Competitor A | Competitor B | Industry Benchmark |
|---------------------|---------|-------------|-------------|-------------------|
| [Dimension 1] | [Spec] | [Spec] | [Spec] | [Reference] |
| [Dimension 2] | [Spec] | [Spec] | [Spec] | [Reference] |
| IP protection depth | [Assessment] | [Assessment] | [Assessment] | — |
| Time-to-replicate estimate | [X years] | — | — | — |

---

## Section 4: Products — Per-Product Forensic Detail

### 4.1 Product Inventory & Lifecycle

| Product | Stage | Launch Date | 2025 Revenue | % of Total | Gross Margin | Next Milestone |
|---------|-------|-------------|-------------|------------|-------------|----------------|
| [Product 1] | Commercial | YYYY-MM | $X | X% | X% | [Milestone] |
| [Product 2] | Clinical Phase II | — | $0 | 0% | — | Phase II data YYYY-QQ |

### 4.2 Per-Product Deep-Dive (Healthcare/Biotech Example)

For **each** product, provide a complete analysis. The healthcare/biotech template below is mandatory for medical companies. Adapt the "Indication → Current Treatments → Competitor Products" structure for other industries (e.g., for SaaS: "Workflow → Current Solutions → Competitor Tools").

#### Healthcare/Biotech Product Deep-Dive Template:

```
### Product: [Product Name / Drug Name / Device Name]

**Product Type:** [Drug (small molecule / biologic / RNA / gene therapy) / Medical Device (Class I/II/III) / Diagnostic / Digital Therapeutic]

**Target Indication(s):**
- Primary indication: [Disease/Condition] — ICD-11 code: [code]
- Prevalence: [X] patients in [Country/Global] ([source])
- Incidence: [X] new cases/year
- Patient segmentation: [by severity, genotype, line of therapy, etc.]

**Current Standard of Care:**
| Treatment | Mechanism | Efficacy | Limitations | Cost/Year | Reimbursement Status |
|-----------|----------|----------|-------------|-----------|---------------------|
| [Current Drug/Surgery/Therapy 1] | [MOA] | [Response rate, PFS, OS, etc.] | [Side effects, resistance, cost, convenience] | $X | [NRDL/Medicare/Private] |
| [Current Drug/Surgery/Therapy 2] | [MOA] | [Data] | [Limitations] | $X | [Status] |
| **This Product** | [MOA] | [Data] | [Limitations] | $X | [Status] |

**Clinical Data Summary:**
| Trial Name/Phase | N | Endpoint | Result | Statistical Significance | Publication |
|-----------------|---|----------|--------|------------------------|------------|
| [Trial] Phase III | [N] | [Primary endpoint] | [Result] | p=[X] | [Journal, Date] |

**Competing Products in Development (Same Indication):**
| Company | Product | Stage | Mechanism | Differentiator vs. Our Product |
|---------|---------|-------|-----------|-------------------------------|
| [Competitor 1] | [Product X] | Phase II | [MOA] | [Advantage/Disadvantage] |
| [Competitor 2] | [Product Y] | Preclinical | [MOA] | [Advantage/Disadvantage] |

**Regulatory Path:**
- Designation: [Breakthrough Therapy / Fast Track / Orphan Drug / PRIME / SAKIGAKE / None]
- Current regulatory status: [Pre-IND / IND filed / Phase I/II/III / NDA/BLA submitted / Approved]
- Expected approval date: [YYYY-MM or range]
- Key regulatory risk: [CMC issue / clinical data sufficiency / comparator choice / endpoint acceptability]

**Commercial Assessment:**
- Target addressable patients: [X] per year in [Country/Region]
- Pricing strategy: [Price point] vs. comparator at [Price point]
- Reimbursement strategy: [NRDL negotiation timeline / Medicare coverage / private insurance]
- Peak sales estimate: $[X]B in [Year], driven by [Key assumptions]
- Sales force requirement: [X] reps, [Y] MSLs
- Manufacturing: [In-house vs. CMO], [capacity], [COGS estimate]
```

#### SaaS/Enterprise Product Template:

Adapt the same structure for non-medical products:

```
### Product: [Product Name]

**What It Does:** [2-3 sentence description of core function]

**Target Customer:**
- Buyer persona: [Title/Department]
- Company size: [Revenue range / employee count]
- Industry verticals: [List]

**Customer's Current Workflow (Before This Product):**
1. [Step 1 — manual/spreadsheet/FTP/email]
2. [Step 2]
3. [Step 3]

**Customer's Workflow (With This Product):**
1. [Step 1 — automated/consolidated in platform]
2. [Step 2]

**Competitive Alternatives:**
| Solution | Type | Pricing | Strengths vs. Our Product | Weaknesses vs. Our Product |
|----------|------|---------|--------------------------|---------------------------|
| [Competitor Product] | [Direct/Indirect/Internal Build] | $[X]/seat/mo | [Strength] | [Weakness] |
| [Manual/Spreadsheet] | [Status Quo] | [Labor cost] | [Strength] | [Weakness] |

**Pricing & Unit Economics:**
- Pricing model: [Per seat / per usage / per transaction / tiered]
- ASP: $[X]/year
- ACV (annual contract value): $[X]
- Implementation/deployment time: [X] weeks
- Training requirement: [X] days
- Customer onboarding cost: $[X]

**Customer Evidence:**
- Logo count: [X] paying customers
- Key reference customers: [Name] ([Industry], [Use Case])
- NPS score: [X] ([source])
- Gross retention: [X]%
```

---

## Section 5: Market — Domestic + International Bifurcation

### 5.1 Mandatory Market Bifurcation

For **every** company, separately analyze:

#### Domestic Market (Company's Home Country)
- Market size: TAM/SAM/SOM
- Growth rate: 3Y/5Y CAGR
- Key demand drivers (domestic-specific)
- Regulatory environment
- Competitive landscape (domestic players only)
- Customer characteristics specific to domestic market
- Pricing dynamics

#### International Market — by Region

| Region | Market Size | Growth Rate | Company's Position | Regulatory Barriers | Key Competitors |
|--------|------------|-------------|-------------------|-------------------|-----------------|
| **US/North America** | $X B (YYYY) | X% CAGR | [Entered/Planned/Blocked] | [FDA, CFIUS, tariffs] | [List] |
| **EU/EEA** | $X B (YYYY) | X% CAGR | [Status] | [CE/MDR, GDPR, EU AI Act] | [List] |
| **China** (if company is non-Chinese) | $X B (YYYY) | X% CAGR | [Status] | [NMPA, CAC, localization req] | [List] |
| **Japan/Korea** | $X B (YYYY) | X% CAGR | [Status] | [PMDA, MFDS] | [List] |
| **Southeast Asia** | $X B (YYYY) | X% CAGR | [Status] | [Country-specific] | [List] |
| **Middle East/Africa** | $X B (YYYY) | X% CAGR | [Status] | [Country-specific] | [List] |
| **Latin America** | $X B (YYYY) | X% CAGR | [Status] | [ANVISA, etc.] | [List] |

### 5.2 Cross-Border Considerations

For each international market the company operates in or plans to enter:

- Localization requirements (language, regulatory, certification)
- IP protection landscape (patent enforceability, trade secret risk)
- FX exposure and hedging
- Local partnership/JV requirements
- Cultural/market differences affecting GTM

---

## Section 6: Competition — Per-Product Forensic Mapping

**CRITICAL: Competition is per-product, NOT per-company. A company with 4 products faces 4 DIFFERENT competitive landscapes.** Lumping all competitors into one table under "the company competes with Medtronic and Abbott" is analytically useless — Medtronic's DBS for Parkinson's does NOT compete with a non-invasive tibial nerve stimulator for OAB. The analyst MUST build a separate competitive landscape for EACH product.

### 6.0 Pre-Draft Gate: Per-Product Competitor Identification

Before writing the competition section, the analyst must:

1. List every product the company has (commercial, clinical, preclinical, R&D)
2. For EACH product, search: "[product category] competitors", "[specific indication] treatment options", "[product type] FDA approved", "[product type] NMPA approved"
3. Search PubMed/ClinicalTrials.gov: "[indication] [technology type]" to find ALL clinical-stage competitors
4. Search government procurement databases for the specific product category
5. Search patent databases for competitive filings in the specific technology area
6. Do NOT combine competitors across products — build separate competitor maps

### 6.1 Per-Product Competitor Database Template

For EACH product, build this table:

```
### Product: [Product Name] — [Indication]

#### Direct Competitors (Same Indication, Same Technology Route)

| Competitor | Product Name | Technology | Regulatory Status | Efficacy Data | Price | Market Share | Strengths vs Us | Weaknesses vs Us |
|-----------|-------------|-----------|-------------------|---------------|-------|-------------|-----------------|-----------------|
| [A] | [X] | [Approach] | FDA/NMPA [status] | [Key clinical result] | $[X] | [X]% | [Why they win] | [Where we win] |

#### Indirect Competitors (Same Indication, Different Technology)

| Competitor | Product/Approach | Technology Route | Why Customers Choose This Instead |
|-----------|-----------------|-----------------|----------------------------------|
| [Current Standard of Care] | [Drug/Surgery/Device] | [Pharma/Surgical/Behavioral] | [Reason for preference] |

#### Pipeline Competitors (Same Indication, Clinical/Preclinical Stage)

| Company | Product | Stage | Key Differentiator | Expected Launch | Threat Level |
|---------|---------|-------|-------------------|----------------|-------------|
| [Name] | [X] | Phase [I/II/III] | [Advantage] | [Year] | [High/Med/Low] |

#### Status Quo / "Do Nothing" Competitor

- What patients currently do: [describe current standard of care, including "just live with it" for untreated conditions]
- Why they don't adopt existing solutions: [cost, invasiveness, side effects, lack of access]
- What would make them switch: [our product's specific advantage]
```

### 6.2 Example: Fuyuan Shuke Per-Product Competition (Illustrative)

**Product 1: CSNS (SCI Cervical Stimulation)**
- Direct competitors: ARCEX (ONWARD Medical, Swiss), ExaStim (GTX Medical, Netherlands), TESCoN device (various academic)
- NOT competitors: Medtronic Intellis SCS (different approach—invasive, different indication—pain, different patient segment—lumbar)
- Pipeline: NCT07361627 (Montreal), NCT07423949 (UBC), NCT07334977 (France)

**Product 2: Jingxiang™ TNS (OAB Tibial Nerve Stimulation)**
- Direct competitors: Urgent PC (Laborie, percutaneous PTNS), eCoin (Valencia Technologies, implantable), RENOVA (Stimwave, implantable), TENSmini (academic wearable)
- NOT competitors: Medtronic InterStim (sacral, not tibial; invasive, not transcutaneous), Axonics (sacral, implantable)
- Indirect: Anticholinergics (tolterodine, solifenacin), β3-agonists (mirabegron), Botox injections

**Product 3: PNS (VTE Neuromuscular Stimulation)**
- Direct competitors: geko (Firstkind, UK), VenaPulse (various), traditional IPC devices (Covidien, Cardinal Health)
- NOT competitors: Eliquis/Xarelto (anticoagulant drugs — different mechanism, complementary not competing)

**Product 4: OSA Hypoglossal Nerve Stimulator (R&D)**
- Direct competitors: Inspire (Inspire Medical Systems, FDA approved), Genio (Nyxoah, CE mark), aura6000 (LivaNova, clinical)
- NOT competitors: CPAP machines (ResMed, Philips — different technology route, first-line not surgical)

### 6.3 Competitive Positioning Map (Per Product)

For EACH product, create a separate positioning map:

| | Market Leader | Strong Challenger | Niche Player | Emerging Threat |
|---|---|---|---|---|
| **Product 1: [Name]** | [Company/Product] | [Company/Product] | [Company/Product] | [Company/Product] |
| **Product 2: [Name]** | [DIFFERENT Company] | [DIFFERENT Company] | — | [DIFFERENT Company] |

**Do not fill the same companies into every product row. If they appear in multiple rows, justify why.**

### 6.4 Source Authority Requirements for Competition Analysis

For each competitor identified, the analyst MUST cite at least ONE authoritative source:
- Company's own website/IR page (product description, indications, regulatory status)
- FDA/NMPA regulatory database (approval status, device classification)
- ClinicalTrials.gov registration (trial phase, endpoints, enrollment)
- Published clinical data (PubMed-indexed paper with sample size and results)
- Company filings (10-K, prospectus, annual report for public companies)
- Patent database (for technology comparison)

**Prohibited:** Using only media summaries or aggregator sites to describe competitors. "According to a 36Kr article" is insufficient for competitor product specifications.

## Section 7: Financials — Forensic Detail

### 7.1 Income Statement Deep-Dive

Go beyond top-line revenue:

- Revenue by product line / segment / geography (in percentages and absolute)
- Revenue by customer type (enterprise vs. SMB, hospital vs. clinic, etc.)
- Revenue quality: recurring vs. one-time, organic vs. acquired, reported vs. adjusted
- Gross margin by product line (not just blended)
- Operating expense breakdown: R&D / S&M / G&A as % of revenue, trend over 3+ years
- Stock-based compensation: as % of revenue, dilution rate
- Customer acquisition cost (CAC) trend
- Customer lifetime value (LTV)
- Payback period on CAC

### 7.2 Detailed Unit Economics

Break down the economics of a single transaction/customer:

```
Unit Economics — [Product/Service]:

Revenue per unit/customer:   $[X]
- COGS (direct materials):   ($[X])
- COGS (direct labor):       ($[X])
- Shipping/Fulfillment:      ($[X])
= Gross Profit per unit:     $[X]  ([X]% margin)
- CAC (sales + marketing):   ($[X])
- Onboarding/Installation:   ($[X])
- Ongoing support (annual):  ($[X])
= Net Profit per unit (Y1):  $[X]
LTV (3-year):               $[X]
LTV:CAC ratio:              [X]:1
CAC payback period:          [X] months
```

### 7.3 Balance Sheet Health

- Cash + equivalents
- Debt: total, current vs. long-term, interest rate, maturity schedule, covenants
- Net cash/debt position
- Working capital: receivables days, inventory days, payables days, cash conversion cycle
- Off-balance-sheet items: operating leases, purchase commitments, contingent liabilities
- Goodwill and intangibles as % of total assets

---

## Data Sources & Evidence Hierarchy

When filling the above sections, prioritize:

1. **Company filings** (10-K, 10-Q, prospectuses, annual reports, business registrations) — highest confidence
2. **Regulatory databases** (FDA, NMPA, CDE, ClinicalTrials.gov, SEC EDGAR, CNINFO, HKEXnews)
3. **Patent databases** (USPTO, CNIPA, WIPO Patentscope, Google Patents)
4. **Government procurement records** (ccgp.gov.cn, SAM.gov)
5. **Industry reports** (IDC, Gartner, Frost & Sullivan, EvaluatePharma, IQVIA)
6. **Academic publications** (PubMed, Google Scholar, arXiv)
7. **Company-provided materials** (pitch deck, IR presentations, product pages)
8. **Media/interviews** — lowest confidence

**For each data point**, cite the specific source, date, and confidence level.

---

## Section-Specific Granularity Benchmarks (All Sections)

These benchmarks are derived from professional investment team analysis reports. Every section must hit these minimum specificity markers. The QA gate (`check_depth.py`) enforces them.

### S1 Company Overview
- ✅ "founded 2025-09-05" not "founded in 2025"
- ✅ "registered capital RMB 12.75 million, paid-in capital not disclosed" not "registered capital not disclosed"
- ✅ "Peng Lei holds 43.1373%, Chen Tianqiao holds 19.6078%" not "the founder holds about 40%"
- ✅ "Two headquarters: Chengdu Tianfu International Bio-Town (global headquarters, 16,000 m²) and the Shanghai Brain Intelligence Park"
- ✅ "On 2026-06-26, phase 1 of the super factory was completed and began operating; investor representatives Ji Wei (Huaying Capital), Zhang Song (Qingsong Capital), Tang Qibo (Gobi Partners) and Gu Jie (Fourier) attended the ribbon cutting"
- ✅ Entity map: parent/HK WFOE/VIE OpCo with EXACT ownership chain

### S2 Team
- ✅ Full education trace: "BS, USTC, mechatronic engineering; MS, Hong Kong Polytechnic University, software engineering; PhD candidate, Fudan University, brain-inspired intelligence"
- ✅ Career chronology with exact titles and company names: "founder and CEO of SaaS company Keruyun → senior vice president, Alibaba Local Services → sixth startup"
- ✅ Key hires: "Bashar W. Badran, Ph.D.: PhD in neuroscience, Medical University of South Carolina; founded the MUSC Neuro-X lab; 69 peer-reviewed papers; previously head of clinical partnerships at Neuralink"
- ✅ External validation: "Sichuan Thousand Talents Program entrepreneurial leader", "committed a further RMB 1 billion to AI and brain science in 2023"

### S3 Technology & IP
- ✅ Technical mechanism deep-dive: "ultrasound blood-flow imaging latency of 0.5-1.5s (near real time)", "sub-millimeter spatial resolution"
- ✅ Direct technical comparison: "Neuralink's 1,024-channel electrodes cover 1.3‰ of the cortex vs the ultrasound route's 25% of whole-brain volume"
- ✅ Patent table with EXACT numbers: "CN119345607A" not "multiple patents"
- ✅ Technology readiness: "a phased array (phase-controlled array) ... electronic scanning, unlike a traditional single probe"
- ✅ Mechanism explained in accessible but precise terms, with quantified performance metrics

### S4 Market
- ✅ TAM broken down by indication: "SCI RMB 15B (3.74M existing patients + 100K new a year); OAB RMB 20B (20M target patients × ¥1,000 each); VTE RMB 15B (50M surgical patients × ¥300 each); OSA RMB 10B (2030 forecast, CAGR 19.7%)"
- ✅ Global market with CAGR and source: "Global neuromodulation market $6.8B (2025) → $13.9B (2033), CAGR 10.4%, Grand View Research"
- ✅ Policy timeline with specific documents: "the 2026 Government Work Report names brain-computer interfaces for the first time; the seven ministries' Implementation Opinions on Promoting Innovative Development of the Brain-Computer Interface Industry; one of six priority industries in the 15th Five-Year Plan"
- ✅ Geographic bifurcation: China market vs global, with separate data

### S5 Competition
- ✅ Named competitors with technical comparison: "Medtronic (global leader in invasive DBS/SCS, $100K+ a unit) vs Fuyuan Shuke (non-invasive, ¥20-30K a unit, 1/50 of the price)"
- ✅ Not "fierce competition" but specific: "the giants' invasive therapies reach under 1% of patients; we target the other 99%"
- ✅ Competitive moat quantified: "50+ IP filings, 5 PCT applications and a national-level novelty search certifying 'first in China, internationally leading'"
- ✅ Direct product-by-product comparison table

### S6 Business Model
- ✅ Dual-engine strategy clearly articulated: "a cash-flow product line (certified, self-funding) plus a core innovation line (first in China, the valuation anchor)"
- ✅ Pricing: "device ¥20-30K plus consumables ¥300 a set; ¥10 a treatment; 1/50 of the invasive price"
- ✅ Unit economics: "RMB 1M+ revenue already; break-even target 2028"

### S7 Financials
- ✅ Actual revenue: "RMB 1M+ of high-tech services and product revenue realized" not "has revenue"
- ✅ Financing history with EXACT details: "Angel round RMB 150M (2026-03-12, co-led by Guosheng Capital and Daotong Investment) → Angel+ round RMB 420M (2026-07-03, led by Huaying Capital, with HongShan, C Capital and Lens Technology following and existing shareholders over-subscribing)"
- ✅ ALL investors named, not "several institutions"
- ✅ Fund usage specified per round

### S8 Funding
- ✅ Complete financing table: Date | Round | Total raised | Investors (ALL named) | Use of funds
- ✅ Cumulative: "2 rounds, RMB 570M raised in total"
- ✅ Investor quality assessment: named VCs with track record

### S9 Strategy & Partnerships
- ✅ Named partners with collaboration scope: "Fourier: lower-limb exoskeleton, upper-limb rehabilitation and the GR-3 humanoid robot, closed-loop 'intent-execution-sensory feedback' training"
- ✅ "signed the strategic cooperation agreement on 2026-01-28" — exact date
- ✅ Clinical partners: "West China, Peking Union and Huashan, among other top-tier hospitals" — named institutions
- ✅ Roadmap with dates: "multi-center clinical trial starts 2026 Q3"

### S10 Risk
- ✅ Specific risks tied to milestones: not "clinical risk" but "if the CSNS multi-center trial shows no benefit over sham stimulation, the valuation anchor collapses (-50% EV)"
- ✅ Probability attached: "30% probability, fatal level"
- ✅ Early warning signal: "2026 Q3-Q4 sales keep falling short of expectations"
- ✅ Mitigation plan: "cash-flow products keep the company running; it can focus on pipelines with easier trials such as OAB and OSA"

### S11 Investment Thesis
- ✅ Non-consensus insight with data: "the market assumes non-invasive means low barriers, but a national-level novelty certification, 50+ IP filings, 5 PCT applications and 2 certificates are very rare at the angel stage"
- ✅ Bull/Base/Bear with specific revenue/probability
- ✅ Exit path with named acquirers: "strategic acquisition by Medtronic, Abbott, PINS Medical or Mindray" not "IPO or M&A"

### S14 Scoring
- ✅ Weighted score table with specific rationale per dimension
- ✅ Key assumption sensitivity: ranked, with disproof trigger and EV impact %
- ✅ Position sizing: Kelly framework with portfolio correlation and max loss
