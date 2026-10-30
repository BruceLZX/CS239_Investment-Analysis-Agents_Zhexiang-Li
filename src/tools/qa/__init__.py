"""The QA checks, ported from the scripts in BruceLZX/investment-analysis-skill (MIT).

Each module carries the name of the script it ports (scripts/check_depth.py and so on) and keeps that
script's thresholds. They read the case file's records and the rendered report instead of the original's _work/
Markdown files, and they fix the scripts' bugs (each fix is noted where it is made). Like every check in this app,
they report and never block: the Phase 2 framework decides what to enforce.
"""
