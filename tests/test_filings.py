import pytest

from tools import filings

from .helpers import FIXTURES

HTML = (FIXTURES / 'sec_10k_sample.htm').read_text()
QUARTERLY = """<div>PART I</div><div>Item 1. Financial Statements</div><p>Condensed statements.</p>
<div>Item 2. Management's Discussion and Analysis</div><p>Net sales rose 16% in the quarter, driven by iPhone.</p>
<p>Services net sales reached a record.</p>
<div>PART II</div><div>Item 1A. Risk Factors</div><p>No material changes.</p>
<div>Item 2. Unregistered Sales of Equity Securities</div><p>None.</p><div>SIGNATURES</div>"""


def read(sec_fetch, document: str = HTML, **kwargs):
    return filings.read_filing('AAPL', fetch=sec_fetch, fetch_document=lambda url: document, **kwargs)


def test_html_becomes_one_block_a_line_without_hidden_xbrl_or_scripts():
    text = filings.html_to_text(HTML)
    assert 'dei:DocumentType' not in text and 'var shown' not in text and '.bold' not in text
    assert 'The Company designs smartphones, personal computers, tablets and wearables, and sells services.' in text
    assert 'Item 7. Management’s Discussion and Analysis of Financial Condition and Results of Operations' in text.splitlines()


def test_an_item_is_its_body_not_its_table_of_contents_line():
    body = filings.find_item(filings.html_to_text(HTML), '7')
    assert body.splitlines()[0].startswith('Item 7. Management’s Discussion')
    assert 'Greater China net sales decreased 4%' in body and 'interest rate' not in body
    assert filings.find_item(filings.html_to_text(HTML), '7a').startswith('Item 7A. Quantitative')


def test_reading_an_item_names_the_filing_and_registers_it(sec_fetch):
    result = read(sec_fetch, form='10-K', item='1A')
    header, _, body = result.text.partition('\n\n')
    assert header.endswith('Item 1A (Risk Factors). Page 1 of 1 (226 characters).')
    assert 'filed 2025-10-31 (accession 0000320193-25-000079)' in header
    assert 'component and product manufacturing in Greater China' in body and 'Next: page' not in body
    [source] = result.sources
    assert source['source_type'] == 'primary filing'
    assert source['location'] == 'https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/'
    assert source['label'].endswith('/000032019325000079/aapl-20250927.htm')


def test_keywords_search_the_whole_filing_on_this_machine(sec_fetch):
    result = read(sec_fetch, form='10-K', item='', keywords=['Greater China'])
    header, _, body = result.text.partition('\n\n')
    assert 'the whole filing, paragraphs mentioning Greater China' in header
    assert len(body.splitlines()) == 3 and all('Greater China' in line for line in body.splitlines())
    with pytest.raises(ValueError, match='No paragraph in Item 7A'):
        read(sec_fetch, form='10-K', item='7A', keywords=['Greater China'])


def test_long_items_come_a_page_at_a_time(sec_fetch, monkeypatch):
    monkeypatch.setattr(filings, 'PAGE_CHARS', 120)
    first, second = read(sec_fetch, form='10-K', item='7'), read(sec_fetch, form='10-K', item='7', page=2)
    assert 'Page 1 of 3' in first.text and first.text.endswith('Next: page 2.')
    assert 'Page 2 of 3' in second.text and 'driven by higher net sales of iPhone and Services' in second.text


def test_a_missing_item_lists_the_items_there_are(sec_fetch):
    with pytest.raises(ValueError, match='its items are 1, 1A, 7, 7A, 8'):
        read(sec_fetch, form='10-K', item='9')
    with pytest.raises(ValueError, match='form must be 10-K or 10-Q'):
        read(sec_fetch, form='8-K', item='1')


def test_a_10q_item_2_is_the_discussion_not_part_ii(sec_fetch):
    result = read(sec_fetch, document=QUARTERLY, form='10-Q', item='2')
    assert "Item 2 (Management's Discussion and Analysis)" in result.text
    assert 'Net sales rose 16% in the quarter' in result.text and 'Unregistered' not in result.text
    assert 'for the period ending 2026-06-27' in result.text
