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
| **药品审评中心 (CDE)** | NMPA | Drug IND/NDA/ANDA applications, review status, clinical trial approvals | Public (部分) | ★★★★★ Critical for biotech |
| **医疗器械注册** | NMPA | Device registration certificates, Class I/II/III approvals | Public | ★★★★★ Critical for medtech |
| **临床试验登记** (chinadrugtrials.org.cn) | CDE | Trial phase, endpoints, enrollment, sites, status changes | Public | ★★★★★ Must-check for clinical-stage |
| **GMP/GSP认证** | NMPA provincial | Manufacturing and distribution quality certifications | Account-gated | ★★★★ Production readiness |
| **医保目录** | NHSA (医保局) | National reimbursement drug list (NRDL) inclusion, pricing | Public | ★★★★★ Revenue driver for drugs |
| **集采 (VBP)** | NHSA | Volume-based procurement results, prices, volumes | Public | ★★★★ Margin impact |
| **药品注册证书** | NMPA | Approved drug list with holder, specification, expiry | Public | ★★★★ IP/approval verification |

**Search strategies:**
- `[药品名/公司名] CDE 审评进度 site:cde.org.cn`
- `[公司名] 临床试验 site:chinadrugtrials.org.cn`
- `[药品名] 医保目录 2025 2026 NRDL`
- `[公司名] GMP 认证 药监局`

### State-Owned Enterprises / Infrastructure / Defense

| Database | Agency | What It Contains | Access Level | Investment Value |
|----------|--------|-----------------|-------------|-----------------|
| **央企名录+财务** | SASAC (国资委) | Central SOE list, financial summaries, restructuring approvals | Public (有限) | ★★★★ SOE ownership verification |
| **国有产权交易** | 各地产权交易所 | SOE equity transfers, mixed-ownership reform deals | Public (分散) | ★★★★ Deal comps |
| **政府采购** (ccgp.gov.cn) | 财政部 | Government procurement contracts, bidders, amounts | Public | ★★★★★ Revenue verification |
| **武器装备科研生产许可** | 国防科工局 | Military production licenses (not publicly searchable) | Restricted | ★★★★★ Defense sector |
| **军工保密资质** | 国防科工局 | Classified — cannot be searched | Restricted | ★★★ Risk indicator (if lost) |

**Search strategies:**
- `[公司名] 政府采购 中标 site:ccgp.gov.cn`
- `[央企名] 国资委 财务 2025`
- `[公司名] 产权交易 股权转让`
- `[行业] 军工四证 资质`

### Semiconductor / Electronics / Manufacturing

| Database | Agency | What It Contains | Access Level | Investment Value |
|----------|--------|-----------------|-------------|-----------------|
| **集成电路企业认定** | MIIT (工信部) | IC design/foundry/packaging enterprise qualification | Public (名单) | ★★★★ Subsidy eligibility |
| **国家大基金投资** | 国家集成电路产业投资基金 | Portfolio companies, investment amounts | Semi-public | ★★★★ Government backing signal |
| **专精特新"小巨人"** | MIIT | SME designation list, tier (国家级/省级) | Public | ★★★★ Policy support indicator |
| **高新技术企业认定** | 科技部/税务局 | High-tech enterprise status, tax benefits | Public | ★★★ Tax rate verification |
| **专利检索** (cnipa.gov.cn) | CNIPA (知识产权局) | Patent applications, grants, legal status, assignments | Public | ★★★★★ IP due diligence |
| **稀土/矿产配额** | MIIT/自然资源部 | Rare earth mining/smelting quotas, export quotas | Public | ★★★★ Supply-constrained industries |

**Search strategies:**
- `[公司名] 专精特新 小巨人 site:miit.gov.cn`
- `[公司名] 高新技术企业 认定`
- `[公司名/技术名] 专利 site:cnipa.gov.cn`
- `[行业] 集成电路 大基金 投资`

### AI / Internet / Data

| Database | Agency | What It Contains | Access Level | Investment Value |
|----------|--------|-----------------|-------------|-----------------|
| **算法备案** | CAC (网信办) | Algorithm registration records, service names, security assessments | Public | ★★★★ AI regulatory compliance |
| **深度合成服务备案** | CAC | Deep synthesis (AI-generated content) service registrations | Public | ★★★★ AI product compliance |
| **数据安全审查** | CAC | Data security review results (mostly non-public) | Restricted | ★★★★★ For companies with large user data |
| **互联网信息服务许可 (ICP)** | MIIT | ICP license number, service scope | Public | ★★★ Basic operation legitimacy |
| **个人信息保护审计** | CAC | Privacy compliance status | Non-public | ★★★ GDPR/China privacy law risk |

**Search strategies:**
- `[公司名/AI产品名] 算法备案 网信办`
- `[公司名] ICP 备案`
- `[APP名] 深度合成 备案`

### Aerospace / Aviation

| Database | Agency | What It Contains | Access Level | Investment Value |
|----------|--------|-----------------|-------------|-----------------|
| **民用航天发射许可** | 国防科工局 | Launch licenses, payload approvals | Restricted (科研许可公开) | ★★★★★ Launch capability proof |
| **卫星频率/轨道** | MIIT (无线电管理局) | Frequency assignments, orbital slot filings | Semi-public (ITU filings) | ★★★★★ Space resource scarcity |
| **民用无人机经营许可证** | CAAC (民航局) | Drone operation permits | Public | ★★★★ Drone sector |
| **适航证 (TC/PC/AC)** | CAAC | Aircraft type/production/airworthiness certificates | Public | ★★★★★ eVTOL/drone manufacturing |

**Search strategies:**
- `[公司名/火箭名] 发射许可 民用航天`
- `[卫星名/星座名] 频率 轨道 ITU`
- `[公司名] 适航证 TC CAAC`

### Finance / Fintech

| Database | Agency | What It Contains | Access Level | Investment Value |
|----------|--------|-----------------|-------------|-----------------|
| **金融许可证** | NFRA (金融监管总局) | Banking, insurance, trust licenses | Public | ★★★★ License legitimacy |
| **支付业务许可证** | PBOC (央行) | Payment service provider licenses | Public | ★★★★★ Fintech core asset |
| **基金从业资格** | AMAC (基金业协会) | Fund manager registrations, product filings | Public | ★★★★ Asset management |
| **征信业务许可** | PBOC | Credit reporting licenses | Restricted | ★★★★★ If applicable |
| **IPO/融资审核** | CSRC/交易所 | IPO filings, review status, feedback letters | Public | ★★★★★ Pre-IPO companies |

### Energy / New Energy

| Database | Agency | What It Contains | Access Level | Investment Value |
|----------|--------|-----------------|-------------|-----------------|
| **光伏/风电项目核准** | NEA (能源局) / 地方发改委 | Project approvals, capacity, grid connection | Semi-public | ★★★★ Pipeline verification |
| **核安全许可证** | NNSA (核安全局) | Nuclear facility licenses, safety reviews | Public (部分) | ★★★★★ Nuclear/fusion sector |
| **新能源汽车准入** | MIIT | NEV manufacturing qualification | Public | ★★★★ Automotive |
| **碳排放配额** | MEE (生态环境部) | Carbon allowance allocations, trading data | Semi-public | ★★★ Carbon-intensive industries |

### Construction / Real Estate

| Database | Agency | What It Contains | Access Level | Investment Value |
|----------|--------|-----------------|-------------|-----------------|
| **房地产开发资质** | MOHURD (住建部) | Developer qualification grades | Public | ★★★★ Developer credibility |
| **土地招拍挂** | 地方自然资源局 | Land auction results, prices, winners | Public (各地分散) | ★★★★ Land bank verification |
| **预售许可证** | 地方住建委 | Pre-sale permits, project details | Public | ★★★ Project pipeline |

### Cross-Cutting Databases (All Industries)

| Database | Agency | What It Contains | Access Level |
|----------|--------|-----------------|-------------|
| **国家企业信用信息公示系统** (gsxt.gov.cn) | SAMR (市场监管总局) | Business registration, shareholders, penalties, annual reports | Public |
| **裁判文书网** (wenshu.court.gov.cn) | 最高人民法院 | All civil/criminal/administrative judgments | Public |
| **中国执行信息公开网** (zxgk.court.gov.cn) | 最高人民法院 | Dishonest executees (老赖), enforcement cases | Public |
| **信用中国** (creditchina.gov.cn) | NDRC (发改委) | Administrative penalties, credit ratings, blacklists | Public |
| **国家税务总局** | STA | Tax payment ratings (A-level taxpayers) | Semi-public |
| **企查查/天眼查/爱企查** | Commercial | Aggregated business data (often paywalled but richer) | Freemium |
| **巨潮资讯** (cninfo.com.cn) | CSRC-designated | Public company filings, announcements | Public |
| **全国中小企业股份转让系统** (neeq.com.cn) | NEEQ | NEEQ-listed company filings | Public |

## The User Data Request Protocol

When the analyst hits an account-gated or restricted database, do NOT silently skip it. Instead, emit a specific, actionable request to the user.

### Request Template

```markdown
### 📋 监管数据库信息请求

为了提升 [公司名] 分析的数据质量，以下信息需要从监管数据库中获取：

| # | 数据库 | 需要查询的内容 | 为什么重要 | 如何获取 |
|---|--------|---------------|-----------|---------|
| 1 | [数据库名] | [具体查询对象] | [对投资判断的影响] | [获取方式：公开URL/登录路径/所需权限] |

**如果您能提供以下任一文件，将显著提升报告的置信度：**
- [ ] [文件名/截图类型 1]
- [ ] [文件名/截图类型 2]
```

### Industry-Specific Request Templates

#### Biotech/Medtech 专用

```markdown
### 📋 药监数据请求

以下数据对评估 [公司名] 的产品管线价值至关重要：

1. **CDE审评进度** — 请登录 https://www.cde.org.cn ，在"受理品种信息"中查询 [药品名/受理号]，截图审评状态和时间线。
2. **临床试验详情** — 请访问 http://www.chinadrugtrials.org.cn ，搜索 [公司名/药品名]，导出试验阶段、入组人数、主要终点、状态变化历史。
3. **医疗器械注册证** — 请访问 NMPA医疗器械查询，输入 [公司名]，截图注册证编号、有效期和产品范围。
4. **医保目录状态** — 请搜索最新版NRDL，确认 [药品名] 是否在目录内、谈判价格和报销比例。

**重要性：** 这些数据直接决定产品管线的估值——一个III期临床的成功概率、一个器械的注册进度、一个药品的医保价格，任何一项变动都可能影响数十亿估值。
```

#### SOE/Infrastructure 专用

```markdown
### 📋 国资委/政府采购数据请求

1. **央企产权登记** — 请通过国资委或产权交易所查询 [公司名] 的国有股权结构，确认实际控制人层级。
2. **政府采购中标记录** — 请访问 https://www.ccgp.gov.cn ，搜索 [公司名]，导出近3年中标项目、金额和采购方。
3. **专精特新认定** — 请访问MIIT官网查询 [公司名] 是否在"小巨人"名单中，以及认定层级（国家级/省级）。
```

#### Semiconductor 专用

```markdown
### 📋 工信部/知识产权数据请求

1. **集成电路企业认定** — 请确认 [公司名] 是否在MIIT公布的集成电路认定企业名单中。
2. **大基金投资记录** — 请查询国家集成电路产业投资基金（大基金一期/二期/三期）的portfolio中是否包含 [公司名]。
3. **核心专利法律状态** — 请在CNIPA (https://www.cnipa.gov.cn) 查询 [专利号列表] 的法律状态（有效/无效/质押/许可）。
```

## Integration into the Analysis Workflow

### When to Trigger This Lens

Trigger when the company belongs to:
- Biotech/medtech/pharma → NMPA/CDE/NHSA databases
- SOE or SOE supply chain → SASAC/procurement databases
- Semiconductor/advanced manufacturing → MIIT/CNIPA databases
- AI/internet/platform → CAC algorithm registry
- Aerospace/satellite → CAAC/国防科工局 databases
- Fintech/payment → PBOC/NFRA license databases
- Energy/nuclear → NEA/NNSA databases
- Any company → gsxt.gov.cn (business registration) + wenshu.court.gov.cn (litigation check) as baseline

### Workflow Steps

1. **Before research:** Identify the company's industry → map to regulatory databases using the tables above.
2. **During web search:** Include 2-3 targeted searches against each relevant public registry.
3. **If account-gated:** Emit a User Data Request using the template.
4. **If information cannot be obtained:** Explicitly note in the report: "未能从 [数据库名] 获取 [信息类型]，该数据对 [投资判断维度] 具有 [重要性等级] 的重要性。建议在尽调中要求公司提供。"
5. **When user provides files:** Treat them as primary-source evidence (confidence: high), cite by filename and issuing agency.

### Data Hierarchy

Regulatory data ranks at the top of the evidence hierarchy:

```
1. Court judgments / regulatory filings (源之根源) ← HIGHEST CONFIDENCE
2. Government-issued licenses / certificates
3. Procurement contract awards (ccgp.gov.cn)
4. Patent office records (CNIPA/USPTO)
5. Public company filings (年报/招股书 via 巨潮)
   --- "hard evidence" line ---
6. Company-provided materials (pitch decks, internal reports)
7. Media reports / industry analysis
8. OCR-derived text from scanned documents ← LOWEST CONFIDENCE
```

Anything below the "hard evidence" line should be cross-verified against something above it whenever possible.

## Common Pitfalls

1. **Don't assume data is unavailable just because it's not on the first page of search results.** Many Chinese government databases are poorly indexed by Google/Bing. Use site: searches and the databases' own (often terrible) search functions.
2. **Don't confuse "企业信用信息公示系统" annual reports with audited financials.** The former are self-reported and often contain placeholder numbers for non-public companies.
3. **Patent counts ≠ patent quality.** A company with 100 utility model patents (实用新型) may have weaker IP than one with 10 invention patents (发明专利). Always distinguish.
4. **NDRC approvals ≠ actual construction.** Many projects receive government approval but are never built due to financing or market conditions.
5. **Algorithm registrations (算法备案) confirm existence but not performance.** A registered AI algorithm tells you the company is operating legally, not that the product is good.
