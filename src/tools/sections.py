"""The report's sections as the investment-analysis skill's template lays them out: a five-minute executive summary,
fourteen numbered sections and a generated source appendix.

Each section has an owner (the bot that researches and writes it), the visual components SKILL.md requires in it,
the tables its playbooks ask for, and the granularity markers scripts/check_depth.py was written to enforce. The
checks, the renderer, the prompts and the dashboard all read SECTIONS, so the standard lives in one place.
"""
from dataclasses import dataclass
import re

from .agents import AGENTS

LEAD, COMPANY, PRODUCT, MARKET = AGENTS['lead'], AGENTS['company'], AGENTS['product'], AGENTS['market']
FUNDAMENTALS, VALUATION, REGULATORY, RED_TEAM = (AGENTS['fundamentals'], AGENTS['valuation'], AGENTS['regulatory'],
                                                 AGENTS['red_team'])


@dataclass(frozen=True)
class Table:
    name: str
    keywords: tuple[str, ...]  # a header cell holding any of these (lowercased) marks the table
    listed: bool | None = None  # True: listed companies only; False: private companies only


@dataclass(frozen=True)
class Section:
    key: str
    number: int | None  # the template's slot, s1-s14; None for the executive summary
    title_zh: str
    title_en: str
    owner: str
    components: tuple[str, ...] = ()  # fence kinds the section must hold (report.COMPONENTS)
    tables: tuple[Table, ...] = ()
    markers: tuple[tuple[str, str], ...] = ()  # (what the marker is, regex): check_depth.py's granularity benchmark
    # Playbook headings the owner reads before researching, as (file, heading); an empty heading is the whole file.
    playbooks: tuple[tuple[str, str], ...] = ()

    @property
    def title(self) -> str:
        return f'{self.title_zh} {self.title_en}'


DATE = (r'\b(?:19|20)\d{2}-\d{2}-\d{2}\b|\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日'
        r'|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? \d{1,2}, (?:19|20)\d{2}')
PERCENT = r'\d+(?:\.\d+)?\s*%'

EXECUTIVE_SUMMARY = Section(
    'executive_summary', None, '5分钟速读', 'Executive Briefing', LEAD,
    components=('verdict', 'briefing', 'efficiency', 'one-question', 'takeaways'),
    playbooks=(('decision_framework.md', ''), ('report_strategy_playbook.md', 'Minimum Decision Standard'),
               ('public_equity_financials_lens.md', 'A1. Current Market Regime Assessment')))

SECTIONS = (
    Section(
        'company_overview', 1, '公司概览', 'Company Overview', COMPANY,
        components=('kpi', 'timeline'),
        tables=(Table('legal entity table', ('entity', '实体', '主体')),
                Table('cap table', ('shareholder', '股东'), listed=False)),
        markers=(('an exact date', DATE), ('an ownership percentage', PERCENT),
                 ('the legal entities', r'incorporat|subsidiar|holding compan|legal entit|注册|子公司|控股|实体')),
        playbooks=(('company_deep_dive_playbook.md', 'Section 1: Company Overview — Forensic Identity'),
                   ('section_deepening.md', 'Company Overview'))),
    Section(
        'team', 2, '创始人与核心团队', 'Founding Team & Key Personnel', COMPANY,
        components=('evidence',),
        tables=(Table('education table', ('degree', 'institution', '学位', '院校', '学历')),
                Table('career table', ('period', 'role', 'title', '任职', '职位', '期间')),
                Table('team assessment matrix', ('dimension', '维度'))),
        markers=(('degrees and institutions',
                  r'(?:B\.?S\b|B\.?A\b|bachelor|M\.?S\b|MBA|master|Ph\.?D|doctor|本科|学士|硕士|博士)'
                  r'.{0,80}(?:universit|college|institute|school|大学|学院)'),
                 ('career history', r'previously|formerly|served as|joined|founded|worked at|曾任|此前|加入|创立|创办'),
                 ('counted achievements', r'\d+[\s-]*(?:patents?|papers?|publications?|years?|exits?|篇|项|年|次)')),
        playbooks=(('company_deep_dive_playbook.md', 'Section 2: Founding Team & Core Personnel — Complete CVs'),
                   ('section_deepening.md', 'Founders and Team'))),
    Section(
        'technology_product', 3, '技术与产品', 'Technology & Product', PRODUCT,
        components=('evidence',),
        tables=(Table('performance metrics table', ('metric', '指标')),
                Table('technology comparison table', ('dimension', 'approach', '维度', '路线')),
                Table('moat table', ('barrier', '壁垒')),
                Table('patent table', ('patent', '专利')),
                Table('product inventory', ('product', '产品'))),
        # Patent and application numbers as written: US 10,912,502, US 17/662,019, WO 2023/123456, CN202310123456.
        markers=(('patent numbers', r'\b(?:US|CN|EP|WO|JP|KR)\s?\d[\d,/]{4,}\d|patent (?:no\.?|number)|专利号'),
                 ('an exact date', DATE),
                 ('a performance metric with a figure',
                  r'(?:accuracy|latency|throughput|efficiency|resolution|capacity|range|speed|power|yield|'
                  r'sensitivity|specificity|density|cycles?|精度|延迟|效率|分辨率|容量|功率|速度|良率|灵敏度).{0,30}\d'),
                 # In words, or in the technology comparison table: Dimension | the company | a rival.
                 ('a comparison with a named rival',
                  r'(?:\bvs\.?|versus|compared (?:with|to)|relative to|相比|相较|优于|对比).{0,80}[A-Z][A-Za-z]+'
                  r'|(?:^|\n)\|\s*(?:Dimension|维度)\s*\|[^|\n]+\|[^|\n]+\|')),
        playbooks=(('company_deep_dive_playbook.md', 'Section 3: Technology & IP — Patent-Level Detail'),
                   ('company_deep_dive_playbook.md', 'Section 4: Products — Per-Product Forensic Detail'),
                   ('section_deepening.md', 'Technology and Product'))),
    Section(
        'market', 4, '市场与行业分析', 'Market & Industry Analysis', MARKET,
        components=('evidence',),
        tables=(Table('market size table', ('tam', 'sam', 'market size', '市场规模')),
                Table('regional market table', ('region', '区域', '地区'))),
        markers=(('market size with a figure',
                  r'(?:\bTAM\b|\bSAM\b|\bSOM\b|market size|market (?:is|was) (?:worth|valued|sized)|市场规模).{0,60}\d'),
                 ('a CAGR', r'CAGR.{0,30}\d+(?:\.\d+)?\s*%|\d+(?:\.\d+)?\s*%\s*CAGR|复合增长率'),
                 ('policy with a year', r'(?:policy|regulat|\bact\b|\blaw\b|guideline|tariff|政策|法规|监管).{0,100}(?:19|20)\d{2}'),
                 # A region followed by its market or its share, or a table with a region column; the first port
                 # needed "market" within 50 characters and missed a split table with a Region column.
                 ('a geographic split', r'(?:United States|\bUS\b|U\.S\.|China|Europe|\bEU\b|Japan|India|Southeast Asia|'
                                        r'global|美国|中国|欧洲|日本|全球).{0,50}(?:market|市场|\d+(?:\.\d+)?\s*%)'
                                        r'|\|\s*(?:Region|Geography|Country|地区|区域|国家)\s*\|')),
        playbooks=(('company_deep_dive_playbook.md', 'Section 5: Market — Domestic + International Bifurcation'),
                   ('geo_market_context_lens.md', ''), ('section_deepening.md', 'Market and Industry'))),
    Section(
        'competition', 5, '竞争格局', 'Competitive Landscape', MARKET,
        components=('evidence', 'quad'),
        tables=(Table('competitor table', ('competitor', '竞争对手', '竞品')),
                Table('positioning table', ('position', '定位'))),
        markers=(('a head-to-head comparison', r'\bvs\.?|versus|compared (?:with|to)|相比|相较|对比'),
                 ('market share figures', r'(?:market share|share of|份额|市占率).{0,30}\d+(?:\.\d+)?\s*%'
                                          r'|\d+(?:\.\d+)?\s*%\s*(?:market )?share'),
                 ('named competitors', r'(?:competitor|rival|竞争对手|竞品).{0,60}[A-Z][a-z]+')),
        playbooks=(('company_deep_dive_playbook.md', 'Section 6: Competition — Per-Product Forensic Mapping'),
                   ('section_deepening.md', 'Competition'))),
    Section(
        'business_model', 6, '商业模式', 'Business Model', FUNDAMENTALS,
        components=('evidence',),
        tables=(Table('unit economics table', ('per unit', 'per customer', 'unit economics', 'ltv', 'cac', '单位经济', '单客')),
                Table('pricing table', ('price', 'pricing', '定价', '价格'))),
        markers=(('a price with a figure', r'(?:price|pricing|\bASP\b|\bfee|subscription|定价|价格|售价).{0,30}\d'),
                 ('a margin with a figure', r'(?:gross margin|contribution margin|net margin|operating margin|unit economics|'
                                            r'毛利率|净利率|贡献利润).{0,30}\d+(?:\.\d+)?\s*%'),
                 ('the revenue model', r'subscription|licen[cs]e|SaaS|per[- ]unit|per[- ]seat|recurring|one-time|hardware|'
                                       r'services|commission|take rate|订阅|一次性|佣金|服务费')),
        playbooks=(('company_deep_dive_playbook.md', '7.2 Detailed Unit Economics'),
                   ('section_deepening.md', 'Business Model'))),
    Section(
        'financials', 7, '财务分析', 'Financial Analysis', FUNDAMENTALS,
        components=('info',),
        tables=(Table('financial statements table', ('revenue', '营业收入', '收入')),
                Table('returns and working capital table', ('roe', 'roic', 'return on', 'dso', 'cash conversion', '回报', '周转'))),
        markers=(('revenue with a figure', r'(?:revenue|sales|营收|收入|销售额).{0,40}\d'),
                 ('profit or cash flow with a figure', r'(?:profit|net income|operating income|EBIT|EBITDA|free cash flow|FCF|'
                                                       r'cash flow|利润|净利|现金流).{0,40}\d'),
                 ('a fiscal year', r'\b(?:FY\s?)?(?:19|20)\d{2}\b|\d{4}\s*年')),
        playbooks=(('public_equity_financials_lens.md', 'Professional Financial Statement Analysis'),
                   ('company_deep_dive_playbook.md', 'Section 7: Financials — Forensic Detail'),
                   ('section_deepening.md', 'Financials'))),
    Section(
        'funding_valuation', 8, '融资历程与估值', 'Funding History & Valuation', VALUATION,
        tables=(Table('funding or trading table', ('round', '轮次', 'market cap', '市值', 'price', '股价')),
                Table('valuation methods table', ('method', '方法')),
                Table('peer multiples table', ('peer', '同行', '可比', 'p/e', 'ev/'))),
        markers=(('valuation or market value with a figure', r'(?:valuation|valued at|market cap|enterprise value|pre-money|'
                                                              r'post-money|估值|市值).{0,50}\d'),
                 ('a multiple', r'\d+(?:\.\d+)?\s*(?:x|×|倍)(?![A-Za-z])|P/E|EV/'),
                 ('capital-raising history', r'\bround\b|Series [A-Z]|\bseed\b|\bIPO\b|offering|raised|financing|融资|轮')),
        playbooks=(('public_equity_financials_lens.md', 'Market Data and Valuation'),
                   ('public_equity_financials_lens.md', 'A2. Stock Price & Trading Context'),
                   ('section_deepening.md', 'Funding and Valuation'))),
    Section(
        'strategy', 9, '发展方向与战略', 'Development Strategy', PRODUCT,
        tables=(Table('milestone table', ('milestone', 'roadmap', '里程碑', '路线图')),
                Table('partner table', ('partner', '合作'))),
        markers=(('a partnership or plan with an action',
                  r'(?:partner|agreement|collaborat|strategy|roadmap|plan|合作|战略|路线).{0,80}'
                  r'(?:sign|launch|announc|expand|enter|start|plan|签署|达成|建立|启动|推出)'),
                 ('a dated milestone', r'\b(?:19|20)\d{2}\b|\bQ[1-4]\b|\bH[12]\b')),
        playbooks=(('section_deepening.md', 'Strategy'),)),
    Section(
        'risk', 10, '风险评估', 'Risk Assessment', RED_TEAM,
        components=('risk-matrix', 'info'),
        markers=(('a probability with a figure', r'(?:probability|likelihood|chance|概率|可能性).{0,30}\d+(?:\.\d+)?\s*%'
                                                 r'|\d+(?:\.\d+)?\s*%\s*(?:probability|chance|概率)'),
                 ('severity levels', r'\b(?:critical|high|medium|low|fatal)\b|致命|高|中|低'),
                 ('mitigation', r'mitigat|hedg|contingen|缓释|应对|对冲')),
        playbooks=(('analysis_core.md', 'Red-Team Pass'), ('section_deepening.md', 'Risk'))),
    Section(
        'thesis', 11, '投资潜力与投资逻辑', 'Investment Potential & Thesis', LEAD,
        components=('scenarios', 'analogs'),
        tables=(Table('key assumptions table', ('assumption', '假设')),),
        markers=(('scenarios', r'\b(?:bull|base|bear)\b|牛市|基准|熊市|情景'),
                 ('a return multiple or target', r'\d+(?:\.\d+)?\s*(?:x|×|倍)(?![A-Za-z])|target price|price target|'
                                                 r'目标价|MOIC|\bIRR\b')),
        playbooks=(('decision_framework.md', ''), ('analysis_core.md', 'Deal Thesis Workflow'),
                   ('section_deepening.md', 'Investment Thesis'))),
    Section(
        'exit', 12, '退出策略分析', 'Exit Strategy Analysis', VALUATION,
        tables=(Table('exit routes table', ('acquirer', 'exit route', 'exit path', 'buyer', 'route', '收购方', '退出路径')),
                Table('precedent exits table', ('precedent', 'transaction', 'deal', '先例', '交易'))),
        markers=(('an exit route', r'\bIPO\b|M&A|acqui|trade sale|secondary sale|\bexit|上市|并购|收购|退出'),
                 ('a named acquirer or venue', r'[A-Z][A-Za-z&.]+(?:\s[A-Z][A-Za-z&.]+)*\s(?:Corp|Inc|Ltd|Group|Holdings|'
                                               r'plc|AG|SE|N\.V\.)|NASDAQ|Nasdaq|NYSE|HKEX|STAR Market|科创板|港交所')),
        playbooks=(('section_deepening.md', 'Exit Strategy'),)),
    Section(
        'esg', 13, 'ESG评估', 'ESG Assessment', REGULATORY,
        tables=(Table('ESG issues table', ('esg', 'issue', '议题')),
                Table('regulatory record table', ('regulator', 'license', 'record', '监管', '许可', '记录')),
                Table('policy impact matrix', ('factor', 'exposure', '因素', '敞口'))),
        markers=(('governance', r'governance|board|independent director|dual-class|voting|治理|董事会|独立董事'),
                 ('environmental or social issues', r'environment|emission|carbon|labor|labour|privacy|safety|'
                                                    r'supply chain|环境|排放|碳|劳工|隐私|安全'),
                 ('compliance records', r'complian|regulator|lawsuit|litigation|settlement|\bfine|recall|enforcement|'
                                        r'合规|监管|诉讼|处罚|召回')),
        playbooks=(('regulatory_database_lens.md', 'Integration into the Analysis Workflow'),
                   ('policy_geopolitics_lens.md', ''), ('section_deepening.md', 'ESG and Governance'))),
    Section(
        'scoring', 14, '综合评分与投资建议', 'Comprehensive Scoring & Recommendation', LEAD,
        components=('sensitivity', 'takeaways'),
        tables=(Table('weighted score table', ('weight', '权重')),),
        markers=(('scores out of 10', r'\d+(?:\.\d+)?\s*/\s*10|(?:score|rating|评分).{0,30}\d+(?:\.\d+)?'),
                 ('sensitivity with a valuation impact', r'(?:assumption|sensitivity|假设|敏感性).{0,80}'
                                                         r'(?:EV|valuation|value|price|估值|价值|影响|impact)')),
        playbooks=(('section_deepening.md', 'Scoring and Recommendation'),
                   ('public_equity_financials_lens.md', 'Recommendation and Position Sizing'),
                   ('public_equity_financials_lens.md', 'A4. Regime-Appropriate Strategy'))),
)
ALL_SECTIONS = (EXECUTIVE_SUMMARY,) + SECTIONS
BY_KEY = {section.key: section for section in ALL_SECTIONS}
BY_NUMBER = {section.number: section for section in SECTIONS}
OWNED = {owner: tuple(s.key for s in ALL_SECTIONS if s.owner == owner) for owner in {s.owner for s in ALL_SECTIONS}}

# The most a section may hold: one model call writes one section, and Rakazo caps a call at 32,768 output tokens,
# reasoning included. It also keeps a section inside one 12,000-character tool result.
MAX_SECTION_CHARS = 9_000

# The skill's ratings (public_equity_financials_lens.md "Rating labels" plus the analysis_core fallback "Hold off")
# and its primary-market decisions (section_deepening.md "Investment Thesis").
LISTED_RATINGS = ('Buy', 'Add', 'Hold', 'Watchlist', 'Hold off', 'Reduce', 'Sell', 'Avoid')
PRIVATE_RATINGS = ('Invest now', 'Invest with conditions', 'Wait for milestone', 'Pass')
# Directional calls on a listed company need the evidence gate (N4): a primary filing and timestamped market data.
LISTED_DIRECTIONAL = ('Buy', 'Add', 'Reduce', 'Sell', 'Avoid')
# Committing capital to a private company needs at least one independent source behind the case (N4).
PRIVATE_COMMITTING = ('Invest now', 'Invest with conditions')

# The skill asks for a "weighted score table with specific rationale per dimension" but defines no dimensions or
# weights, so these are the app's own, one set per company type (percent, summing to 100).
SCORE_WEIGHTS = {
    'listed': {'Business quality and moat': 15, 'Growth and market': 10, 'Competitive position': 10,
               'Earnings quality and financial strength': 20, 'Valuation and margin of safety': 20,
               'Management, governance and capital allocation': 10, 'Balance-sheet and downside resilience': 10,
               'Catalysts and timing': 5},
    'private': {'Team': 20, 'Technology and product': 15, 'Market': 15, 'Competition and moat': 10,
                'Business model and unit economics': 10, 'Traction and financials': 10, 'Valuation and terms': 10,
                'Exit path': 5, 'ESG and governance': 5},
}
# analysis_core.md: "If a section lacks peer/benchmark context, do not score it above 7/10."
NO_BENCHMARK_CAP = 7


def section_key(name: str) -> str:
    """A section's key from its key, number ("s4", "S4", "4") or English title; raises ValueError otherwise."""
    wanted = name.strip()
    if wanted in BY_KEY:
        return wanted
    number = re.fullmatch(r'[sS]?(\d{1,2})', wanted)
    if number and int(number.group(1)) in BY_NUMBER:
        return BY_NUMBER[int(number.group(1))].key
    lowered = wanted.lower()
    for section in ALL_SECTIONS:
        if lowered in (section.title_en.lower(), section.title_zh):
            return section.key
    keys = ', '.join(section.key for section in ALL_SECTIONS)
    raise ValueError(f'No section {name!r}. Sections: {keys}.')


def is_rating(rating: str, listed: bool) -> bool:
    return rating in (LISTED_RATINGS if listed else PRIVATE_RATINGS)
