from tools import memo
from tools.memo import check_memo

FILING = {'id': 'S1', 'source_type': 'primary filing'}
PRICES = {'id': 'S2', 'source_type': 'market data'}
DECK = {'id': 'S3', 'source_type': 'company-provided'}
MEDIA = {'id': 'S4', 'source_type': 'independent media'}
SOURCES = [FILING, PRICES, DECK, MEDIA]
DISCLOSURE = 'Data as of 2026-10-23. For research purposes only; not investment advice.'
CLEAN = f'Rating: Watchlist\nRevenue grew 6% to $416.2B in FY2025 [S1].\nThe stock closed at 348.22 [S2].\n{DISCLOSURE}'


def rules(report: dict) -> list[str]:
    return [finding['rule'] for finding in report['findings']]


def test_a_clean_memo_has_no_findings():
    report = check_memo(CLEAN, SOURCES)
    assert report['findings'] == []
    assert report['rating'] == 'watchlist'
    assert report['cited_registered_ids'] == ['S1', 'S2']


def test_n1_source_ids_missing_from_the_register_are_flagged():
    report = check_memo(CLEAN + '\nMargins expanded [S9].', SOURCES)
    assert rules(report) == ['N1']
    assert 'S9' in report['findings'][0]['detail']


def test_n2_numbers_without_sources_are_flagged_but_dates_and_years_are_not():
    report = check_memo(CLEAN + '\nServices margin is about 75% according to analysts in 2025.', SOURCES)
    assert rules(report) == ['N2']
    assert report['findings'][0]['examples'] == ['Services margin is about 75% according to analysts in 2025.']


def test_n3_company_claims_need_a_verification_status():
    assert rules(check_memo(CLEAN + '\nThe robot picks 94% of ripe fruit [S3].', SOURCES)) == ['N3']
    labelled = CLEAN + '\nThe robot picks 94% of ripe fruit (company-provided, not independently verified) [S3].'
    assert check_memo(labelled, SOURCES)['findings'] == []
    corroborated = CLEAN + '\nThe robot picks 94% of ripe fruit [S3][S4].'
    assert check_memo(corroborated, SOURCES)['findings'] == []


def test_n4_listed_ratings_need_a_filing_and_market_data():
    buy = CLEAN.replace('Rating: Watchlist', 'Rating: Buy')
    assert 'N4' in rules(check_memo(buy, [FILING]))
    assert 'N4' not in rules(check_memo(buy, SOURCES))


def test_n4_invest_needs_an_independent_source():
    deck_only = f'Rating: Invest\nARR reached $3.2M (company-provided, unverified) [S3].\n{DISCLOSURE}'
    assert rules(check_memo(deck_only, SOURCES)) == ['N4']
    corroborated = deck_only + '\nIndependent coverage confirms two paid deployments [S4].'
    assert check_memo(corroborated, SOURCES)['findings'] == []


def test_n6_internal_working_material_is_flagged():
    report = check_memo(CLEAN + '\nAs noted in evidence packet E1, the must-fix items from R1 are resolved.', SOURCES)
    assert rules(report) == ['N6']
    for word in ('E1', 'R1', 'evidence packet', 'must-fix'):
        assert word in report['findings'][0]['detail']


def test_missing_disclaimer_and_data_date_are_flagged():
    assert rules(check_memo('Rating: Hold\nRevenue grew 6% [S1].', SOURCES)) == ['disclosure', 'disclosure']


def test_citation_pattern_comes_from_the_skill():
    assert memo.SOURCE_ID_RE.pattern == r'\bS\d+\b'
