"""The team's agents as the MCP server knows them.

Each bot reaches the server at its own endpoint, /mcp?agent=<key> (see team/profiles.py), so the
server can tell which agent made each call without asking the model.
"""
AGENTS = {'lead': 'Lead Analyst', 'fundamentals': 'Fundamentals Analyst', 'market': 'Market Analyst',
          'reviewer': 'IC Reviewer'}
ANALYSTS = (AGENTS['fundamentals'], AGENTS['market'])
