# Threat Modeling Mode

Load this reference when the user asks for a threat model rather than a code scan. Produces an architectural security analysis document instead of a code-level vulnerability report.

## Process

1. **System model**: identify components, entry points, data flows, trust boundaries, and external dependencies from the codebase. Every claim must reference a repo path. Record trusted inputs and deprioritized or out-of-scope surfaces with a reason for each decision.
2. **Asset inventory**: what data and capabilities are worth protecting? Rate each asset's sensitivity (public, internal, confidential, restricted) based on impact of unauthorized disclosure.
3. **STRIDE analysis per component**: for each component, evaluate Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, and Elevation of Privilege. Use element-type mapping:
   - External entities → Spoofing, Repudiation
   - Processes → all six categories
   - Data stores → Tampering, Repudiation, Information Disclosure, DoS
   - Data flows → Tampering, Information Disclosure, DoS

   For infrastructure/IAM surfaces, supplement STRIDE with checks for excessive grants, lateral identity use, changes outside IaC, access left after migrations, and scope enforcement on automated approval, merge, and write paths. Record overlapping threats once in the same analysis.

   Describe threats that remain relevant after known bugs are fixed. Use past CVEs and security fixes as likelihood evidence, not as the threat itself.
4. **Risk matrix**: plot each threat by Impact (1-5) x Likelihood (1-5). Score residual likelihood after verified controls. Record owner assertions that would change a score but lack code evidence as unverified open questions. Prioritize by composite score.
5. **Focus paths**: 5-15 repo-relative file paths that merit deeper review, each with a one-sentence reason tied to the threat model.
6. **Coverage check**: account for every entry point in at least one threat's attack surface or in a reasoned deprioritization row.

## Output format

```markdown
# Threat Model: [System Name]

## System Overview
[Components, entry points, trust boundaries, data flows -- with repo path evidence]

## Trusted Inputs and Deprioritized Surfaces

| Input or Surface | Trust or Scope Decision | Reason and Repo Evidence |
|------------------|-------------------------|--------------------------|
| ... | ... | ... |

## Threat Analysis

| ID | STRIDE Category or Infrastructure Abuse Path | Threat | Component and Entry Points | Verified Controls | Impact | Residual Likelihood | Risk |
|----|---------------------------------------------|--------|----------------------------|-------------------|--------|---------------------|------|
| TM-001 | Spoofing | ... | ... | ... | 4 | 3 | 12 |

## Open Questions

[Unverified owner assertions, affected threat IDs/scores, and the evidence needed]

## Risk Matrix
[Impact x Likelihood grid with threat IDs plotted]

## Focus Paths
| Path | Reason |
|------|--------|
| src/auth/session.ts | Verify token generation against the session-impersonation threat |

## Recommendations
### Immediate (before next deploy)
### 30-day
### 90-day
```

Explicitly note non-capabilities to avoid inflated severity. Pause and validate assumptions with the user before producing the final report.
