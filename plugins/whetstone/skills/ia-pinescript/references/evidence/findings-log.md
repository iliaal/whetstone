# ia-pinescript findings log

Persistent iteration evidence for ia-pinescript. See [`/diagnose-negatives`](../../../../../.claude/commands/diagnose-negatives.md) Step 3 for the schema.

## EX-001: Misfire on TradingView MCP server (JS) audit

- Label: negative
- Kind: wrong_trigger
- Origin: human-verified (diagnose-negatives reviewer accepted)
- Source: 2 of 2 negative sessions in distillery/.eval-data/ia-pinescript/sessions.jsonl (2026-04-27 harvest)
- Status: resolved
- Expected behavior: skill should not inject when the user is auditing a JavaScript MCP server that connects to the TradingView API but contains zero `.pine` files
- Observed behavior: skill injected because regex `tradingview|...` matched bare "tradingview" in the prompt; agent then loaded ia-simplifying-code and ia-code-review (correct skills), wasting the injection
- Skill delta:
  - `plugins/whetstone/hooks/skill-patterns.sh:65`: tightened regex so bare `tradingview` no longer matches; required Pine-context qualifier within 30 chars (`tradingview.{0,30}(pine|indicator|strategy|chart|script)`); added symmetric `\bstrategy\b.{0,20}(pine|trading.?view)` clause
  - `plugins/whetstone/skills/ia-pinescript/SKILL.md:4-7`: rewrote description to scope triggers to `.pine` files or TradingView Pine indicators/strategies (drops standalone "TradingView", "indicators", "strategies", "backtesting" as triggers)
  - `distillery/tests/fixtures/triggers/ia-pinescript.jsonl`: added two negative-case fixtures from the actual misfire prompts
- Anonymization: redacted nothing; both prompts were generic infrastructure audits with no sensitive content
