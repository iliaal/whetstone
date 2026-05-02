# Threat Modeling Mode

Load this reference when the user asks for a threat model rather than a code scan. Produces an architectural security analysis document instead of a code-level vulnerability report.

## Process

1. **System model**: identify components, data flows, trust boundaries, and external dependencies from the codebase. Every claim must reference a repo path.
2. **Asset inventory**: what data and capabilities are worth protecting? Rate each asset's sensitivity (public, internal, confidential, restricted) based on impact of unauthorized disclosure.
3. **STRIDE analysis per component**: for each component, evaluate Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, and Elevation of Privilege. Use element-type mapping:
   - External entities → Spoofing, Repudiation
   - Processes → all six categories
   - Data stores → Tampering, Repudiation, Information Disclosure, DoS
   - Data flows → Tampering, Information Disclosure, DoS
4. **Risk matrix**: plot each threat by Impact (1-5) x Likelihood (1-5). Prioritize by composite score.
5. **Focus paths**: 5-15 repo-relative file paths that merit deeper review, each with a one-sentence reason tied to the threat model.

## Output format

```markdown
# Threat Model: [System Name]

## System Overview
[Components, trust boundaries, data flows -- with repo path evidence]

## STRIDE Analysis
| ID | Category | Threat | Target Component | Impact | Likelihood | Risk |
|----|----------|--------|-----------------|--------|------------|------|
| TM-001 | Spoofing | ... | ... | 4 | 3 | 12 |

## Risk Matrix
[Impact x Likelihood grid with threat IDs plotted]

## Focus Paths
| Path | Reason |
|------|--------|
| src/auth/session.ts | Session token generation lacks entropy check |

## Recommendations
### Immediate (before next deploy)
### 30-day
### 90-day
```

Explicitly note non-capabilities to avoid inflated severity. Pause and validate assumptions with the user before producing the final report.
