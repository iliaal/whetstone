# Example Scenario

**User:** "That worked! The N+1 query is fixed."

**Skill activates:**

1. **Detect confirmation:** "That worked!" triggers auto-invoke
2. **Gather context:**
   - Module: Brief System
   - Symptom: Brief generation taking >5 seconds, N+1 query when loading email threads
   - Failed attempts: Added pagination (didn't help), checked background job performance
   - Solution: Added eager loading with `includes(:emails)` on Brief model
   - Root cause: Missing eager loading causing separate database query per email thread
3. **Check existing:** No similar issue found
4. **Generate filename:** `n-plus-one-brief-generation-BriefSystem-20251110.md`
5. **Validate YAML:**
   ```yaml
   module: Brief System
   date: 2025-11-10
   problem_type: performance_issue
   component: database_model
   symptoms:
     - "N+1 query when loading email threads"
     - "Brief generation taking >5 seconds"
   root_cause: missing_include
   severity: high
   tags: [n-plus-one, eager-loading, performance]
   ```
   Valid
6. **Create documentation:**
   - `docs/solutions/performance-issues/n-plus-one-brief-generation-BriefSystem-20251110.md`
7. **Cross-reference:** None needed (no similar issues)

**Output:**

```
Solution documented

File created:
- docs/solutions/performance-issues/n-plus-one-brief-generation-BriefSystem-20251110.md

What's next?
1. Continue workflow (recommended)
2. Add to Required Reading - Promote to critical patterns (critical-patterns.md)
3. Link related issues - Connect to similar problems
4. Add to existing skill - Add to a learning skill (e.g., hotwire-native)
5. Create new skill - Extract into new learning skill
6. View documentation - See what was captured
7. Other
```
