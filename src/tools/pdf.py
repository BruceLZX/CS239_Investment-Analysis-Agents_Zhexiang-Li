"""Print an HTML report to PDF with WeasyPrint, as the skill's scripts/generate_pdf.py does.

report.write_pdf runs this in a child process with the library path WeasyPrint needs:

    python -m tools.pdf report.html report.pdf

WeasyPrint lays out some of the template differently from a browser: it draws the section headings, which are
<button> elements, as form controls on top of the text, its inline-flex source tags break lines, and its card grids
use auto-fit columns. The printed copy turns the buttons into plain blocks and adds PRINT_FIXES; the HTML report
itself keeps the template unchanged.
"""
from pathlib import Path
import re
import sys

from weasyprint import CSS, HTML

PRINT_FIXES = """
@page { size: A4; margin: 14mm 12mm 16mm; }
p { text-align: left !important; }
.section-heading { display: block !important; width: 100%; padding: 12px 14px !important; }
.section-index { display: inline-block !important; width: 30px; height: 30px; line-height: 30px; text-align: center;
                 vertical-align: middle; margin-right: 10px; }
.section-title { display: inline-block !important; vertical-align: middle; }
.section-title strong, .section-title span { display: block; }
.source-tag, .source-confidence { display: inline !important; min-height: 0 !important; padding: 0 4px !important;
                                  line-height: 1.4; margin-left: 2px !important; }
.kpi-dashboard, .efficiency-strip, .briefing-grid, .quad-grid, .analog-grid { display: flex !important;
                                                                              flex-wrap: wrap; }
.kpi-card { flex: 1 1 21%; margin: 0 8px 8px 0; }
.eff-card { flex: 1 1 17%; margin: 0 8px 8px 0; }
.brief-card { flex: 1 1 29%; margin: 0 8px 8px 0; }
.quad-item, .analog-card { flex: 1 1 44%; margin: 0 8px 8px 0; }
.verdict-strip { display: block !important; }
.verdict-strip strong, .verdict-strip span { display: block; }
"""


def printable(markup: str) -> str:
    """The report with its buttons as plain blocks (the toolbar's are hidden in print anyway)."""
    return re.sub(r'</button>', '</div>', re.sub(r'<button\b', '<div', markup))


def main(argv: list[str]) -> None:
    source = Path(argv[1])
    HTML(string=printable(source.read_text()), base_url=str(source.parent)).write_pdf(
        argv[2], stylesheets=[CSS(string=PRINT_FIXES)])


if __name__ == '__main__':
    main(sys.argv)
