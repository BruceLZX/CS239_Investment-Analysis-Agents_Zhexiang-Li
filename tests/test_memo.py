from tools import memo
from tools.memo import check_memo

FILING = {'id': 'S1', 'source_type': 'primary'}
PRICES = {'id': 'S2', 'source_type': 'market data'}
DECK = {'id': 'S3', 'source_type': 'company-provided'}
MEDIA = {'id': 'S4', 'source_type': 'independent'}
SOURCES = [FILING, PRICES, DECK, MEDIA]
DISCLAIMER = 'For research purposes only; not investment advice.'
CLEAN = f'Revenue grew 6% to $416.2B in FY2025 [S1].\n\nThe stock closed at 348.22 [S2].\n\n{DISCLAIMER}'


def rules(report: dict) -> list[str]:
    return [finding['rule'] for finding in report['findings']]


def test_a_clean_report_has_no_findings():
    report = check_memo(CLEAN, SOURCES, 'Watchlist', listed=True)
    assert report['findings'] == []
    assert report['cited_registered_ids'] == ['S1', 'S2']


def test_n1_source_ids_missing_from_the_register_are_flagged():
    report = check_memo(CLEAN + '\n\nMargins expanded [S9].', SOURCES)
    assert rules(report) == ['N1']
    assert 'S9' in report['findings'][0]['detail']


def test_s_numbers_inside_urls_are_not_citations():
    # Found in a live run: ScienceDirect's article URL ".../pii/S2772375524000595" was read as a citation.
    linked = CLEAN + '\n\nField robot study: https://www.sciencedirect.com/science/article/pii/S2772375524000595 [S4]'
    assert check_memo(linked, SOURCES)['findings'] == []


def test_n2_is_judged_per_paragraph_so_one_tag_covers_a_paragraph():
    # A section is capped at six inline tags, so a paragraph is cited once, not every sentence.
    paragraph = 'Revenue grew 6% to $416.2B. Services reached 26% of sales. Margins rose 170bp [S1].'
    assert rules(check_memo(paragraph, SOURCES)) == ['disclosure']
    report = check_memo(CLEAN + '\n\nServices margin is 75% according to analysts in 2025.', SOURCES)
    assert rules(report) == ['N2']
    assert report['findings'][0]['examples'] == ['Services margin is 75% according to analysts in 2025.']


def test_table_rows_carry_their_own_sources_and_headers_are_not_figures():
    table = '| Year | FY2024 | FY2025 | Source |\n|---|---|---|---|\n| Revenue | $391B | $416B | S1 |\n| Margin | 46% | 47% | |'
    report = check_memo(table, SOURCES)
    assert rules(report) == ['N2', 'disclosure'] and report['findings'][0]['examples'] == ['| Margin | 46% | 47% | |']


def test_dates_years_forms_small_ordinals_and_component_fences_are_not_figures():
    text = ('::: timeline\nThe 10-K for FY2025, filed 2025-10-31, lists 3 segments and Item 7 discusses Model 3 '
            'pricing.\n:::')
    assert memo.material_numbers(text) == []
    assert check_memo(text + f'\n\n{DISCLAIMER}', SOURCES)['findings'] == []


def test_n3_company_claims_need_a_verification_status():
    report = check_memo('The robot picks 94% of ripe fruit [S3].', SOURCES)
    assert 'N3' in rules(report)
    labelled = check_memo(f'The robot picks 94% of ripe fruit, a company-provided figure not independently verified '
                          f'[S3].\n\n{DISCLAIMER}', SOURCES)
    assert labelled['findings'] == []
    chinese = check_memo(f'机器人采摘率94%（公司提供，未独立验证）[S3]。\n\n{DISCLAIMER}', SOURCES)
    assert chinese['findings'] == []


def test_n4_listed_directional_ratings_need_a_filing_and_market_data():
    assert check_memo(CLEAN, SOURCES, 'Buy', listed=True)['findings'] == []
    filing_only = f'Revenue grew 6% to $416.2B in FY2025 [S1].\n\n{DISCLAIMER}'
    assert rules(check_memo(filing_only, [FILING, MEDIA], 'Sell', listed=True)) == ['N4']
    assert check_memo(filing_only, [FILING, MEDIA], 'Watchlist', listed=True)['findings'] == []


def test_n4_committing_to_a_private_company_needs_an_independent_source():
    deck_only = f'Pilots grew 3x, company-provided and unverified [S3].\n\n{DISCLAIMER}'
    assert rules(check_memo(deck_only, SOURCES, 'Invest now', listed=False)) == ['N4']
    assert check_memo(deck_only, SOURCES, 'Wait for milestone', listed=False)['findings'] == []


def test_n6_internal_working_material_and_team_names_are_flagged():
    for leak in ('As the Valuation Analyst found, the margin holds.', 'Per the evidence matrix, margins rose.',
                 'The must-fix items from R2 are resolved.', 'Saved with save_memo_part.', '证据矩阵显示毛利率上升。'):
        assert 'N6' in rules(check_memo(f'{leak}\n\n{DISCLAIMER}', SOURCES)), leak


def test_a_missing_disclaimer_is_flagged():
    assert rules(check_memo('Revenue grew [S1].', SOURCES)) == ['disclosure']


def test_citation_pattern_finds_ids_next_to_chinese_text():
    assert memo.cited_ids('来源S1，见S12。') == {'S1', 'S12'}
