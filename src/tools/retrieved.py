"""What a data tool returns: its text, and the sources it retrieved, which the MCP server registers.

Registering in the tool means a filing or price the team relied on is always in the source register, with the
agent who retrieved it, and the bot gets the IDs to cite instead of a URL to register by hand.
"""
from dataclasses import dataclass, field


@dataclass
class Retrieved:
    text: str
    # Each source: title, source_type, location, date, confidence, claims, and label (how the result names it).
    sources: list[dict] = field(default_factory=list)


def source(title: str, source_type: str, location: str, date: str, claims: str, label: str,
           confidence: str = 'high') -> dict:
    return {'title': title, 'source_type': source_type, 'location': location, 'date': date,
            'confidence': confidence, 'claims': claims, 'label': label}
