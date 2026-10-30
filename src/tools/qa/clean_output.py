"""The delivery folder's contract, ported from scripts/clean_output.py: sources/ with the client's
original documents, exactly one HTML report and one PDF, and nothing else. The server writes the folder itself, so
this checks it rather than deleting anything.
"""
from pathlib import Path


def check_output(folder: str | Path) -> dict:
    folder = Path(folder)
    if not folder.is_dir():
        return {'failures': [f'no delivery folder at {folder}'], 'passed': False}
    failures = []
    if not (folder / 'sources').is_dir():
        failures.append('no sources/ folder')
    htmls = [p.name for p in folder.iterdir() if p.is_file() and p.suffix == '.html']
    pdfs = [p.name for p in folder.iterdir() if p.is_file() and p.suffix == '.pdf']
    if len(htmls) != 1:
        failures.append(f'{len(htmls)} HTML reports; needs exactly 1')
    if len(pdfs) != 1:
        failures.append(f'{len(pdfs)} PDF reports; needs exactly 1')
    extra = sorted(p.name for p in folder.iterdir() if p.name != 'sources' and p.suffix not in ('.html', '.pdf'))
    if extra:
        failures.append('working files left in the delivery folder: ' + ', '.join(extra))
    return {'failures': failures, 'passed': not failures, 'html': htmls, 'pdf': pdfs}
