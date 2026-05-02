# Quality Guidelines & Error Handling

## Quality Guidelines

**Good documentation has:**

- Exact error messages (copy-paste from output)
- Specific file:line references
- Observable symptoms (what you saw, not interpretations)
- Failed attempts documented (helps avoid wrong paths)
- Technical explanation (not just "what" but "why")
- Code examples (before/after if applicable)
- Prevention guidance (how to catch early)
- Cross-references (related issues)

**Avoid:**

- Vague descriptions ("something was wrong")
- Missing technical details ("fixed the code")
- No context (which version? which file?)
- Just code dumps (explain why it works)
- No prevention guidance
- No cross-references

---

## Execution Guidelines

**MUST do:**
- Validate YAML frontmatter (BLOCK if invalid per Step 5 validation gate)
- Extract exact error messages from conversation
- Include code examples in solution section
- Create directories before writing files (`mkdir -p`)
- Ask user and WAIT if critical context missing

**MUST NOT do:**
- Skip YAML validation (validation gate is blocking)
- Use vague descriptions (not searchable)
- Omit code examples or cross-references

---

## Error Handling

**Missing context:**
- Ask user for missing details
- Don't proceed until critical info provided

**YAML validation failure:**
- Show specific errors
- Present retry with corrected values
- BLOCK until valid

**Similar issue ambiguity:**
- Present multiple matches
- Let user choose: new doc, update existing, or link as duplicate

**Module not in modules documentation:**
- Warn but don't block
- Proceed with documentation
- Suggest: "Add [Module] to modules documentation if not there"
