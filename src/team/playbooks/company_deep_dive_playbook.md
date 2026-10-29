# Company Deep-Dive Playbook

Use this playbook for every company analysis. It raises the mandatory depth standard from "coverage" to "forensic detail." Every section must answer the deepening questions below. When information is unavailable, state it explicitly and explain what data would be needed and how it affects confidence.

This playbook is mandatory for all company types. For public equities, some sections (equity structure, financials) will have richer data sources; for early-stage startups, some sections will require more effort to source.

## The Granularity Benchmark

Professional investment analysis is defined by **specificity**, not length. A 200-page report that uses vague language is worse than a 50-page report where every claim has a number attached. The following standards are non-negotiable:

### Numbers Must Be Precise
- ❌ "approximately 45%" → ✅ "43.1373%" or "43.1%" (state source and confidence)
- ❌ "hundreds of patents" → ✅ "69 granted patents + 12 pending across US/CN/EP"
- ❌ "founded in 2023" → ✅ "2023年10月15日" or "2023年10月"
- ❌ "raised several hundred million" → ✅ "$75M Series B at $450M pre-money (2025-03-15)"
- ❌ "large facility" → ✅ "16,000平方米，含二类/三类有源医疗器械GMP厂房"

### People Must Be Traceable
- ❌ "毕业于知名大学" → ✅ "本科 中国科学技术大学 机械电子工程；硕士 香港理工大学 软件工程"
- ❌ "曾在多家公司工作" → ✅ each role: company + title + dates + specific achievements
- ❌ "行业资深人士" → ✅ "69篇同行评审论文；曾任职于Neuralink担任临床合作负责人"
- Every founder bio must trace from undergraduate through highest degree
- Every key hire must have: institution + degree + year + prior employer + role + achievements

### Events Must Be Dated
- ❌ "recently completed funding" → ✅ "2026年6月26日，超级工厂一期竣工投运"
- ❌ "has partnerships with hospitals" → ✅ "与上海华山医院、上海市精神卫生中心、华西医院共建联合实验室"
- ❌ "attended by investors" → ✅ "华映资本季薇、清松资本张松、戈壁创投唐啟波、傅利叶顾捷出席剪彩"

### If Data Is Unavailable
- State EXACTLY what is missing (e.g., "注册资本未公开" not "信息不足")
- Explain how material the gap is to the investment decision
- List what source would resolve it (e.g., "需查阅工商登记档案")
- NEVER fill the gap with vague language that sounds informative but conveys no data

---

## Section 1: Company Overview — Forensic Identity

### 1.1 Legal Entity Map

Map every legal entity in the corporate structure. This is not optional — investors must know exactly which entity they are investing in.

| Entity | Jurisdiction | Entity Type | Role | Ownership % | Ultimate Controller |
|--------|-------------|-------------|------|-------------|---------------------|
| [Holding Co] | Cayman/BVI | Ltd | IPO vehicle / top holding | 100% (top) | Founder(s) |
| [HK Co] | Hong Kong | Ltd | Intermediate holding | 100% by Holding Co | — |
| [WFOE] | Shanghai, China | 外商独资企业 | VIE anchor / operating license holder | 100% by HK Co | — |
| [VIE OpCo] | Beijing, China | 内资有限公司 | Operating entity (holds ICP, licenses) | VIE controlled | Nominee shareholders |
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
e.g., NOT "ultrasound stimulates the brain" BUT "经颅聚焦超声(tFUS)通过相控阵换能器发射多束超声波，
在颅内特定位置形成干涉焦点，产生机械力效应(非热效应)调控神经元膜电位。焦点尺寸~2-3mm³，
空间分辨率达亚毫米级别，可穿透完整颅骨，无需开颅手术。"]

**2. Key Performance Metrics**
| Metric | Value | Measurement Method | Source |
|--------|-------|-------------------|--------|
| Spatial resolution | 亚毫米级(~0.5mm) | [How measured] | [Paper/Source] |
| Temporal resolution | 0.5-1.5s延迟 | [How measured] | [Paper/Source] |
| Brain coverage | 25%全脑体积 | [How measured] | [Paper/Source] |
| Penetration depth | 经颅(颅骨完整) | [How measured] | [Paper/Source] |
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
| Physical principle | [e.g., 超声波机械效应] | [e.g., 微电极记录电场] | [e.g., 血管内电极] | [e.g., 硬膜外电极阵列] |
| Invasiveness | 非侵入(经颅) | 侵入(开颅植入) | 半侵入(血管介入) | 侵入(开颅植入) |
| Channel count | [N] (等效) | 1024 | 16-128 | 96-256 |
| Brain coverage | 25%全脑 | 1.3‰皮层 | 局部血管周围 | 1-2mm²皮层 |
| Spatial resolution | 亚毫米 | 单神经元(50μm) | 毫米级 | 微米级(单神经元) |
| Signal type | 血流间接(代谢) | 电场直接(电生理) | 电场直接(电生理) | 电场直接(电生理) |
| Surgical requirement | 无 | 开颅手术 | 血管介入手术 | 开颅手术 |
| FDA/NMPA status | [Status] | FDA HDE 2024 | FDA IDE 2023 | FDA IDE 2017 |

**5. Technology Evolution & Roadmap**
- Generation 1: [Current capability, year achieved]
- Generation 2: [Next milestone, target year]
- Generation 3: [Long-term vision, target year]
- Key bottleneck to overcome: [The single hardest unsolved problem]
- Who else is trying to solve it: [Research groups, competitors, open-source projects]

**6. Key Debates in the Field**
- Debate 1: [e.g., 侵入式 vs 非侵入式 — 哪个路线最终胜出？]
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

### 6.2 Example: 复远数科 Per-Product Competition (Illustrative)

**Product 1: CSNS (SCI Cervical Stimulation)**
- Direct competitors: ARCEX (ONWARD Medical, Swiss), ExaStim (GTX Medical, Netherlands), TESCoN device (various academic)
- NOT competitors: Medtronic Intellis SCS (different approach—invasive, different indication—pain, different patient segment—lumbar)
- Pipeline: NCT07361627 (Montreal), NCT07423949 (UBC), NCT07334977 (France)

**Product 2: 胫享™ TNS (OAB Tibial Nerve Stimulation)**
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

1. **Company filings** (10-K, 10-Q, 招股书, 年报, 工商登记) — highest confidence
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
- ✅ "2025年9月5日成立" not "2025年成立"
- ✅ "注册资本1,275万人民币，实缴资本未公开" not "注册资本未公开"
- ✅ "彭雷持股43.1373%，陈天桥持股19.6078%" not "创始人持股约40%"
- ✅ "双总部：成都天府国际生物城(全球总部，16000㎡)+上海脑智天地"
- ✅ "2026年6月26日超级工厂一期竣工投运，投资人代表：华映资本季薇、清松资本张松、戈壁创投唐啟波、傅利叶顾捷出席剪彩"
- ✅ Entity map: parent/HK WFOE/VIE OpCo with EXACT ownership chain

### S2 Team
- ✅ Full education trace: "本科中科大机械电子工程；硕士香港理工大学软件工程；博士复旦大学类脑智能(在读)"
- ✅ Career chronology with exact titles and company names: "SaaS公司客如云创始人及CEO→阿里巴巴本地生活资深副总裁→第六次创业"
- ✅ Key hires: "Bashar W. Badran, Ph.D. — 南卡罗来纳医科大学神经科学博士，创立MUSC Neuro-X实验室，69篇同行评审论文，曾任职Neuralink临床合作负责人"
- ✅ External validation: "四川省千人计划创业领军人才"，"2023年追加10亿元投入AI+脑科学"

### S3 Technology & IP
- ✅ Technical mechanism deep-dive: "超声血流成像延迟时间0.5s~1.5s(近乎实时)"，"空间分辨率达亚毫米级别"
- ✅ Direct technical comparison: "Neuralink 1024通道电极覆盖大脑皮层1.3‰ vs 超声波路线覆盖25%全脑体积"
- ✅ Patent table with EXACT numbers: "CN119345607A" not "多项专利"
- ✅ Technology readiness: "相控阵(Phased Array)全称相位控制阵列...电子扫描技术区别于传统单探头"
- ✅ Mechanism explained in accessible but precise terms, with quantified performance metrics

### S4 Market
- ✅ TAM broken down by indication: "SCI 150亿(374万存量+10万/年新增)；OAB 200亿(2000万目标人群×¥1000/人)；VTE 150亿(5000万手术患者×¥300/人)；OSA 100亿(2030预测CAGR 19.7%)"
- ✅ Global market with CAGR and source: "全球神经调控市场$68亿(2025)→$139亿(2033)，CAGR 10.4% — Grand View Research"
- ✅ Policy timeline with specific documents: "2026年政府工作报告首次写入'脑机接口'，七部委《关于推动脑机接口产业创新发展的实施意见》，十五五规划六大重点产业"
- ✅ Geographic bifurcation: China market vs global, with separate data

### S5 Competition
- ✅ Named competitors with technical comparison: "美敦力(侵入式DBS/SCS全球龙头，$10万+/台) vs 复远数科(非侵入式，¥2-3万/台，价格1/50)"
- ✅ Not "竞争激烈" but specific: "巨头侵入式覆盖不足1%，我们瞄准99%"
- ✅ Competitive moat quantified: "50+知识产权+5PCT+国家一级查新'国内首创国际领先'认证"
- ✅ Direct product-by-product comparison table

### S6 Business Model
- ✅ Dual-engine strategy clearly articulated: "现金流产品线(已获证→自我造血)+核心创新产品线(国内首创→估值锚点)"
- ✅ Pricing: "设备¥2-3万+耗材¥300/套，单次治疗成本仅¥10元，侵入式价格的1/50"
- ✅ Unit economics: "100万+收入即时，2028年盈亏平衡目标"

### S7 Financials
- ✅ Actual revenue: "100万+高新技术服务及产品收入已实现" not "已有收入"
- ✅ Financing history with EXACT details: "天使轮1.5亿(2026-03-12，国生资本+道彤投资联合领投)→天使+轮4.2亿(2026-07-03，华映资本领投，红杉中国+C资本+蓝思科技等跟投，老股东超额加码)"
- ✅ ALL investors named, not "多家机构"
- ✅ Fund usage specified per round

### S8 Funding
- ✅ Complete financing table: 时间 | 轮次 | 总融资额 | 投资方(ALL named) | 资金用途
- ✅ Cumulative: "共融资2轮，累计完成融资5.7亿元人民币"
- ✅ Investor quality assessment: named VCs with track record

### S9 Strategy & Partnerships
- ✅ Named partners with collaboration scope: "傅利叶 — 下肢外骨骼+上肢康复+GR-3人形机器人，'意图-执行-感知反馈'闭环训练"
- ✅ "2026年1月28日正式签署战略合作协议" — exact date
- ✅ Clinical partners: "华西、协和、华山等三甲医院" — named institutions
- ✅ Roadmap with dates: "2026 Q3启动多中心临床"

### S10 Risk
- ✅ Specific risks tied to milestones: not "临床风险" but "CSNS多中心临床若显示疗效不优于假刺激对照→估值锚崩溃(-50% EV)"
- ✅ Probability attached: "30%概率，致命等级"
- ✅ Early warning signal: "2026 Q3-Q4销售数据持续低于预期"
- ✅ Mitigation plan: "现金流产品维持公司运转；可聚焦OAB/OSA等临床难度较低的管线"

### S11 Investment Thesis
- ✅ Non-consensus insight with data: "市场认为非侵入式=低壁垒，但国家一级查新认证+50+IP+5PCT+2张证组合在天使轮极为稀缺"
- ✅ Bull/Base/Bear with specific revenue/probability
- ✅ Exit path with named acquirers: "美敦力/雅培/品驰/迈瑞等战略并购" not "IPO或并购"

### S14 Scoring
- ✅ Weighted score table with specific rationale per dimension
- ✅ Key assumption sensitivity: ranked, with disproof trigger and EV impact %
- ✅ Position sizing: Kelly framework with portfolio correlation and max loss
