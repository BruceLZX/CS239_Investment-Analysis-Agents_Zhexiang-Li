"""Web search and fetch: DuckDuckGo's result page as recorded, and a fetch that stays on public addresses."""
from pathlib import Path
import socket

import httpx
import pytest

from tools import web

FIXTURES = Path(__file__).parent / 'fixtures'


def response(status=200, text='', content_type='text/html', url='https://example.com/', content=None) -> httpx.Response:
    return httpx.Response(status, headers={'content-type': content_type}, content=content if content is not None else text.encode(),
                          request=httpx.Request('GET', url))


def test_results_come_from_a_recorded_page_with_links_unwrapped():
    html = (FIXTURES / 'ddg_results.html').read_text()
    hits = web.search('apple services', get=lambda url, params: response(text=html))
    assert 1 <= len(hits) <= 3
    for hit in hits:
        assert hit['title'] and hit['url'].startswith('http') and 'duckduckgo.com' not in hit['url']
    assert web.parse_results(html, 1) == hits[:1]


def test_a_redirect_link_is_unwrapped_and_html_in_results_is_flattened():
    html = ('<div class="result"><a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fnews.example%2Fa&rut=x">'
            'A <b>big</b>  story</a><a class="result__snippet" href="x">Some <b>bold</b> text</a></div>'
            '<div class="result"><a class="result__a" href="javascript:void(0)">Not a page</a></div>')
    assert web.parse_results(html) == [{'title': 'A big story', 'url': 'https://news.example/a', 'snippet': 'Some bold text'}]


def test_a_page_with_no_results_is_an_empty_list():
    assert web.search('nothing at all', get=lambda url, params: response(text='<html><body>No results.</body></html>')) == []


@pytest.mark.parametrize('answer', [response(status=403), response(text='<div class="anomaly-modal">Check</div>')])
def test_a_refusal_from_the_provider_is_said_plainly_and_not_mistaken_for_no_results(answer):
    with pytest.raises(ValueError, match='refusing requests'):
        web.search('a query', get=lambda url, params: answer)


def test_an_empty_query_is_refused():
    with pytest.raises(ValueError, match='query is required'):
        web.search('  ')


def test_a_page_comes_back_with_its_title_and_text_cut_to_length():
    html = '<html><head><title> The  page </title></head><body><p>' + 'word ' * 400 + '</p></body></html>'
    page = web.fetch('https://example.com/', 500, get=lambda url: response(text=html))
    assert page['title'] == 'The page' and page['truncated'] and page['text'].endswith('[Content truncated]')
    assert len(page['text']) < 550


def test_a_page_loses_its_navigation_and_keeps_its_article():
    html = ('<html><head><title>Q &amp; A</title></head><body><nav>Home Products</nav><header>Menu</header>'
            f"<article><p>{'The real text. ' * 50}</p></article><footer>Contact us</footer></body></html>")
    page = web.fetch('https://example.com/', 2000, get=lambda url: response(text=html))
    assert page['title'] == 'Q & A' and page['text'].startswith('The real text.')
    assert 'Home Products' not in page['text'] and 'Contact us' not in page['text']


def test_a_failed_or_empty_page_is_explained():
    with pytest.raises(ValueError, match='HTTP 404'):
        web.fetch('https://example.com/', get=lambda url: response(status=404))
    with pytest.raises(ValueError, match='no readable text'):
        web.fetch('https://example.com/', get=lambda url: response(text='<html><body></body></html>'))


@pytest.mark.parametrize('url', ['file:///etc/passwd', 'ftp://example.com/x', 'http://'])
def test_only_http_urls_are_fetched(url):
    with pytest.raises(ValueError, match='Only public http'):
        web._public(url)


@pytest.mark.parametrize('address', ['127.0.0.1', '10.0.0.5', '169.254.169.254', '192.168.1.1', '::1'])
def test_a_private_address_is_refused(monkeypatch, address):
    monkeypatch.setattr(socket, 'getaddrinfo', lambda host, port: [(None, None, None, None, (address, 0))])
    with pytest.raises(ValueError, match='not a public address'):
        web._public('https://looks-public.example/')


def test_a_redirect_is_checked_at_every_hop(monkeypatch):
    checked = []
    monkeypatch.setattr(web, '_public', lambda url: checked.append(url))

    def answer(request):
        if request.url.host == 'first.example':
            return httpx.Response(302, headers={'location': 'https://second.example/page'})
        return httpx.Response(200, text='<p>Arrived</p>', headers={'content-type': 'text/html'})
    real_client = httpx.Client
    monkeypatch.setattr(web.httpx, 'Client', lambda **kwargs: real_client(transport=httpx.MockTransport(answer), **kwargs))
    assert web._get('https://first.example/').text == '<p>Arrived</p>'
    assert checked == ['https://first.example/', 'https://second.example/page']
