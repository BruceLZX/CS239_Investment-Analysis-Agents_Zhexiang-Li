"""Hand-written report sections that meet the skill's standard, for tests. The company, Northwind Devices (NWD), and
its figures are fictional."""


def source(source_id: str, source_type: str, location: str, title: str = '', confidence: str = 'high') -> dict:
    return {'id': source_id, 'title': title or f'Title {source_id}', 'source_type': source_type, 'location': location,
            'date': '2026-10-28', 'confidence': confidence, 'claims': f'claims of {source_id}',
            'registered_by': 'Fundamentals Analyst'}


SOURCES = [
    source('S1', 'primary', 'https://www.sec.gov/Archives/edgar/data/1/nwd-10k-2025.htm', 'Northwind 10-K FY2025'),
    source('S2', 'primary', 'https://www.sec.gov/Archives/edgar/data/1/nwd-10q-q3-2026.htm', 'Northwind 10-Q Q3 2026'),
    source('S3', 'market data', 'https://finance.yahoo.com/quote/NWD', 'NWD price and multiples', 'medium'),
    source('S4', 'primary', 'https://www.sec.gov/Archives/edgar/data/2/peers-10k.htm', 'Peer 10-K filings'),
    source('S5', 'independent', 'https://www.reuters.com/technology/device-price-war', 'Reuters: device price cuts'),
    source('S6', 'independent', 'https://www.idc.com/devices-2025', 'IDC device tracker'),
    source('S7', 'company-provided', 'sources/northwind_deck.pdf p.4', 'Northwind investor deck', 'low'),
    source('S8', 'near-primary', 'https://investors.northwind.example/attach-rate', 'Northwind IR: attach rate'),
]

FINANCIALS = """\
Northwind's earnings are better than its revenue line suggests, because a shift toward recurring software lifted \
margins while unit sales stalled. The investor question is whether that mix shift can keep paying for the hardware \
business that still produces most of the revenue.

Revenue rose 4.8% to $4.21 billion in FY2025, but the growth came almost entirely from subscriptions, which reached \
$1.12 billion and 26.6% of sales according to the annual 10-K filing [S1]. Hardware revenue fell 1.9% to $3.09 \
billion over the same period, so the company is growing on a narrowing base of device owners.

| Line item | FY2023 | FY2024 | FY2025 | Source |
|---|---|---|---|---|
| Revenue | $3.71B | $4.02B | $4.21B | S1 |
| Gross margin | 38.2% | 39.6% | 41.3% | S1 |
| Operating income | $402M | $455M | $517M | S1 |
| Free cash flow | $488M | $552M | $610M | S1, S2 |
| Net cash | $1.05B | $1.21B | $1.34B | S2 |

Gross margin expanded 170 basis points to 41.3% because subscription revenue carries a gross margin near 78%, \
against 28.1% for devices, as disclosed in the segment note. Compared with the peer median gross margin of 36.5% \
across four listed device makers, Northwind now earns a premium that its pricing alone does not explain [S1, S4].

Cash conversion is strong: free cash flow of $610 million equals 118% of net income, and the latest 10-Q shows net \
cash of $1.34 billion with no debt maturing before 2029 [S2]. However, receivables days rose from 41 to 52 in a \
year, which is the first sign that distributors are being given longer terms to keep devices moving.

| Measure | FY2024 | FY2025 | Peer median | Source |
|---|---|---|---|---|
| Return on invested capital | 17.4% | 19.8% | 12.1% | S1, S4 |
| Days sales outstanding | 41 | 52 | 44 | S1, S4 |
| Cash conversion cycle (days) | 33 | 46 | 38 | S1, S4 |

::: info warning
**Red flag:** receivables grew 31% while revenue grew 4.8%, and the allowance for doubtful accounts doubled to \
$18 million [S2].
:::

The notes add two smaller concerns. Stock-based compensation reached $142 million, or 3.4% of revenue, and \
capitalized software development rose to $96 million, which flatters operating income relative to cash spending \
reported in the filing [S1]. Neither changes the cash picture, but both make the reported margin look higher than \
the economic margin.

The variable that moves the outcome most is the subscription attach rate: each point of attach on the installed \
base adds $38 million of high-margin revenue, according to our sensitivity built on the 10-K disclosures. If attach \
stalls, the downside case is a business growing near zero with a hardware margin that peers have shown can fall \
quickly in a price war [S3, S5].

For investors, the statements support a quality business at a fair valuation rather than a cheap one; the \
receivables trend is the item that would change our position. Confidence is medium-high: the figures come from \
audited filings, but the receivables explanation still needs diligence with management to verify distributor terms.
"""

EXECUTIVE_SUMMARY = """\
::: verdict
| Rating | Action | Composite score | Confidence | Horizon | Source |
|---|---|---|---|---|---|
| Watchlist | Starter position below $38 | 6.7 / 10 | Medium | 12-18 months | S3 |
:::

Northwind trades at $41.20 on NASDAQ (2026-10-28), 24.1x trailing earnings against a peer median of 19.5x [S3]. \
The market is pricing in subscription growth that the evidence supports only in part, so our verdict is Watchlist \
with a starter position below $38.

::: briefing
| Card | Text | Source |
|---|---|---|
| Core positive: mix shift | Subscriptions reached 26.6% of revenue and carry a 78% gross margin. | S1 |
| Core positive: balance sheet | Net cash of $1.34 billion and no maturities before 2029. | S2 |
| Key risk: receivables | Days sales outstanding rose from 41 to 52 in FY2025. | S1 |
| Key risk: price war | Device peers cut prices 8% in 2025, the bear case for hardware margins. | S5 |
| Valuation and terms | 24.1x earnings is a 24% premium to peers for a business growing 4.8%. | S3 |
:::

::: efficiency
| Measure | Value | Source |
|---|---|---|
| Revenue FY2025 | $4.21B | S1 |
| Free cash flow | $610M | S1 |
| Gross margin | 41.3% | S1 |
| P/E (TTM) | 24.1x | S3 |
:::

The consensus view treats Northwind as a software company in the making; our non-consensus point is that the \
hardware base is shrinking faster than subscriptions can grow, so the premium needs proof. Evidence confidence is \
medium: the financials come from audited filings, while the attach-rate data is the company's own disclosure. \
Follow-up diligence should verify distributor terms behind the receivables jump.

::: one-question
What share of FY2026 subscription revenue comes from devices sold before FY2024?

The answer shows whether growth depends on a shrinking installed base, which would turn the rating from Watchlist \
to Avoid.
:::

::: takeaways
1. Subscriptions at 26.6% of revenue now drive the margin story [S1].
2. Receivables rising to 52 days is the leading risk signal [S1].
3. At 24.1x earnings the stock already prices in the mix shift [S3].
:::
"""

SCORING = """\
The composite score is 6.7, a quality business whose price already reflects most of the good news [S1, S3].

| Dimension | Weight | Score | Rationale | Source |
|---|---|---|---|---|
| Business quality and moat | 15% | 8 | Subscriptions carry a 78% margin | S1 |
| Growth and market | 10% | 6 | Revenue up 4.8% | S1 |
| Competitive position | 10% | 7 | Margin 4.8 points above peers | S4 |
| Earnings quality and financial strength | 20% | 7 | FCF 118% of net income | S1 |
| Valuation and margin of safety | 20% | 5 | 24.1x vs peer 19.5x | S3 |
| Management, governance and capital allocation | 10% | 7 | Net cash $1.34B | S2 |
| Balance-sheet and downside resilience | 10% | 8 | No maturities before 2029 | S2 |
| Catalysts and timing | 5% | 6 | Q4 results in February | S3 |
"""
