"""Word lists and patterns shared by the QA checks.

The skill's lists are Chinese, since its reports usually are; each list here keeps the skill's terms verbatim and
adds English equivalents, so an English report is held to the same standard instead of failing (or passing) only
because of its language.
"""
import html
import re

# Python's \b treats Chinese characters as word characters, so the skill's \bS\d+\b misses "来源S1"; lookarounds
# work in both languages.
SOURCE_ID_RE = re.compile(r'(?<![A-Za-z0-9])S\d+(?!\d)')
URL_RE = re.compile(r'https?://[^\s|)>"\]]+')
STYLE_SCRIPT_RE = re.compile(r'<(style|script)[^>]*>[\s\S]*?</\1>', re.I)
TAG_RE = re.compile(r'<[^>]+>')
PARAGRAPH_RE = re.compile(r'<p(?:\s+[^>]*)?>[\s\S]*?</p>', re.I)
SENTENCE_RE = re.compile(r'[^。！？.!?]{24,}[。！？.!?]')
# check_depth.py's NUMBER_PATTERN.
NUMBER_RE = re.compile(r'(?<![A-Za-z])(?:\d+(?:\.\d+)?%?|\d{4}年|\d+(?:\.\d+)?\s*(?:万|亿|百万|千万|billion|million|m|bn|元|美元|'
                       r'个月|年))', re.I)
PLACEHOLDER_TERMS = ('todo', 'tbd', 'xxx', '待补', '待填', 'placeholder')

# check_depth.py ANALYTICAL_COVERAGE_TERMS, with English added.
ANALYTICAL_COVERAGE = {
    'evidence/source grounding': ('证据', '来源', 'source', '验证', '公开', '披露', '公告', '年报', '招股书', '监管', '据',
                                  'filing', 'disclosed', 'reported', 'according to', 'verified', 'evidence'),
    'economic/strategic interpretation': ('原因', '驱动', '为什么', '意味着', '反映', '导致', 'because', 'driven by', 'economics',
                                          'unit economics', '经济', 'means', 'implies', 'reflects', 'as a result', 'due to'),
    'comparison/context': ('对标', '竞品', '竞争', '同行', '同业', '替代', 'benchmark', 'peer', 'comparable', '相比', '高于', '低于',
                           'compared', 'versus', ' vs', 'median', 'relative to', 'than'),
    'counter-evidence/risk': ('风险', '失败', '局限', '不确定', '挑战', '压力', '下行', '反过来', 'counter', 'bear case',
                              'downside', 'however', 'risk', 'weaken', 'contradict'),
    'investor implication': ('投资', '决策', '估值', '条款', '建议', '买入', '卖出', '持有', '等待', 'watchlist', 'implication',
                             'investor', 'valuation', 'position', 'thesis', 'recommend'),
    'open diligence': ('待验证', '尽调', '待核实', '下一步', '仍需确认', '需要核实', 'diligence', 'follow-up', 'open question',
                       'to verify', 'unverified', 'to confirm', 'not disclosed'),
    'confidence/calibration': ('置信', 'confidence', 'high', 'medium', 'low', '高', '中', '低', '把握', '确定性', '可信度'),
}
# check_depth.py counts these words as source mentions, with URLs and source tags.
SOURCE_MENTION_RE = re.compile(r'来源|Source|source|据|披露|公告|年报|招股书|专利|监管|新闻|报告'
                               r'|filing|10-K|10-Q|8-K|annual report|disclosed|according to|reported')

# check_depth.py SHALLOW_PHRASES, and the English ones this app has used since Phase 1.
SHALLOW_PHRASES = ('市场空间广阔', '团队背景强', '技术壁垒高', '商业模式清晰', '竞争激烈', '风险可控', '发展前景良好', '具有较大潜力',
                   'huge market', 'massive opportunity', 'strong team', 'high barriers to entry', 'clear business model',
                   'fierce competition', 'risks are manageable', 'bright future', 'significant potential',
                   'well positioned', 'well-positioned', 'best-in-class', 'world-class')
# check_depth.py VAGUE_PATTERNS (more than two fail a section), with English added.
VAGUE_PATTERNS = (
    r'(?:approximately|大约|约|大概|左右)\s*\d+',
    r'(?:毕业于|曾在|工作于)(?:知名|著名|顶尖|一流)(?:大学|公司|企业|机构)',
    r'(?:持有|拥有)(?:大量|众多|多个|多项)(?:专利|知识产权)',
    r'(?:团队|创始人|高管)(?:经验丰富|背景优秀|能力突出)',
    r'(?:估值|营收|利润)(?:合理|可观|良好|不错)',
    r'未公开(?:\s*披露)?\s*(?:具体)?(?:\s*数据|\s*信息)?(?:\.|。)',
    r'\b(?:roughly|around|about)\s+\$?\d',
    r'\b(?:many|numerous|several)\s+(?:patents|customers|partners)\b',
    r'\b(?:graduated from|worked at) (?:a )?(?:top|leading|prestigious|well-known) (?:university|company|firm)',
    r'\b(?:team|founders|management)\s+(?:is|are)\s+(?:experienced|strong|excellent)\b',
    r'\b(?:valuation|revenue|profit)\s+(?:is|looks)\s+(?:reasonable|decent|good|solid)\b',
)
MAX_VAGUE = 2
# check_depth.py FINAL_REPORT_FORBIDDEN_PATTERNS (writing about how the report is made), with English added.
FORBIDDEN_PATTERNS = (
    r'不能被写成', r'要把证据等级', r'而不是把材料拆成孤立事实', r'同时处理证据、反证、机制和投资含义', r'source\s*ID只用于锁定证据来源',
    r'必须放回[^。]{0,40}自身语境判断', r'关键原件在18-24个月内无法提供', r'先核实目标公司真实控制什么，再讨论行业空间', r'本节应支持',
    r'\bthis (?:part|section|report|memo) (?:should|must|will|needs to)\b', r'\bas (?:briefed|instructed)\b',
    r'\bevidence gate\b', r'\bpart check\b', r'\bsection check\b', r'\bthe brief asked\b', r'\bsource IDs? (?:are|is) only\b',
)
# check_depth.py PER_SECTION_FILLER_TERMS.
SECTION_FILLER = ('原件优先级应按3层推进', '这些ID只说明证据来源，不替代原件尽调', '公开来源与公司材料交叉校验', '不为未验证里程碑一次性定价')
# check_depth.py BOILERPLATE_LIMITS: (pattern, most allowed in the whole report), with English scaffolds added.
BOILERPLATE_LIMITS = (
    ('投资人读法', 2), ('class="source-note"', 2), ('引用锚点', 1), ('原件优先级应按3层推进', 1),
    ('第一层是能否证明目标公司真实拥有资产、人员和合同', 1), ('这些ID只说明证据来源，不替代原件尽调', 1),
    ('还需要单独检查2026年预算、2027年里程碑', 1), ('公开来源与公司材料交叉校验', 4), ('不为未验证里程碑一次性定价', 3),
    ('相比只看赛道热度', 2), ('交易结构含义也很直接', 2), ('因此本节的投资含义', 3), ('经济机制：', 4), ('比较与基准：', 4),
    ('反证与风险：', 4), ('投资含义：', 4), ('判断：[^。]{0,80}要把证据等级、经济机制、替代方案、反证和投资动作放在同一条逻辑链', 1),
    ('里的经济机制要通过注册证、医生采用、患者依从、支付路径、渠道复购和真实回款共同解释', 1), ('的benchmark：', 1), ('原件优先级：', 1),
    ('决策门槛：', 1), ('决策清单：', 1),
    ('How investors should read this', 2), ('Economic mechanism:', 4), ('Comparison and benchmark:', 4),
    ('Counter-evidence and risk:', 4), ('Investor implication:', 4), ('Decision threshold:', 1), ('Decision checklist:', 1),
)
INTERNAL_WRITING_TERMS = ('不能被写成', '要把证据等级', '而不是把材料拆成孤立事实', '同时处理证据、反证、机制和投资含义', 'source ID只用于锁定证据来源')


def strip_html(markup: str) -> str:
    """Visible text: style and script removed (check_depth.py skipped this, so CSS counted as text), tags dropped,
    entities decoded and whitespace collapsed."""
    text = TAG_RE.sub(' ', STYLE_SCRIPT_RE.sub(' ', markup))
    return re.sub(r'\s+', ' ', html.unescape(text)).strip()


def source_ids(text: str) -> set[str]:
    return set(SOURCE_ID_RE.findall(URL_RE.sub('', text)))


def numbers(text: str) -> list[str]:
    """Numeric facts as check_depth.py counts them, without the digits of source IDs and URLs."""
    return NUMBER_RE.findall(SOURCE_ID_RE.sub(' ', URL_RE.sub(' ', text)))


def missing_groups(text: str, groups: dict[str, tuple[str, ...]]) -> list[str]:
    lowered = text.lower()
    return [name for name, words in groups.items() if not any(word.lower() in lowered for word in words)]


def has_placeholder(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(r'(?<![a-z])' + re.escape(term) + r'(?![a-z])', lowered) if term.isascii() else term in lowered
               for term in PLACEHOLDER_TERMS)
