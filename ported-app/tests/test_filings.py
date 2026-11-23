import copy

import httpx
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
    with pytest.raises(ValueError, match='form must be 10-K, 10-Q, 8-K or DEF 14A'):
        read(sec_fetch, form='S-1', item='1')


def test_a_10q_item_2_is_the_discussion_not_part_ii(sec_fetch):
    result = read(sec_fetch, document=QUARTERLY, form='10-Q', item='2')
    assert "Item 2 (Management's Discussion and Analysis)" in result.text
    assert 'Net sales rose 16% in the quarter' in result.text and 'Unregistered' not in result.text
    assert 'for the period ending 2026-06-27' in result.text


ARCHIVE = 'https://www.sec.gov/Archives/edgar/data/320193/'
DOCUMENTS = {
    ARCHIVE + '000032019325000079/aapl-20250927.htm': 'sec_10k_aapl_more_items.htm',
    ARCHIVE + '000032019325000079/0000320193-25-000079-index.htm': 'sec_index_aapl_10k.htm',
    ARCHIVE + '000032019325000079/a10-kexhibit21109272025.htm': 'sec_ex21_aapl.htm',
    ARCHIVE + '000032019326000018/aapl-20260730.htm': 'sec_8k_aapl.htm',
    ARCHIVE + '000032019326000018/0000320193-26-000018-index.htm': 'sec_index_aapl_8k.htm',
    ARCHIVE + '000032019326000018/a8-kex991q3202606272026.htm': 'sec_ex991_aapl.htm',
    ARCHIVE + '000114036126015711/ef20071035_8k.htm': 'sec_8k_aapl_502.htm',
    ARCHIVE + '000114036126015711/0001140361-26-015711-index.htm': 'sec_index_aapl_8k_502.htm',
    ARCHIVE + '000130817926000008/aapl014016-def14a.htm': 'sec_def14a_aapl.htm',
}


def recorded(url: str) -> str:
    """The recorded documents of Apple's filings; any other URL is offline."""
    if url not in DOCUMENTS:
        raise httpx.ConnectError(f'offline: {url}')
    return (FIXTURES / DOCUMENTS[url]).read_text()


def read_recorded(sec_fetch, **kwargs):
    return filings.read_filing('AAPL', fetch=sec_fetch, fetch_document=recorded, **kwargs)


def test_more_10k_items_are_read_and_part_iii_points_to_the_proxy(sec_fetch):
    cyber = read_recorded(sec_fetch, form='10-K', item='1c')
    assert 'Item 1C (Cybersecurity). Page 1 of 1' in cyber.text
    assert 'Head of Corporate Information Security' in cyber.text
    for item in ('1B', '2', '3', '4', '5', '9A'):
        assert f'Item {item} (' in read_recorded(sec_fetch, form='10-K', item=item).text
    pay = read_recorded(sec_fetch, form='10-K', item='11').text
    assert pay.splitlines()[0].endswith('Item 11 (Executive Compensation). Page 1 of 1 (156 characters). This item is '
                                        'incorporated by reference to the proxy statement; read form DEF 14A, section '
                                        'compensation.')
    assert 'section auditor.' in read_recorded(sec_fetch, form='10-K', item='14').text.splitlines()[0]
    assert 'incorporated by reference' not in read_recorded(sec_fetch, form='10-K', item='2').text.splitlines()[0]


def test_exhibit_21_comes_from_the_filing_index(sec_fetch):
    result = read_recorded(sec_fetch, form='10-K', item='EX-21')
    header, _, body = result.text.partition('\n\n')
    assert header.endswith('(accession 0000320193-25-000079): Exhibit 21, subsidiaries of the registrant. Page 1 of 1 '
                           f'({len(body):,} characters).')
    assert 'Apple Distribution International Limited Ireland' in body
    [source] = result.sources
    assert source['label'].endswith('/000032019325000079/a10-kexhibit21109272025.htm')
    assert read_recorded(sec_fetch, form='10-K', item='21').text == result.text


def test_an_8k_item_is_read_from_the_latest_8k_reporting_it_with_its_press_release(sec_fetch):
    result = read_recorded(sec_fetch, form='8-K', item='2.02')
    header = result.text.splitlines()[0]
    assert header.startswith('Apple Inc. 8-K reporting 2026-07-30, filed 2026-07-30 (accession 0000320193-26-000018): '
                             'Item 2.02 (Results of Operations and Financial Condition), then exhibit 99.1 (the press '
                             'release). Page 1 of 1')
    assert 'issued a press release regarding Apple’s financial results' in result.text
    assert 'Exhibit 99.1 (press release, ' + ARCHIVE + '000032019326000018/a8-kex991q3202606272026.htm):' in result.text
    assert 'Apple reports third quarter results' in result.text
    assert result.sources[0]['title'] == 'Apple Inc. 8-K reporting 2026-07-30'


def test_8k_items_choose_their_filing_and_the_release_reads_alone(sec_fetch):
    departure = read_recorded(sec_fetch, form='8-K', item='5.02').text
    assert '(accession 0001140361-26-015711): Item 5.02 (Departure or Election of Directors and Officers' in departure
    assert 'Tim Cook will transition from his role as Chief Executive Officer' in departure
    assert 'press release' not in departure.splitlines()[0]  # that 8-K has no exhibit 99
    release = read_recorded(sec_fetch, form='8-K', item='EX-99.1').text
    assert ': Exhibit 99.1 (press release). Page 1 of 1' in release and 'Item 2.02' not in release
    assert 'Item 2.02 Results of Operations' in read_recorded(sec_fetch, form='8-K', item='').text


def test_8k_items_that_are_missing_or_unknown(sec_fetch):
    submissions = copy.deepcopy(sec_fetch('https://data.sec.gov/submissions/CIK0000320193.json'))
    recent = submissions['filings']['recent']
    recent['items'] = [items.replace('7.01', '8.01') for items in recent['items']]  # no Regulation FD 8-K
    without_fd = lambda url: submissions if 'submissions' in url else sec_fetch(url)
    with pytest.raises(ValueError, match='No 8-K filing reporting Item 7.01 found for AAPL'):
        read_recorded(without_fd, form='8-K', item='7.01')
    with pytest.raises(ValueError, match=r'8-K items are 2.02, 5.02, 7.01, 8.01, 9.01, 99.1'):
        read_recorded(sec_fetch, form='8-K', item='7')
    with pytest.raises(ValueError, match='Item 8.01 not found in this 8-K; its items are 2.02, 9.01'):
        read_recorded(sec_fetch, form='8-K', item='8.01', accession='0000320193-26-000018')


def test_an_8k_item_reads_without_its_release_when_the_index_is_unreachable(sec_fetch):
    def no_index(url: str) -> str:
        if url.endswith('-index.htm'):
            raise httpx.ConnectError('offline')
        return recorded(url)
    text = filings.read_filing('AAPL', '8-K', '2.02', fetch=sec_fetch, fetch_document=no_index).text
    assert 'Item 2.02 (Results of Operations and Financial Condition); its exhibit index could not be read.' in text


def test_proxy_sections_are_found_by_their_headings(sec_fetch):
    openings = {'directors': 'Nominees for Election', 'compensation': 'Compensation Discussion and Analysis',
                'ownership': 'Security Ownership of Certain Beneficial Owners and Management',
                'related': 'Related Party Policy and Transactions', 'committees': 'Board and Committee Structure',
                'auditor': 'Fees Paid to Auditors'}
    for section, opening in openings.items():
        result = read_recorded(sec_fetch, form='DEF 14A', item=section)
        header, _, body = result.text.partition('\n\n')
        assert '(found by its heading)' in header and body.startswith(opening), section
    header = read_recorded(sec_fetch, form='DEF 14A', item='cd&a').text.splitlines()[0]
    assert header.startswith('Apple Inc. DEF 14A for the meeting of 2026-02-24, filed 2026-01-08 (accession '
                             '0001308179-26-000008): Compensation discussion and analysis (found by its heading).')


def test_proxy_sections_skip_contents_entries_and_running_headers():
    text = filings.html_to_text((FIXTURES / 'sec_def14a_aapl.htm').read_text())
    directors = filings.proxy_section(text, 'directors')
    # The contents list "Nominees / for Election / 25" first; the section is the later heading with the bios.
    assert directors.startswith('Nominees for Election\nThe matrix on the following page highlights')
    assert 'Art Levinson' in directors and 'Compensation of Directors' not in directors
    # The page header (Summary, Governance, Directors, ... Other, Information) does not end a section,
    # and "Our 2025 Named / Executive Officers" inside the CD&A is not a heading.
    pay = filings.proxy_section(text, 'compensation')
    assert 'Our 2025 Named\nExecutive Officers\nTim Cook' in pay and pay.count('Information') >= 1
    assert 'People and Compensation Committee Report' not in pay


def test_tesla_proxy_gives_directors_then_executive_officers_and_drops_zero_width_spaces():
    raw = (FIXTURES / 'sec_def14a_tsla.htm').read_text()
    assert '&#8203;' in raw
    text = filings.html_to_text(raw)
    assert '\u200b' not in text
    directors = filings.proxy_section(text, 'directors')
    board, officers = directors.split('\n\n')
    assert board.startswith('Information Regarding the Board and Director Nominees')
    assert officers.startswith('Executive Officers\nThe names of Tesla’s executive officers, their ages')
    assert 'Vaibhav Taneja\n48\nChief Financial Officer' in officers
    related = filings.proxy_section(text, 'related')
    assert related.startswith('Certain Relationships and Related Person Transactions\nReview of Related Person')
    assert 'SpaceX is party to certain commercial' in related and 'Ownership of Securities' not in related


def test_a_proxy_section_without_a_heading_falls_back_to_its_keywords(sec_fetch):
    tesla = lambda url: (FIXTURES / 'sec_def14a_tsla.htm').read_text()
    result = filings.read_filing('AAPL', 'DEF 14A', 'compensation', fetch=sec_fetch, fetch_document=tesla)
    header, _, body = result.text.partition('\n\n')
    assert ('Compensation discussion and analysis (no heading found), paragraphs mentioning compensation discussion.'
            in header)
    assert body.splitlines() == ['Compensation Discussion and Analysis']
    with pytest.raises(ValueError, match='No paragraph in Principal accountant fees and services'):
        filings.read_filing('AAPL', 'DEF 14A', 'auditor', fetch=sec_fetch, fetch_document=tesla)
    with pytest.raises(ValueError, match='DEF 14A sections are directors, compensation, ownership, related'):
        filings.read_filing('AAPL', 'DEF 14A', '7', fetch=sec_fetch, fetch_document=tesla)
