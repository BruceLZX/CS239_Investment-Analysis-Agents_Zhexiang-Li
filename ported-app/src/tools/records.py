"""Regulator records and research literature: FDA clearances, approvals and recalls, clinical trials, vehicle
recalls, federal awards, SEC full-text search, PubMed and arXiv.

A search comes back as short lists of records, each with its ID, title, date, status and link, and each record is a
source to cite. Requests to the SEC carry the SEC_USER_AGENT contact its fair-access policy asks for; every other
service gets a generic User-Agent with no personal details. Successful responses are cached for a day beside the SEC
responses.
"""
from collections.abc import Callable
from datetime import date, datetime, timezone
import hashlib
import json
import re
import time
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx

from . import sec_edgar
from .retrieved import Retrieved, source

CACHE = sec_edgar.CACHE.parent / 'records'
CACHE_SECONDS = 24 * 3600
USER_AGENT = 'investment-research-agents/1.0'
RECORD_SOURCES = ('openfda_device', 'openfda_drug', 'openfda_recalls', 'clinicaltrials', 'nhtsa_recalls',
                  'usaspending', 'sec_fulltext')
LITERATURE_SOURCES = ('pubmed', 'arxiv')
MAX_RECORDS = 20  # in all, across a search's lists, so the records and their sources fit in one tool result
OPENFDA_URL = 'https://api.fda.gov/{path}.json'
TRIALS_URL = 'https://clinicaltrials.gov/api/v2/studies'
TRIAL_FIELDS = ('NCTId,BriefTitle,OverallStatus,Phase,LeadSponsorName,StartDate,PrimaryCompletionDate,'
                'LastUpdatePostDate,EnrollmentCount')
NHTSA_URL = 'https://api.nhtsa.gov'
MAX_VEHICLES = 30  # (model year, model) pairs searched for one make
USASPENDING_URL = 'https://api.usaspending.gov/api/v2/search/{path}/'
# (name, award type codes, amount field): USAspending searches one group of award types at a time.
AWARD_GROUPS = (('contracts', ['A', 'B', 'C', 'D'], 'Award Amount'), ('grants', ['02', '03', '04', '05'], 'Award Amount'),
                ('loans', ['07', '08'], 'Loan Value'))
EFTS_URL = 'https://efts.sec.gov/LATEST/search-index'
FULLTEXT_YEARS = 5
EUTILS_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/{tool}.fcgi'
ARXIV_URL = 'https://export.arxiv.org/api/query'
ATOM = {'atom': 'http://www.w3.org/2005/Atom', 'opensearch': 'http://a9.com/-/spec/opensearch/1.1/',
        'arxiv': 'http://arxiv.org/schemas/atom'}
STOP_WORDS = {'a', 'an', 'and', 'or', 'not', 'the', 'of', 'for', 'with', 'in', 'on', 'to', 'by'}

Fetch = Callable[..., tuple[int, str]]  # (url, params=None, body=None) -> (HTTP status, text)


def fetch_url(url: str, params: dict | None = None, body: dict | None = None) -> tuple[int, str]:
    """GET the URL (or POST the JSON body) and return the status and text; a 200 response is cached for a day."""
    host = urlparse(url).hostname or ''
    agent = sec_edgar.user_agent() if host == 'sec.gov' or host.endswith('.sec.gov') else USER_AGENT
    CACHE.mkdir(parents=True, exist_ok=True)
    key = json.dumps([url, params, body], sort_keys=True)
    path = CACHE / f'{hashlib.sha256(key.encode()).hexdigest()[:32]}.txt'
    if path.exists() and time.time() - path.stat().st_mtime < CACHE_SECONDS:
        return 200, path.read_text()
    headers = {'User-Agent': agent}
    if body is None:
        response = httpx.get(url, params=params, headers=headers, timeout=30, follow_redirects=True)
    else:
        response = httpx.post(url, json=body, headers=headers, timeout=60)
    if response.status_code == 200:
        path.write_text(response.text)
    return response.status_code, response.text


def _json(text: str) -> dict:
    try:
        data = json.loads(text)
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _iso(day: str | None) -> str:
    """A date as YYYY-MM-DD from openFDA's YYYYMMDD or NHTSA's DD/MM/YYYY; other forms pass through."""
    day = (day or '').strip()
    if re.fullmatch(r'\d{8}', day):
        return f'{day[:4]}-{day[4:6]}-{day[6:]}'
    if match := re.fullmatch(r'(\d{2})/(\d{2})/(\d{4})', day):
        return f'{match[3]}-{match[2]}-{match[1]}'
    return day[:10]


def _short(text: str | None, most: int) -> str:
    text = ' '.join((text or '').split())
    return text if len(text) <= most else text[:most - 3].rstrip() + '...'


def _words(query: str) -> list[str]:
    words = [w for w in re.findall(r'[a-z0-9]+', query.lower()) if w not in STOP_WORDS and len(w) > 1]
    if not words:
        raise ValueError('The query has no words to search for.')
    return words


def _record(id: str, title: str, day: str, status: str, link: str) -> dict:
    return {'id': id, 'title': _short(title, 140), 'date': day, 'status': _short(status, 160), 'link': link}


def _years_before(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year - years)
    except ValueError:  # 29 February
        return day.replace(year=day.year - years, day=28)


# Each search gives lists: (heading, total found, records, kind), kind naming a record in its source's title.
Listing = tuple[str, int, list[dict], str]


def _openfda(path: str, query: str, fields: tuple[str, ...], sort: str | None, limit: int,
             fetch: Fetch) -> tuple[int, list[dict]]:
    """An openFDA search: every word of the query, matched as a prefix, in one of the fields; a query with a colon is
    openFDA syntax and goes as written. openFDA answers 404 NOT_FOUND when nothing matches."""
    terms = ' AND '.join(f'{word}*' for word in _words(query)) if ':' not in query else None
    search = query if terms is None else ' '.join(f'{field}:({terms})' for field in fields)
    params = {'search': search, 'limit': limit, **({'sort': sort} if sort else {})}
    status, text = fetch(OPENFDA_URL.format(path=path), params)
    data = _json(text)
    error = data.get('error') or {}
    if status == 404 and error.get('code') == 'NOT_FOUND':
        return 0, []
    if status != 200 or 'results' not in data:
        raise ValueError(f"openFDA {path} answered {status}: {error.get('message') or text[:200]}")
    return data['meta']['results']['total'], data['results']


def _device(query: str, limit: int, fetch: Fetch) -> list[Listing]:
    total, found = _openfda('device/510k', query, ('device_name', 'applicant', 'openfda.device_name'),
                            'decision_date:desc', limit, fetch)
    clearances = []
    for r in found:
        number = r.get('k_number', '')
        page = 'denovo.cfm?id=' if number.startswith('DEN') else 'pmn.cfm?ID='
        decision = r.get('decision_description') if r.get('decision_description') not in (None, 'Unknown') else ''
        clearances.append(_record(
            number, f"{r.get('device_name')} ({r.get('applicant')})", r.get('decision_date', ''),
            f"{'De Novo' if number.startswith('DEN') else '510(k)'} decision {r.get('decision_code')}"
            f"{' ' + decision if decision else ''}; product code {r.get('product_code')}",
            f'https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/{page}{number}'))
    pma_total, found = _openfda('device/pma', query, ('trade_name', 'generic_name', 'applicant'),
                                'decision_date:desc', limit, fetch)
    approvals = [_record(
        f"{r.get('pma_number')}{'/' + r['supplement_number'] if r.get('supplement_number') else ''}",
        f"{r.get('trade_name')} ({r.get('applicant')})", r.get('decision_date', ''),
        f"PMA decision {r.get('decision_code')}; {r.get('supplement_type') or 'original'}"
        f"{': ' + r['supplement_reason'] if r.get('supplement_reason') else ''}",
        f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpma/pma.cfm?id={r.get('pma_number')}"
        f"{r.get('supplement_number') or ''}") for r in found]
    return [('FDA 510(k) clearances and De Novo grants (openFDA device/510k), newest decision first', total,
             clearances, 'FDA 510(k)'),
            ('FDA premarket approvals and supplements (openFDA device/pma), newest decision first', pma_total,
             approvals, 'FDA PMA')]


def _drug(query: str, limit: int, fetch: Fetch) -> list[Listing]:
    total, found = _openfda('drug/drugsfda', query, ('openfda.brand_name', 'openfda.generic_name',
                                                     'products.brand_name', 'products.active_ingredients.name',
                                                     'sponsor_name'),
                            'submissions.submission_status_date:desc', limit, fetch)
    records = []
    for r in found:
        products = r.get('products') or []
        brands = list(dict.fromkeys(p.get('brand_name', '') for p in products if p.get('brand_name')))[:3]
        ingredients = list(dict.fromkeys(a['name'] for p in products for a in p.get('active_ingredients') or []))[:3]
        submissions = sorted(r.get('submissions') or [], key=lambda s: s.get('submission_status_date', ''))
        latest = submissions[-1] if submissions else {}
        original = next((s for s in submissions if s.get('submission_type') == 'ORIG'
                         and s.get('submission_status') == 'AP'), None)
        number = r.get('application_number', '')
        records.append(_record(
            number, f"{', '.join(brands) or 'no brand'} ({', '.join(ingredients).lower()}), {r.get('sponsor_name')}",
            _iso(latest.get('submission_status_date')),
            f"latest submission {latest.get('submission_type')} {latest.get('submission_number')} status "
            f"{latest.get('submission_status')} ({latest.get('submission_class_code_description') or 'n/a'})"
            + (f"; original approval {_iso(original['submission_status_date'])}" if original else ''),
            'https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo='
            + re.sub(r'\D', '', number)))
    return [('Drugs@FDA applications (openFDA drug/drugsfda), latest submission first', total, records,
             'FDA application')]


def _recalls(query: str, limit: int, fetch: Fetch) -> list[Listing]:
    total, found = _openfda('device/recall', query, ('product_description', 'recalling_firm', 'openfda.device_name'),
                            'event_date_initiated:desc', limit, fetch)
    devices = [_record(
        r.get('product_res_number', ''), f"{r.get('product_description')} ({r.get('recalling_firm')})",
        r.get('event_date_initiated', ''),
        f"{r.get('recall_status')}; root cause: {r.get('root_cause_description') or 'not given'}",
        f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfRES/res.cfm?id={r.get('cfres_id')}") for r in found]
    drug_total, found = _openfda('drug/enforcement', query, ('product_description', 'recalling_firm',
                                                             'openfda.brand_name', 'openfda.generic_name'),
                                 'report_date:desc', limit, fetch)
    drugs = [_record(
        r.get('recall_number', ''), f"{r.get('product_description')} ({r.get('recalling_firm')})",
        _iso(r.get('recall_initiation_date')),
        f"{r.get('classification')}, {r.get('status')}; {r.get('reason_for_recall')}",
        f"https://api.fda.gov/drug/enforcement.json?search=recall_number:%22{r.get('recall_number')}%22")
        for r in found]
    return [('FDA medical device recalls (openFDA device/recall), newest first', total, devices, 'FDA device recall'),
            ('FDA drug recall enforcement reports (openFDA drug/enforcement), newest report first', drug_total, drugs,
             'FDA drug recall')]


def _trials(query: str, limit: int, fetch: Fetch) -> list[Listing]:
    status, text = fetch(TRIALS_URL, {'query.term': query, 'pageSize': limit, 'countTotal': 'true',
                                      'sort': 'LastUpdatePostDate:desc', 'fields': TRIAL_FIELDS})
    data = _json(text)
    if status != 200 or 'studies' not in data:
        raise ValueError(f'ClinicalTrials.gov answered {status}: {text[:200]}')
    records = []
    for study in data['studies']:
        p = study.get('protocolSection', {})
        ident, state, design = p.get('identificationModule', {}), p.get('statusModule', {}), p.get('designModule', {})
        sponsor = p.get('sponsorCollaboratorsModule', {}).get('leadSponsor', {}).get('name', '')
        phases = '/'.join(re.sub(r'phase(\d)', r'phase \1', phase.lower().replace('_', ' '))  # EARLY_PHASE1
                          for phase in design.get('phases') or [] if phase != 'NA') or 'no phase'
        enrollment = (design.get('enrollmentInfo') or {}).get('count')
        records.append(_record(
            ident.get('nctId', ''), f"{ident.get('briefTitle')} ({sponsor})",
            (state.get('lastUpdatePostDateStruct') or {}).get('date', ''),
            f"{state.get('overallStatus', '').replace('_', ' ').lower()}, {phases}; started "
            f"{(state.get('startDateStruct') or {}).get('date', 'n/a')}, primary completion "
            f"{(state.get('primaryCompletionDateStruct') or {}).get('date', 'n/a')}"
            + (f'; enrollment {enrollment}' if enrollment else ''),
            f"https://clinicaltrials.gov/study/{ident.get('nctId', '')}"))
    return [('ClinicalTrials.gov studies, most recently updated first (date = last update)',
             data.get('totalCount', len(records)), records, 'ClinicalTrials.gov')]


def _nhtsa(path: str, params: dict, fetch: Fetch) -> list[dict]:
    """An NHTSA API list; it answers 400 with Count 0 when nothing matches."""
    status, text = fetch(f'{NHTSA_URL}/{path}', params)
    data = _json(text)
    results = data.get('results')
    if results is None or (status != 200 and (data.get('Count') or data.get('count'))):
        raise ValueError(f'NHTSA {path} answered {status}: {text[:200]}')
    return results


def _vehicle_recalls(query: str, limit: int, fetch: Fetch, today: date | None = None) -> list[Listing]:
    """Recalls by make, and model and model year when the query names them ("Tesla Model Y 2025"); without a year,
    the next, this and last model years."""
    year_now = (today or date.today()).year
    named_year = re.search(r'\b(19[5-9]\d|20\d\d)\b', query)
    years = [int(named_year[1])] if named_year else [year_now + 1, year_now, year_now - 1]
    rest = ' '.join(re.sub(r'\b(19[5-9]\d|20\d\d)\b', ' ', query).split()).upper()
    makes = {row['make'] for year in years for row in _nhtsa('products/vehicle/makes',
                                                             {'modelYear': year, 'issueType': 'r'}, fetch)}
    make = max((m for m in makes if rest == m or rest.startswith(m + ' ')), key=len, default=None)
    if make is None:
        raise ValueError(f"No make in NHTSA's recall data for model years {years[-1]}-{years[0]} starts the query "
                         f"{query!r}; begin with the make, as in 'Tesla Model 3 2025'.")
    wanted = rest[len(make):].strip()
    vehicles = []
    for year in years:
        models = dict.fromkeys(row['model'] for row in _nhtsa('products/vehicle/models', {
            'modelYear': year, 'make': make, 'issueType': 'r'}, fetch))
        vehicles += [(year, model) for model in models if not wanted or wanted in model]
    campaigns: dict[str, dict] = {}
    for year, model in vehicles[:MAX_VEHICLES]:
        for r in _nhtsa('recalls/recallsByVehicle', {'make': make, 'model': model, 'modelYear': year}, fetch):
            campaign = campaigns.setdefault(r['NHTSACampaignNumber'], dict(r, vehicles=[]))
            campaign['vehicles'].append(f'{year} {model}')
    ordered = sorted(campaigns.values(), key=lambda r: _iso(r.get('ReportReceivedDate')), reverse=True)
    records = []
    for r in ordered[:limit]:
        flags = [label for label, on in (('over-the-air remedy', r.get('overTheAirUpdate')),
                                         ('park outside', r.get('parkOutSide')), ('do not drive', r.get('parkIt'))) if on]
        records.append(_record(
            r['NHTSACampaignNumber'], f"{r.get('Component')}: {r.get('Summary')}", _iso(r.get('ReportReceivedDate')),
            f"affects {', '.join(r['vehicles'][:4])}{' and more' if len(r['vehicles']) > 4 else ''}"
            + (f"; {', '.join(flags)}" if flags else ''),
            f"https://www.nhtsa.gov/recalls?nhtsaId={r['NHTSACampaignNumber']}"))
    searched = f"{make}{' ' + wanted if wanted else ''}, model years {years[-1]}-{years[0]}"
    capped = f'; the first {MAX_VEHICLES} of {len(vehicles)} models' if len(vehicles) > MAX_VEHICLES else ''
    return [(f'NHTSA recall campaigns for {searched}{capped}, newest report first', len(ordered), records,
             'NHTSA recall')]


def _awards(query: str, limit: int, fetch: Fetch) -> list[Listing]:
    filters = {'recipient_search_text': [query]}
    status, text = fetch(USASPENDING_URL.format(path='spending_by_award_count'), None, {'filters': filters})
    counts = _json(text).get('results')
    if status != 200 or not isinstance(counts, dict):
        raise ValueError(f'USAspending answered {status}: {text[:200]}')
    groups = [group for group in AWARD_GROUPS if counts.get(group[0])]
    per_group = max(1, min(limit, MAX_RECORDS // max(len(groups), 1)))
    listings = []
    for name, codes, amount in groups:
        dated = 'Issued Date' if name == 'loans' else 'Start Date'
        fields = ['Award ID', 'Recipient Name', dated, 'End Date', amount, 'Awarding Agency', 'Description',
                  'generated_internal_id']
        status, text = fetch(USASPENDING_URL.format(path='spending_by_award'), None, {
            'filters': dict(filters, award_type_codes=codes), 'fields': fields, 'limit': per_group, 'page': 1,
            'sort': amount, 'order': 'desc'})
        data = _json(text)
        if status != 200 or 'results' not in data:
            raise ValueError(f"USAspending answered {status}: {data.get('detail') or text[:200]}")
        records = [_record(
            r.get('Award ID') or 'no ID', f"{r.get('Recipient Name')}: {r.get('Description') or 'no description'}",
            r.get(dated) or '', f"${r.get(amount) or 0:,.0f}, {r.get('Awarding Agency')}"
                                + (f", ends {r['End Date']}" if r.get('End Date') else ''),
            f"https://www.usaspending.gov/award/{r.get('generated_internal_id')}") for r in data['results']]
        listings.append((f'Federal {name} to recipients whose names contain {query!r} (USAspending, from fiscal '
                         '2008; check each recipient is the company), largest first', counts[name], records,
                         'USAspending award'))
    if not listings:
        listings.append((f'Federal awards to recipients whose names contain {query!r} (USAspending, from fiscal 2008)',
                         0, [], 'USAspending award'))
    return listings


def _fulltext(query: str, limit: int, fetch: Fetch, today: date | None = None) -> list[Listing]:
    end = today or date.today()
    start = _years_before(end, FULLTEXT_YEARS)
    status, text = fetch(EFTS_URL, {'q': query, 'dateRange': 'custom', 'startdt': start.isoformat(),
                                    'enddt': end.isoformat()})
    data = _json(text)
    hits = data.get('hits')
    if status != 200 or not isinstance(hits, dict):
        raise ValueError(f'SEC full-text search answered {status}: {text[:200]}')
    records = []
    for hit in hits.get('hits', [])[:limit]:
        found = hit.get('_source', {})
        accession, _, file_name = hit.get('_id', '').partition(':')
        cik = int((found.get('ciks') or ['0'])[0])
        name = ' '.join((found.get('display_names') or ['unknown filer'])[0].split())
        form, kind = found.get('form', ''), found.get('file_type', '')
        period = f", period {found['period_ending']}" if found.get('period_ending') else ''
        records.append(_record(
            accession, f"{name}, {form}{' ' + kind if kind and kind != form else ''}", found.get('file_date', ''),
            f"{found.get('file_description') or kind or form}{period}",
            f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{file_name}"))
    total = hits.get('total', {})
    return [(f'SEC EDGAR full-text search, filings from {start} to {end}, best match first'
             + (' (more than 10,000 found)' if total.get('relation') == 'gte' else ''),
             total.get('value', len(records)), records, 'SEC filing')]


def _pubmed(query: str, limit: int, fetch: Fetch) -> list[Listing]:
    status, text = fetch(EUTILS_URL.format(tool='esearch'), {'db': 'pubmed', 'term': query, 'retmax': limit,
                                                             'retmode': 'json', 'sort': 'relevance',
                                                             'tool': 'investment-research-agents'})
    found = _json(text).get('esearchresult')
    if status != 200 or not isinstance(found, dict) or 'idlist' not in found:
        raise ValueError(f'PubMed search answered {status}: {text[:200]}')
    heading = 'PubMed articles, best match first (date = publication year)'
    if not found['idlist']:
        return [(heading, int(found.get('count', 0)), [], 'PubMed')]
    status, text = fetch(EUTILS_URL.format(tool='esummary'), {'db': 'pubmed', 'id': ','.join(found['idlist']),
                                                              'retmode': 'json', 'tool': 'investment-research-agents'})
    summaries = _json(text).get('result')
    if status != 200 or not isinstance(summaries, dict):
        raise ValueError(f'PubMed summaries answered {status}: {text[:200]}')
    records = []
    for pmid in summaries.get('uids', []):
        item = summaries[pmid]
        authors = [a['name'] for a in item.get('authors') or [] if a.get('authtype') == 'Author']
        doi = next((a['value'] for a in item.get('articleids') or [] if a.get('idtype') == 'doi'), None)
        records.append(_record(
            f'PMID {pmid}', item.get('title', '').rstrip('.'), item.get('pubdate', '')[:4],
            f"{', '.join(authors[:3])}{' et al.' if len(authors) > 3 else ''}; {item.get('source')}"  # the journal
            + (f'; doi {doi}' if doi else ''), f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/'))
    return [(heading, int(found.get('count', len(records))), records, 'PubMed')]


def _arxiv(query: str, limit: int, fetch: Fetch) -> list[Listing]:
    """arXiv's API: every word of the query anywhere in a paper; a query with a field prefix (ti:, au:, abs:, cat:,
    all:) goes as written."""
    search = query if re.search(r'\b(ti|au|abs|co|jr|cat|rn|id|all):', query) else \
        ' AND '.join(f'all:{word}' for word in _words(query))
    status, text = fetch(ARXIV_URL, {'search_query': search, 'start': 0, 'max_results': limit,
                                     'sortBy': 'relevance'})
    try:
        feed = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        raise ValueError(f'arXiv answered {status}: {text[:200]}') from None
    entries = feed.findall('atom:entry', ATOM)
    if status != 200 or any('/api/errors' in (e.findtext('atom:id', '', ATOM)) for e in entries):
        message = ' '.join(e.findtext('atom:summary', '', ATOM) for e in entries) or text[:200]
        raise ValueError(f'arXiv answered {status}: {message.strip()}')
    records = []
    for entry in entries:
        link = entry.findtext('atom:id', '', ATOM).replace('http://', 'https://')
        authors = [a.findtext('atom:name', '', ATOM) for a in entry.findall('atom:author', ATOM)]
        category = entry.find('arxiv:primary_category', ATOM)
        records.append(_record(
            f"arXiv:{link.rsplit('/abs/', 1)[-1]}", entry.findtext('atom:title', '', ATOM),
            entry.findtext('atom:published', '', ATOM)[:4],
            f"{', '.join(authors[:3])}{' et al.' if len(authors) > 3 else ''}"
            + (f"; {category.get('term')}" if category is not None else ''), link))
    total = int(feed.findtext('opensearch:totalResults', str(len(records)), ATOM))
    return [('arXiv papers, best match first (date = first version year)', total, records, 'arXiv')]


SEARCHES = {'openfda_device': _device, 'openfda_drug': _drug, 'openfda_recalls': _recalls,
            'clinicaltrials': _trials, 'nhtsa_recalls': _vehicle_recalls, 'usaspending': _awards,
            'sec_fulltext': _fulltext, 'pubmed': _pubmed, 'arxiv': _arxiv}
LISTS = {'openfda_device': 2, 'openfda_recalls': 2}  # sources that give two lists share the record budget


def _result(searched: str, query: str, listings: list[Listing], source_type: str, confidence: str) -> Retrieved:
    """The lists as numbered lines (ID | title | date | status | link), each record a source."""
    retrieved = datetime.now(timezone.utc).date().isoformat()
    lines = [f'Search of {searched} for {query!r}, retrieved {retrieved}.']
    sources = []
    for heading, total, records, kind in listings:
        shown = f', showing {len(records)}' if 0 < len(records) < total else ''
        lines += ['', f'{heading}: {total:,} found{shown}.']
        if not records:
            lines.append('No records match.')
        for number, r in enumerate(records, 1):
            lines.append(f"{number}. {r['id']} | {r['title']} | {r['date'] or 'no date'} | {r['status']} | {r['link']}")
            sources.append(source(f"{kind} {r['id']}: {r['title']}", source_type, r['link'], r['date'] or retrieved,
                                  f"{kind} {r['id']} ({r['date'] or 'undated'}): {r['status']}", f"{kind} {r['id']}",
                                  confidence=confidence))
    return Retrieved('\n'.join(lines), list({s['location']: s for s in sources}.values()))


def search_public_records(source: str, query: str, limit: int = 10, fetch: Fetch = fetch_url) -> Retrieved:
    """Regulator and government records matching the query, each with ID, title, date, status and link:
    openfda_device (510(k) clearances, De Novo grants and PMA approvals), openfda_drug (Drugs@FDA applications),
    openfda_recalls (device recalls and drug recall enforcement reports), clinicaltrials (ClinicalTrials.gov),
    nhtsa_recalls (vehicle recalls; the query starts with the make, as in "Tesla Model Y 2025"), usaspending
    (federal contracts, grants and loans by recipient name) and sec_fulltext (EDGAR full-text search of the last
    five years; quote a phrase). limit: records a list, at most 20 in all. Every record is a primary source."""
    name = source.strip().lower()
    if name not in RECORD_SOURCES:
        raise ValueError(f"source must be one of {', '.join(RECORD_SOURCES)}.")
    if not query.strip():
        raise ValueError('The query is empty.')
    limit = max(1, min(limit, MAX_RECORDS // LISTS.get(name, 1)))
    return _result(name, query.strip(), SEARCHES[name](query.strip(), limit, fetch), 'primary', 'high')


def search_literature(source: str, query: str, limit: int = 10, fetch: Fetch = fetch_url) -> Retrieved:
    """Research papers matching the query, each with its ID, title, year, authors, venue and link: pubmed
    (PubMed, with the total count, journal and DOI) or arxiv (arXiv preprints, not peer reviewed, so medium
    confidence). limit: at most 20. Every paper is an independent source."""
    name = source.strip().lower()
    if name not in LITERATURE_SOURCES:
        raise ValueError(f"source must be one of {', '.join(LITERATURE_SOURCES)}.")
    if not query.strip():
        raise ValueError('The query is empty.')
    return _result(name, query.strip(), SEARCHES[name](query.strip(), max(1, min(limit, MAX_RECORDS)), fetch),
                   'independent', 'medium' if name == 'arxiv' else 'high')
