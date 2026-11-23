"""Render each fixture deck (*_deck.md) to a PDF beside it: one slide a page, with visible slide numbers.

Each "## N. Title" heading starts slide N, numbered from 1; the deck's title and the lines above slide 1 go on
slide 1. An HTML comment in a deck stands for text hidden from a human reader, like white text on a slide: the PDF
draws it in white at 2pt, so it is in the text layer that text extractors and AI tools read, but not visible on the
page. A slide too long for its page is set in smaller type until it fits. From src/:

    .venv/bin/python fixtures/build_decks.py                            # every deck
    .venv/bin/python fixtures/build_decks.py fixtures/vantelle_deck.md  # one deck
"""
import html
import os
from pathlib import Path
import re
import sys

from markdown_it import MarkdownIt

FIXTURES = Path(__file__).resolve().parent
SLIDE_RE = re.compile(r'^## (\d+)\. ', re.M)
COMMENT_RE = re.compile(r'<!--(.*?)-->', re.S)
# Type sizes in points, largest first: each slide gets the largest one that fits its page.
SIZES = (13, 12, 11, 10.5, 10, 9.5, 9, 8.5, 8)
MARKDOWN = MarkdownIt('commonmark', {'html': True}).enable('table')
STYLE = """
* { font-variant-ligatures: none; }
body { margin: 0; font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; color: #111827; }
section.slide + section.slide { break-before: page; }
h1 { margin: 0 0 0.4em; font-size: 2em; color: #0f172a; }
h2 { margin: 0 0 0.6em; padding-bottom: 0.25em; border-bottom: 3px solid #0f766e; font-size: 1.55em;
     color: #0f172a; }
p, li { margin: 0 0 0.35em; line-height: 1.35; }
ul { margin: 0 0 0.5em; padding-left: 0; list-style: none; }
li { padding-left: 1.1em; text-indent: -1.1em; }
li::before { content: "-\\00a0\\00a0"; }
table { width: 100%; margin: 0.3em 0 0.6em; border-collapse: collapse; font-size: 0.92em; }
th, td { padding: 0.22em 0.45em; border: 1px solid #cbd5e1; text-align: left; vertical-align: top; }
th { background: #f1f5f9; }
.hidden-text { margin: 0; color: #ffffff; font-size: 2pt; line-height: 1; }
"""


def slides(markdown: str) -> tuple[str, list[str]]:
    """The deck's title and each slide's markdown, checked to be numbered 1, 2, 3 ... in order."""
    title = re.search(r'^# (.+)$', markdown, re.M).group(1).strip()
    headings = list(SLIDE_RE.finditer(markdown))
    numbers = [int(heading.group(1)) for heading in headings]
    if not numbers or numbers != list(range(1, len(numbers) + 1)):
        raise ValueError(f'slides must be numbered 1 to N in order; found {numbers}')
    starts = [heading.start() for heading in headings] + [len(markdown)]
    parts = [markdown[start:end] for start, end in zip(starts, starts[1:])]
    parts[0] = markdown[:starts[0]] + parts[0]
    return title, parts


def slide_html(markdown: str, size: float) -> str:
    hidden = COMMENT_RE.sub(lambda m: f'\n\n<div class="hidden-text">{html.escape(" ".join(m.group(1).split()))}'
                                      '</div>\n\n', markdown)
    return f'<section class="slide" style="font-size: {size}pt">\n{MARKDOWN.render(hidden)}</section>'


def page_html(title: str, label: str, sections: list[str]) -> str:
    def quoted(text: str) -> str:
        return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'
    margins = (f'@page {{ size: 13.333in 7.5in; margin: 0.5in 0.6in 0.6in;\n'
               f'  @bottom-left {{ content: {quoted(title)}; font: 8pt Helvetica, Arial, sans-serif; color: #6b7280; }}\n'
               f'  @bottom-center {{ content: {quoted(label)}; font: bold 8pt Helvetica, Arial, sans-serif; '
               f'color: #b91c1c; }}\n'
               f'  @bottom-right {{ content: "Slide " counter(page) " of " counter(pages); '
               f'font: 9pt Helvetica, Arial, sans-serif; }} }}')
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title>'
            f'<style>{margins}{STYLE}</style></head><body>\n' + '\n'.join(sections) + '\n</body></html>')


def build(deck: Path) -> tuple[Path, list[float]]:
    """Write the deck's PDF beside it; returns the PDF and each slide's type size."""
    from weasyprint import HTML  # Loads Pango, so only once the library path is set.

    markdown = deck.read_text()
    title, parts = slides(markdown)
    label = 'CONFIDENTIAL' if 'confidential' in markdown.lower() else ''
    sizes = []
    for number, part in enumerate(parts, 1):
        size = next((size for size in SIZES
                     if len(HTML(string=page_html(title, label, [slide_html(part, size)])).render().pages) == 1), None)
        if size is None:
            raise SystemExit(f'{deck.name}: slide {number} does not fit one page even at {SIZES[-1]}pt; shorten it.')
        sizes.append(size)
    document = HTML(string=page_html(title, label, [slide_html(part, size) for part, size in zip(parts, sizes)])).render()
    if len(document.pages) != len(parts):
        raise SystemExit(f'{deck.name}: {len(parts)} slides came out as {len(document.pages)} pages.')
    pdf = deck.with_suffix('.pdf')
    document.write_pdf(pdf)
    return pdf, sizes


def _with_library_path() -> None:
    """On macOS, restart with Homebrew's library folder on the library path, where WeasyPrint finds Pango: the path
    has to be set before the process starts."""
    if sys.platform != 'darwin' or os.environ.get('BUILD_DECKS_RESTARTED'):
        return
    folders = [folder for folder in ('/opt/homebrew/lib', '/usr/local/lib')
               if Path(folder, 'libpango-1.0.0.dylib').exists()]
    current = [folder for folder in os.environ.get('DYLD_FALLBACK_LIBRARY_PATH', '').split(':') if folder]
    missing = [folder for folder in folders if folder not in current]
    if missing:
        env = dict(os.environ, DYLD_FALLBACK_LIBRARY_PATH=':'.join(current + missing), BUILD_DECKS_RESTARTED='1')
        os.execve(sys.executable, [sys.executable, *sys.argv], env)


def main(argv: list[str]) -> None:
    _with_library_path()
    for deck in [Path(arg) for arg in argv[1:]] or sorted(FIXTURES.glob('*_deck.md')):
        pdf, sizes = build(deck)
        print(f'{pdf}: {len(sizes)} slides, type {min(sizes):g}-{max(sizes):g}pt')


if __name__ == '__main__':
    main(sys.argv)
