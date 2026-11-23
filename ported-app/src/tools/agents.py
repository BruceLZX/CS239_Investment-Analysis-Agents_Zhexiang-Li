"""The team's agents as the MCP server knows them.

Each bot reaches the server at its own endpoint, /mcp?agent=<key> (see team/profiles.py), so the
server can tell which agent made each call without asking the model.
"""
AGENTS = {'lead': 'Lead Analyst', 'company': 'Company Analyst', 'product': 'Product Analyst',
          'market': 'Market Analyst', 'fundamentals': 'Fundamentals Analyst', 'valuation': 'Valuation Analyst',
          'regulatory': 'Regulatory Analyst', 'red_team': 'Red Team Analyst', 'reviewer': 'IC Reviewer'}
# The six analysts the Lead briefs at the start of a case, each owning report sections.
ANALYSTS = tuple(AGENTS[key] for key in ('company', 'product', 'market', 'fundamentals', 'valuation', 'regulatory'))
# Every bot that researches: the analysts and the Red Team, which researches counter-evidence.
RESEARCHERS = ANALYSTS + (AGENTS['red_team'],)
