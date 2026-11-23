import json

import httpx
import pytest

from tools import records

from .helpers import FIXTURES


def text_of(name: str) -> str:
    return (FIXTURES / name).read_text()


class Recorded:
    """Serves recorded responses by URL (and, where one URL serves several searches, by what is asked), and keeps
    every request so tests can check what was sent."""

    def __init__(self, routes: dict):
        self.routes, self.calls = routes, []

    def __call__(self, url: str, params: dict | None = None, body: dict | None = None) -> tuple[int, str]:
        self.calls.append((url, params, body))
        route = self.routes[url]
        status, name = route(params, body) if callable(route) else route
        return status, text_of(name) if name.endswith(('.json', '.xml')) else name


OPENFDA = 'https://api.fda.gov/{}.json'


def test_device_search_lists_clearances_and_approvals_newest_first():
    fetch = Recorded({OPENFDA.format('device/510k'): (200, 'openfda_510k_cgm.json'),
                      OPENFDA.format('device/pma'): (200, 'openfda_pma_cgm.json')})
    result = records.search_public_records('openfda_device', 'continuous glucose monitor', 2, fetch)
    lines = result.text.splitlines()
    assert lines[2] == ('FDA 510(k) clearances and De Novo grants (openFDA device/510k), newest decision first: 29 '
                        'found, showing 2.')
    assert lines[3] == ('1. DEN250049 | Libre Duo 10 Day Continuous Dual Glucose Ketone Monitoring System (Abbott '
                        'Diabetes Care) | 2026-08-25 | De Novo decision DENG; product code SJD | '
                        'https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/denovo.cfm?id=DEN250049')
    assert lines[4].startswith('2. K261402 | Dexcom G7 Continuous Glucose Monitoring System')
    assert '510(k) decision SESE Substantially Equivalent' in lines[4] and lines[4].endswith('pmn.cfm?ID=K261402')
    assert lines[7].startswith('1. P160048/S031 | Eversense® Continuous Glucose Monitoring System (Senseonics, '
                               'Incorporated) | 2026-03-19 | PMA decision APPR; Normal 180 Day Track No User Fee: '
                               'Postapproval Study Protocol | ')
    assert lines[7].endswith('cfpma/pma.cfm?id=P160048S031')
    # Every word, as a prefix, in one of the name fields: "monitor*" finds "Monitoring".
    _, params, _ = fetch.calls[0]
    assert params == {'search': 'device_name:(continuous* AND glucose* AND monitor*) applicant:(continuous* AND '
                                'glucose* AND monitor*) openfda.device_name:(continuous* AND glucose* AND monitor*)',
                      'limit': 2, 'sort': 'decision_date:desc'}
    assert len(result.sources) == 4 and {s['source_type'] for s in result.sources} == {'primary'}
    assert result.sources[0]['title'].startswith('FDA 510(k) DEN250049: Libre Duo')
    assert result.sources[0]['date'] == '2026-08-25' and result.sources[0]['label'] == 'FDA 510(k) DEN250049'


def test_a_query_in_openfda_syntax_goes_as_written_and_two_lists_share_the_record_budget():
    fetch = Recorded({OPENFDA.format('device/510k'): (200, 'openfda_510k_cgm.json'),
                      OPENFDA.format('device/pma'): (200, 'openfda_pma_cgm.json')})
    records.search_public_records('openfda_device', 'product_code:QBJ', 50, fetch)
    assert [params['search'] for _, params, _ in fetch.calls] == ['product_code:QBJ'] * 2
    assert [params['limit'] for _, params, _ in fetch.calls] == [10, 10]


def test_drug_applications_give_their_latest_submission_and_first_approval():
    fetch = Recorded({OPENFDA.format('drug/drugsfda'): (200, 'openfda_drugsfda_semaglutide.json')})
    lines = records.search_public_records('openfda_drug', 'semaglutide', 10, fetch).text.splitlines()
    assert lines[2] == 'Drugs@FDA applications (openFDA drug/drugsfda), latest submission first: 2 found.'
    assert lines[3] == ('1. NDA213051 | OZEMPIC, RYBELSUS (semaglutide), NOVO | 2026-01-30 | latest submission SUPPL 30 '
                        'status AP (Labeling); original approval 2019-09-20 | https://www.accessdata.fda.gov/scripts/'
                        'cder/daf/index.cfm?event=overview.process&ApplNo=213051')
    assert lines[4].startswith('2. ANDA220314 | SEMAGLUTIDE (semaglutide), APOTEX INC | 2026-04-07 | latest submission '
                               'ORIG 1 status TA (n/a) |')


def test_no_match_is_an_empty_list_and_a_server_error_is_an_error():
    fetch = Recorded({OPENFDA.format('drug/drugsfda'): (404, 'openfda_not_found.json')})
    result = records.search_public_records('openfda_drug', 'continuous glucose monitor', 10, fetch)
    assert result.text.endswith('latest submission first: 0 found.\nNo records match.') and result.sources == []
    fetch = Recorded({OPENFDA.format('drug/drugsfda'): (500, 'openfda_server_error.json')})
    with pytest.raises(ValueError, match='openFDA drug/drugsfda answered 500: Check your request and try again'):
        records.search_public_records('openfda_drug', 'insulin', 10, fetch)


def test_recalls_cover_devices_and_drugs():
    fetch = Recorded({OPENFDA.format('device/recall'): (200, 'openfda_device_recall_cgm.json'),
                      OPENFDA.format('drug/enforcement'): (200, 'openfda_drug_enforcement_insulin.json')})
    lines = records.search_public_records('openfda_recalls', 'insulin', 10, fetch).text.splitlines()
    assert lines[3].startswith('1. Z-0203-2027 | CareLink Clinic, REF: MMT-7350 (Medtronic MiniMed, Inc.) | 2026-09-11 | '
                               'Open, Classified; root cause: Software design | ')
    assert lines[3].endswith('cfRES/res.cfm?id=222434')
    drug = next(line for line in lines if line.startswith('1. D-0615-2021'))
    assert ' | 2021-03-22 | Class I, Terminated; Temperature Abuse' in drug
    assert drug.endswith('https://api.fda.gov/drug/enforcement.json?search=recall_number:%22D-0615-2021%22')


TRIALS = 'https://clinicaltrials.gov/api/v2/studies'


def test_trials_come_most_recently_updated_first_with_status_and_phase():
    fetch = Recorded({TRIALS: (200, 'clinicaltrials_cgm.json')})
    result = records.search_public_records('clinicaltrials', 'continuous glucose monitor', 3, fetch)
    lines = result.text.splitlines()
    assert lines[2] == ('ClinicalTrials.gov studies, most recently updated first (date = last update): 1,906 found, '
                        'showing 3.')
    assert lines[3] == ('1. NCT06848361 | Helping Adults With Type 2 Diabetes Use Their Health Data for Healthy Diabetes '
                        'Self-Management (Ann-Marie Rosland) | 2026-10-29 | active not recruiting, no phase; started '
                        '2025-04-28, primary completion 2026-12; enrollment 80 | https://clinicaltrials.gov/study/NCT06848361')
    _, params, _ = fetch.calls[0]
    assert params['query.term'] == 'continuous glucose monitor' and params['sort'] == 'LastUpdatePostDate:desc'


def test_trials_none_found_and_a_refused_request():
    assert 'No records match.' in records.search_public_records(
        'clinicaltrials', 'zzqq', 3, Recorded({TRIALS: (200, 'clinicaltrials_none.json')})).text
    with pytest.raises(ValueError, match='ClinicalTrials.gov answered 400: Unknown sort field'):
        records.search_public_records('clinicaltrials', 'x', 3, Recorded({TRIALS: (400, 'Unknown sort field')}))


NHTSA = 'https://api.nhtsa.gov/'


def vehicles(recalls: tuple[int, str]) -> Recorded:
    return Recorded({NHTSA + 'products/vehicle/makes': (200, 'nhtsa_makes_2026.json'),
                     NHTSA + 'products/vehicle/models': (200, 'nhtsa_models_tesla_2026.json'),
                     NHTSA + 'recalls/recallsByVehicle': recalls})


def test_vehicle_recalls_by_make_model_and_year():
    fetch = vehicles((200, 'nhtsa_recalls_tesla_model_y_2026.json'))
    lines = records.search_public_records('nhtsa_recalls', 'tesla model y 2026', 10, fetch).text.splitlines()
    assert lines[2] == 'NHTSA recall campaigns for TESLA MODEL Y, model years 2026-2026, newest report first: 3 found.'
    # NHTSA lists the oldest campaign first; the result puts the newest report first.
    assert [line.split(' | ')[0] for line in lines[3:6]] == ['1. 25V490000', '2. 25V410000', '3. 25V359000']
    assert lines[5].startswith('3. 25V359000 | VISIBILITY:WINDSHIELD WIPER/WASHER:LINKAGES: Tesla, Inc. (Tesla) is '
                               'recalling certain 2026 Model Y vehicles.')
    assert lines[5].endswith(' | 2025-05-30 | affects 2026 MODEL Y | https://www.nhtsa.gov/recalls?nhtsaId=25V359000')
    # The models list repeats MODEL Y; it is asked for once.
    asked = [params for url, params, _ in fetch.calls if url.endswith('recallsByVehicle')]
    assert asked == [{'make': 'TESLA', 'model': 'MODEL Y', 'modelYear': 2026}]


def test_vehicle_recalls_none_found_and_an_unknown_make():
    empty = records.search_public_records('nhtsa_recalls', 'Tesla Cybertruck 2026', 10,
                                          vehicles((400, 'nhtsa_recalls_none.json')))
    assert empty.text.endswith('newest report first: 0 found.\nNo records match.')
    with pytest.raises(ValueError, match="No make in NHTSA's recall data for model years 2026-2026 starts the query"):
        records.search_public_records('nhtsa_recalls', 'Rivian R1S 2026', 10, vehicles((200, 'nhtsa_recalls_none.json')))


AWARDS = 'https://api.usaspending.gov/api/v2/search/{}/'


def awards(by_group: dict) -> Recorded:
    def search(params, body):
        return by_group[tuple(body['filters']['award_type_codes'])]
    return Recorded({AWARDS.format('spending_by_award_count'): (200, 'usaspending_count_tesla.json'),
                     AWARDS.format('spending_by_award'): search})


def test_federal_awards_by_recipient_list_each_award_group():
    fetch = awards({('A', 'B', 'C', 'D'): (200, 'usaspending_contracts_tesla.json'),
                    ('02', '03', '04', '05'): (200, 'usaspending_grants_tesla.json'),
                    ('07', '08'): (200, 'usaspending_loans_tesla.json')})
    result = records.search_public_records('usaspending', 'Tesla', 10, fetch)
    lines = result.text.splitlines()
    assert lines[2] == ("Federal contracts to recipients whose names contain 'Tesla' (USAspending, from fiscal 2008; "
                        'check each recipient is the company), largest first: 6,429 found, showing 2.')
    assert lines[3] == ('1. 80KSC026F0004 | TESLA LABORATORIES INC.: PROVIDE ENGINEERING SUPPORT TO SPECIAL PROJECTS | '
                        '2026-05-04 | $14,056,334, National Aeronautics and Space Administration, ends 2030-09-30 | '
                        'https://www.usaspending.gov/award/CONT_AWD_80KSC026F0004_8000_80KSC025A0010_8000')
    loan = next(line for line in lines if line.startswith('1. 9406545001'))
    assert ' | 2017-04-11 | $3,300,000, Small Business Administration | ' in loan
    posted = [body for url, _, body in fetch.calls if url.endswith('spending_by_award/')]
    assert [body['limit'] for body in posted] == [6, 6, 6]  # three groups share the 20-record budget
    assert posted[2]['sort'] == 'Loan Value' and 'Issued Date' in posted[2]['fields']
    assert len(result.sources) == 6


def test_no_awards_and_a_refused_award_search():
    fetch = Recorded({AWARDS.format('spending_by_award_count'): (200, '{"results": {"contracts": 0, "grants": 0}}')})
    assert records.search_public_records('usaspending', 'Nobody', 10, fetch).text.endswith('0 found.\nNo records match.')
    fetch = awards({('A', 'B', 'C', 'D'): (400, 'usaspending_bad_request.json')})
    with pytest.raises(ValueError, match="USAspending answered 400: Sort value 'Nope' not found"):
        records.search_public_records('usaspending', 'Tesla', 10, fetch)


EFTS = 'https://efts.sec.gov/LATEST/search-index'


def test_sec_full_text_search_links_each_document():
    fetch = Recorded({EFTS: (200, 'efts_cgm.json')})
    lines = records.search_public_records('sec_fulltext', '"continuous glucose monitor"', 3, fetch).text.splitlines()
    assert lines[2].startswith('SEC EDGAR full-text search, filings from ') and lines[2].endswith('813 found, showing 3.')
    assert lines[3] == ('1. 0001079973-19-000331 | Nemaura Medical Inc. (NMRD) (CIK 0001602078), 8-K EX-99.1 | '
                        '2019-05-29 | EXHIBIT 99.1, period 2019-05-29 | '
                        'https://www.sec.gov/Archives/edgar/data/1602078/000107997319000331/nmra_ex99x1.htm')
    _, params, _ = fetch.calls[0]
    assert params['q'] == '"continuous glucose monitor"' and params['dateRange'] == 'custom'


def test_sec_full_text_search_none_found_and_an_error():
    none = records.search_public_records('sec_fulltext', '"zzqq"', 3, Recorded({EFTS: (200, 'efts_none.json')}))
    assert none.text.endswith('0 found.\nNo records match.')
    with pytest.raises(ValueError, match='SEC full-text search answered 503'):
        records.search_public_records('sec_fulltext', 'x', 3, Recorded({EFTS: (503, 'Service Unavailable')}))


EUTILS = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/{}.fcgi'


def test_pubmed_gives_the_total_and_each_article_with_journal_year_and_doi():
    fetch = Recorded({EUTILS.format('esearch'): (200, 'pubmed_esearch_lithium.json'),
                      EUTILS.format('esummary'): (200, 'pubmed_esummary_lithium.json')})
    result = records.search_literature('pubmed', 'lithium battery', 3, fetch)
    lines = result.text.splitlines()
    assert lines[2] == 'PubMed articles, best match first (date = publication year): 31,997 found, showing 3.'
    assert lines[3] == ('1. PMID 30977440 | Risk assessment of lithium-ion battery explosion: chemical leakages | 2018 | '
                        'Park YJ, Kim MK, Kim HS et al.; J Toxicol Environ Health B Crit Rev; doi '
                        '10.1080/10937404.2019.1601815 | https://pubmed.ncbi.nlm.nih.gov/30977440/')
    assert {(s['source_type'], s['confidence']) for s in result.sources} == {('independent', 'high')}
    _, params, _ = fetch.calls[1]
    assert params['id'] == '30977440,37420774,33477513' and 'email' not in params


def test_pubmed_none_found_and_an_error():
    fetch = Recorded({EUTILS.format('esearch'): (200, 'pubmed_esearch_none.json')})
    assert records.search_literature('pubmed', 'zzqq', 3, fetch).text.endswith('0 found.\nNo records match.')
    with pytest.raises(ValueError, match='PubMed search answered 429'):
        records.search_literature('pubmed', 'x', 3, Recorded({EUTILS.format('esearch'): (429, 'Too Many Requests')}))


ARXIV = 'https://export.arxiv.org/api/query'


def test_arxiv_papers_with_authors_year_and_category():
    fetch = Recorded({ARXIV: (200, 'arxiv_lithium.xml')})
    result = records.search_literature('arxiv', 'lithium battery', 2, fetch)
    lines = result.text.splitlines()
    assert lines[2] == 'arXiv papers, best match first (date = first version year): 106 found, showing 2.'
    assert lines[3] == ('1. arXiv:2404.07577v1 | Generating Comprehensive Lithium Battery Charging Data with Generative '
                        'AI | 2024 | Lidang Jiang, Changyan Hu, Sibei Ji et al.; cs.LG | https://arxiv.org/abs/2404.07577v1')
    _, params, _ = fetch.calls[0]
    assert params['search_query'] == 'all:lithium AND all:battery'
    assert {s['confidence'] for s in result.sources} == {'medium'}  # preprints, not peer reviewed


def test_arxiv_none_found_and_its_error_feed():
    assert records.search_literature('arxiv', 'zzqq', 3, Recorded({ARXIV: (200, 'arxiv_none.xml')})).text.endswith(
        '0 found.\nNo records match.')
    with pytest.raises(ValueError, match='arXiv answered 400: max_results must be non-negative'):
        records.search_literature('arxiv', 'ti:lithium', 3, Recorded({ARXIV: (400, 'arxiv_error.xml')}))


def test_unknown_sources_and_empty_queries_are_rejected():
    with pytest.raises(ValueError, match='source must be one of openfda_device, openfda_drug'):
        records.search_public_records('fda', 'x')
    with pytest.raises(ValueError, match='source must be one of pubmed, arxiv'):
        records.search_literature('scholar', 'x')
    with pytest.raises(ValueError, match='The query is empty'):
        records.search_public_records('openfda_drug', '  ')


def test_only_sec_requests_carry_the_contact_and_responses_are_cached(tmp_path, monkeypatch):
    sent = []

    def respond(url, headers, **kwargs):
        sent.append((url, headers['User-Agent']))
        return httpx.Response(200, text=json.dumps({'ok': True}), request=httpx.Request('GET', url))
    monkeypatch.setattr(records, 'CACHE', tmp_path)
    monkeypatch.setattr(records.httpx, 'get', lambda url, params, headers, timeout, follow_redirects: respond(url, headers))
    monkeypatch.setattr(records.httpx, 'post', lambda url, json, headers, timeout: respond(url, headers))
    monkeypatch.setenv('SEC_USER_AGENT', 'Test Person test@example.com')
    records.fetch_url('https://efts.sec.gov/LATEST/search-index', {'q': 'a'})
    records.fetch_url('https://api.fda.gov/device/510k.json', {'search': 'a'})
    records.fetch_url('https://api.usaspending.gov/api/v2/search/spending_by_award/', None, {'filters': {}})
    assert records.fetch_url('https://api.fda.gov/device/510k.json', {'search': 'a'}) == (200, '{"ok": true}')
    assert sent == [('https://efts.sec.gov/LATEST/search-index', 'Test Person test@example.com'),
                    ('https://api.fda.gov/device/510k.json', 'investment-research-agents/1.0'),
                    ('https://api.usaspending.gov/api/v2/search/spending_by_award/', 'investment-research-agents/1.0')]
