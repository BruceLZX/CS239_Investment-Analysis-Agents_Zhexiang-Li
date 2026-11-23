"""The team's policies as rules the app enforces, for Phase 2's safe port.

rules.py is the rule table: each rule names the policies it enforces, the tools it guards and what it does.
engine.py applies it at the one place every tool call passes through, the MCP server's dispatch, and logs every
decision to the run's policy_log.jsonl. A run is in one of two modes: enforce refuses, observe only logs what it would
have refused. A case file with no mode (Phase 1 and the baseline traces) has no enforcement at all.

The course's policy-assurance framework has not been released, so this is the app's own layer. The rule table does not
depend on how it is called: engine.before and engine.after are the only entry points, for a framework to take over.
"""
