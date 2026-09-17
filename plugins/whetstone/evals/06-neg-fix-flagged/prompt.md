---
max_turns: 20
timeout_seconds: 420
allowed_tools: [Skill, Read, Glob, Grep]
runs: 3
---
A code review flagged that `parse_env()` mishandles inline comments in values: `TOKEN=abc123 # prod` yields the value `abc123 # prod`, while `MSG="a # b"` must keep its `#`. Fix it. No repository is available; return the corrected function.

```python
def parse_env(text: str) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env
```
