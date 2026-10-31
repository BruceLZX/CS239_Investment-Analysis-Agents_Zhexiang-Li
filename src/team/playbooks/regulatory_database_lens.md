# Regulatory & Government Database Intelligence Lens

Use this lens when government filings, regulatory approvals, official registries, license status, subsidy records, or compliance history can materially affect the investment thesis. This lens applies to virtually every company — the question is *which* databases, not *whether* to check them.

## Core Principle

Regulatory databases are the closest thing to "source of truth" in investment research. They are maintained by government agencies with legal authority, carry penalties for false reporting, and often contain data that companies do not voluntarily disclose. A single regulatory filing can be worth more than ten media articles.

However, most of these databases require accounts, are behind paywalls, have clunky Chinese-only interfaces, or restrict API access. Treat them as a **capability ladder**:

```
Tier 1: Public web search → Tier 2: Public registry lookup → Tier 3: Account-gated query → Tier 4: User-fetched documents
```

## Industry → Regulatory Body Mapping

### Healthcare / Biotech / Medtech

| Database | Agency | What It Contains | Access Level | Investment Value |
|----------|--------|-----------------|-------------|-----------------|
| **Center for Drug Evaluation (CDE)** | NMPA | Drug IND/NDA/ANDA applications, review status, clinical trial approvals | Public (partly) | ★★★★★ Critical for biotech |
| **Medical device registration** | NMPA | Device registration certificates, Class I/II/III approvals | Public | ★★★★★ Critical for medtech |
| **Clinical trial registry** (chinadrugtrials.org.cn) | CDE | Trial phase, endpoints, enrollment, sites, status changes | Public | ★★★★★ Must-check for clinical-stage |
| **GMP/GSP certification** | NMPA provincial | Manufacturing and distribution quality certifications | Account-gated | ★★★★ Production readiness |
| **National reimbursement list** | NHSA | National reimbursement drug list (NRDL) inclusion, pricing | Public | ★★★★★ Revenue driver for drugs |
| **Volume-based procurement (VBP)** | NHSA | Volume-based procurement results, prices, volumes | Public | ★★★★ Margin impact |
| **Drug registration certificates** | NMPA | Approved drug list with holder, specification, expiry | Public | ★★★★ IP/approval verification |

**Search strategies:**
- `[drug or company name] CDE review status site:cde.org.cn`
- `[company name] clinical trial site:chinadrugtrials.org.cn`
- `[drug name] national reimbursement list 2025 2026 NRDL`
- `[company name] GMP certification NMPA`

### State-Owned Enterprises / Infrastructure / Defense

| Database | Agency | What It Contains | Access Level | Investment Value |
|----------|--------|-----------------|-------------|-----------------|
| **Central SOE list and financials** | SASAC | Central SOE list, financial summaries, restructuring approvals | Public (limited) | ★★★★ SOE ownership verification |
| **State-owned equity transactions** | Local equity exchanges | SOE equity transfers, mixed-ownership reform deals | Public (scattered) | ★★★★ Deal comps |
| **Government procurement** (ccgp.gov.cn) | Ministry of Finance | Government procurement contracts, bidders, amounts | Public | ★★★★★ Revenue verification |
| **Weapons R&D and production license** | SASTIND | Military production licenses (not publicly searchable) | Restricted | ★★★★★ Defense sector |
| **Defense security qualification** | SASTIND | Classified — cannot be searched | Restricted | ★★★ Risk indicator (if lost) |

**Search strategies:**
- `[company name] government procurement award site:ccgp.gov.cn`
- `[central SOE name] SASAC financials 2025`
- `[company name] equity exchange share transfer`
- `[industry] defense industry licenses`

### Semiconductor / Electronics / Manufacturing

| Database | Agency | What It Contains | Access Level | Investment Value |
|----------|--------|-----------------|-------------|-----------------|
| **Integrated circuit enterprise qualification** | MIIT | IC design/foundry/packaging enterprise qualification | Public (list) | ★★★★ Subsidy eligibility |
| **"Big Fund" investments** | China Integrated Circuit Industry Investment Fund | Portfolio companies, investment amounts | Semi-public | ★★★★ Government backing signal |
| **"Little giant" specialized SMEs** | MIIT | SME designation list, tier (national or provincial) | Public | ★★★★ Policy support indicator |
| **High-tech enterprise status** | Ministry of Science and Technology, tax bureau | High-tech enterprise status, tax benefits | Public | ★★★ Tax rate verification |
| **Patent search** (cnipa.gov.cn) | CNIPA | Patent applications, grants, legal status, assignments | Public | ★★★★★ IP due diligence |
| **Rare earth and mineral quotas** | MIIT, Ministry of Natural Resources | Rare earth mining/smelting quotas, export quotas | Public | ★★★★ Supply-constrained industries |

**Search strategies:**
- `[company name] little giant specialized SME site:miit.gov.cn`
- `[company name] high-tech enterprise status`
- `[company or technology name] patent site:cnipa.gov.cn`
- `[industry] integrated circuit Big Fund investment`

### AI / Internet / Data

| Database | Agency | What It Contains | Access Level | Investment Value |
|----------|--------|-----------------|-------------|-----------------|
| **Algorithm registration** | CAC | Algorithm registration records, service names, security assessments | Public | ★★★★ AI regulatory compliance |
| **Deep synthesis service registration** | CAC | Deep synthesis (AI-generated content) service registrations | Public | ★★★★ AI product compliance |
| **Data security review** | CAC | Data security review results (mostly non-public) | Restricted | ★★★★★ For companies with large user data |
| **Internet content provider license (ICP)** | MIIT | ICP license number, service scope | Public | ★★★ Basic operation legitimacy |
| **Personal information protection audit** | CAC | Privacy compliance status | Non-public | ★★★ GDPR/China privacy law risk |

**Search strategies:**
- `[company or AI product name] algorithm registration CAC`
- `[company name] ICP registration`
- `[app name] deep synthesis registration`

### Aerospace / Aviation

| Database | Agency | What It Contains | Access Level | Investment Value |
|----------|--------|-----------------|-------------|-----------------|
| **Civil space launch license** | SASTIND | Launch licenses, payload approvals | Restricted (research licenses are public) | ★★★★★ Launch capability proof |
| **Satellite frequencies and orbits** | MIIT (Radio Administration Bureau) | Frequency assignments, orbital slot filings | Semi-public (ITU filings) | ★★★★★ Space resource scarcity |
| **Civil drone operating permit** | CAAC | Drone operation permits | Public | ★★★★ Drone sector |
| **Airworthiness certificates (TC/PC/AC)** | CAAC | Aircraft type/production/airworthiness certificates | Public | ★★★★★ eVTOL/drone manufacturing |

**Search strategies:**
- `[company or rocket name] launch license civil space`
- `[satellite or constellation name] frequency orbit ITU`
- `[company name] airworthiness certificate TC CAAC`

### Finance / Fintech

| Database | Agency | What It Contains | Access Level | Investment Value |
|----------|--------|-----------------|-------------|-----------------|
| **Financial licenses** | NFRA | Banking, insurance, trust licenses | Public | ★★★★ License legitimacy |
| **Payment business license** | PBOC | Payment service provider licenses | Public | ★★★★★ Fintech core asset |
| **Fund manager registration** | AMAC | Fund manager registrations, product filings | Public | ★★★★ Asset management |
| **Credit reporting license** | PBOC | Credit reporting licenses | Restricted | ★★★★★ If applicable |
| **IPO and financing review** | CSRC, exchanges | IPO filings, review status, feedback letters | Public | ★★★★★ Pre-IPO companies |

### Energy / New Energy

| Database | Agency | What It Contains | Access Level | Investment Value |
|----------|--------|-----------------|-------------|-----------------|
| **Solar and wind project approvals** | NEA, local NDRC offices | Project approvals, capacity, grid connection | Semi-public | ★★★★ Pipeline verification |
| **Nuclear safety license** | NNSA | Nuclear facility licenses, safety reviews | Public (partly) | ★★★★★ Nuclear/fusion sector |
| **New energy vehicle market access** | MIIT | NEV manufacturing qualification | Public | ★★★★ Automotive |
| **Carbon emission allowances** | MEE | Carbon allowance allocations, trading data | Semi-public | ★★★ Carbon-intensive industries |

### Construction / Real Estate

| Database | Agency | What It Contains | Access Level | Investment Value |
|----------|--------|-----------------|-------------|-----------------|
| **Real estate development qualification** | MOHURD | Developer qualification grades | Public | ★★★★ Developer credibility |
| **Land auctions** | Local natural resources bureaus | Land auction results, prices, winners | Public (scattered by locality) | ★★★★ Land bank verification |
| **Pre-sale permits** | Local housing commissions | Pre-sale permits, project details | Public | ★★★ Project pipeline |

### Cross-Cutting Databases (All Industries)

| Database | Agency | What It Contains | Access Level |
|----------|--------|-----------------|-------------|
| **National Enterprise Credit Information Publicity System** (gsxt.gov.cn) | SAMR | Business registration, shareholders, penalties, annual reports | Public |
| **China Judgements Online** (wenshu.court.gov.cn) | Supreme People's Court | All civil/criminal/administrative judgments | Public |
| **China Enforcement Information Public Website** (zxgk.court.gov.cn) | Supreme People's Court | Dishonest judgment debtors, enforcement cases | Public |
| **Credit China** (creditchina.gov.cn) | NDRC | Administrative penalties, credit ratings, blacklists | Public |
| **State Taxation Administration** | STA | Tax payment ratings (A-level taxpayers) | Semi-public |
| **Qichacha, Tianyancha, Aiqicha** | Commercial | Aggregated business data (often paywalled but richer) | Freemium |
| **CNINFO** (cninfo.com.cn) | CSRC-designated | Public company filings, announcements | Public |
| **National Equities Exchange and Quotations** (neeq.com.cn) | NEEQ | NEEQ-listed company filings | Public |

## The User Data Request Protocol

When the analyst hits an account-gated or restricted database, do NOT silently skip it. Instead, emit a specific, actionable request to the user.

### Request Template

```markdown
### 📋 Regulatory database information request

To improve the data quality of the [company name] analysis, the following information is needed from regulatory databases:

| # | Database | What to look up | Why it matters | How to get it |
|---|--------|---------------|-----------|---------|
| 1 | [database name] | [what exactly to look up] | [effect on the investment judgement] | [how to get it: public URL, login path, permissions needed] |

**Any of these files would significantly raise the report's confidence:**
- [ ] [file name or screenshot type 1]
- [ ] [file name or screenshot type 2]
```

### Industry-Specific Request Templates

#### Biotech/Medtech

```markdown
### 📋 Drug regulator data request

These data are essential to valuing the product pipeline of [company name]:

1. **CDE review status:** log in at https://www.cde.org.cn, look up [drug name or acceptance number] under the accepted applications, and send a screenshot of its review status and timeline.
2. **Clinical trial details:** at http://www.chinadrugtrials.org.cn, search [company or drug name] and export the trial phase, enrollment, primary endpoints and status history.
3. **Medical device registration certificate:** in the NMPA's device lookup, enter [company name] and send a screenshot of the certificate number, expiry and product scope.
4. **Reimbursement list status:** search the latest NRDL and confirm whether [drug name] is listed, its negotiated price and its reimbursement ratio.

**Why it matters:** these data directly set the pipeline's valuation. The odds of a Phase III trial, a device's registration progress or a drug's reimbursement price can each move the valuation by billions.
```

#### SOE/Infrastructure

```markdown
### 📋 SASAC and government procurement data request

1. **Central SOE equity registration:** through SASAC or an equity exchange, look up [company name]'s state ownership structure and confirm the level of its actual controller.
2. **Government procurement awards:** at https://www.ccgp.gov.cn, search [company name] and export the awards of the last 3 years, with amounts and buyers.
3. **Little giant designation:** on the MIIT site, check whether [company name] is on the "little giant" list, and at which level (national or provincial).
```

#### Semiconductor

```markdown
### 📋 MIIT and intellectual property data request

1. **Integrated circuit enterprise qualification:** confirm whether [company name] is on MIIT's list of qualified integrated circuit enterprises.
2. **Big Fund investments:** check whether the portfolio of the China Integrated Circuit Industry Investment Fund (Big Fund phases I, II and III) includes [company name].
3. **Legal status of core patents:** at CNIPA (https://www.cnipa.gov.cn), look up the legal status (valid, invalid, pledged or licensed) of [list of patent numbers].
```

## Integration into the Analysis Workflow

### When to Trigger This Lens

Trigger when the company belongs to:
- Biotech/medtech/pharma → NMPA/CDE/NHSA databases
- SOE or SOE supply chain → SASAC/procurement databases
- Semiconductor/advanced manufacturing → MIIT/CNIPA databases
- AI/internet/platform → CAC algorithm registry
- Aerospace/satellite → CAAC and SASTIND databases
- Fintech/payment → PBOC/NFRA license databases
- Energy/nuclear → NEA/NNSA databases
- Any company → gsxt.gov.cn (business registration) + wenshu.court.gov.cn (litigation check) as baseline

### Workflow Steps

1. **Before research:** Identify the company's industry → map to regulatory databases using the tables above.
2. **During web search:** Include 2-3 targeted searches against each relevant public registry.
3. **If account-gated:** Emit a User Data Request using the template.
4. **If information cannot be obtained:** Explicitly note in the report: "[information type] could not be obtained from [database name]; it has [importance level] importance for [dimension of the investment judgement]. Ask the company for it in diligence."
5. **When user provides files:** Treat them as primary-source evidence (confidence: high), cite by filename and issuing agency.

### Data Hierarchy

Regulatory data ranks at the top of the evidence hierarchy:

```
1. Court judgments / regulatory filings (the root source) ← HIGHEST CONFIDENCE
2. Government-issued licenses / certificates
3. Procurement contract awards (ccgp.gov.cn)
4. Patent office records (CNIPA/USPTO)
5. Public company filings (annual reports and prospectuses via CNINFO)
   --- "hard evidence" line ---
6. Company-provided materials (pitch decks, internal reports)
7. Media reports / industry analysis
8. OCR-derived text from scanned documents ← LOWEST CONFIDENCE
```

Anything below the "hard evidence" line should be cross-verified against something above it whenever possible.

## Common Pitfalls

1. **Don't assume data is unavailable just because it's not on the first page of search results.** Many Chinese government databases are poorly indexed by Google/Bing. Use site: searches and the databases' own (often terrible) search functions.
2. **Don't confuse "National Enterprise Credit Information Publicity System" annual reports with audited financials.** The former are self-reported and often contain placeholder numbers for non-public companies.
3. **Patent counts ≠ patent quality.** A company with 100 utility model patents may have weaker IP than one with 10 invention patents. Always distinguish.
4. **NDRC approvals ≠ actual construction.** Many projects receive government approval but are never built due to financing or market conditions.
5. **Algorithm registrations confirm existence but not performance.** A registered AI algorithm tells you the company is operating legally, not that the product is good.
