# Quick Reference Commands

## Finding Work

```bash
# List highest priority unblocked work
grep -l 'dependencies: \[\]' todos/*-ready-p1-*.md

# List all pending items needing triage
ls todos/*-pending-*.md

# Find next issue ID
ls todos/ | grep -o '^[0-9]\+' | sort -n | tail -1 | awk '{printf "%03d", $1+1}'

# Count by status
for status in pending ready complete; do
  echo "$status: $(ls -1 todos/*-$status-*.md 2>/dev/null | wc -l)"
done
```

## Dependency Management

```bash
# What blocks this todo?
grep "^dependencies:" todos/003-*.md

# What does this todo block?
grep -l 'dependencies:.*"002"' todos/*.md
```

## Searching

```bash
# Search by tag
grep -l "tags:.*typescript" todos/*.md

# Search by priority
ls todos/*-p1-*.md

# Full-text search
grep -r "payment" todos/
```
