# Documentation Capture Process (Detailed)

<critical_sequence name="documentation-capture" enforce_order="strict">

## 7-Step Process

<step number="1" required="true">
### Step 1: Detect Confirmation

**Auto-invoke after phrases:**

- "that worked"
- "it's fixed"
- "working now"
- "problem solved"
- "that did it"

**OR manual:** `/ia-compound` command

**Non-trivial problems only:**

- Multiple investigation attempts needed
- Tricky debugging that took time
- Non-obvious solution
- Future sessions would benefit

**Skip documentation for:**

- Simple typos
- Obvious syntax errors
- Trivial fixes immediately corrected
</step>

<step number="2" required="true" depends_on="1">
### Step 2: Gather Context

Extract from conversation history:

**Required information:**

- **Module name**: Which module or component had the problem
- **Symptom**: Observable error/behavior (exact error messages)
- **Investigation attempts**: What didn't work and why
- **Root cause**: Technical explanation of actual problem
- **Solution**: What fixed it (code/config changes)
- **Prevention**: How to avoid in future

**Environment details:**

- Framework/language version
- Stage (0-6 or post-implementation)
- OS version
- File/line references

**BLOCKING REQUIREMENT:** If critical context is missing (module name, exact error, stage, or resolution steps), ask user and WAIT for response before proceeding to Step 3:

```
I need a few details to document this properly:

1. Which module had this issue? [ModuleName]
2. What was the exact error message or symptom?
3. What stage were you in? (0-6 or post-implementation)

[Continue after user provides details]
```
</step>

<step number="3" required="false" depends_on="2">
### Step 3: Check Existing Docs

Search docs/solutions/ for similar issues:

```bash
# Search by error message keywords
grep -r "exact error phrase" docs/solutions/

# Search by symptom category
ls docs/solutions/[category]/
```

**IF similar issue found:**

THEN present decision options:

```
Found similar issue: docs/solutions/[path]

What's next?
1. Create new doc with cross-reference (recommended)
2. Update existing doc (only if same root cause)
3. Other

Choose (1-3): _
```

WAIT for user response, then execute chosen action.

**ELSE** (no similar issue found):

Proceed directly to Step 4 (no user interaction needed).
</step>

<step number="4" required="true" depends_on="2">
### Step 4: Generate Filename

Format: `[sanitized-symptom]-[module]-[YYYYMMDD].md`

**Sanitization rules:**

- Lowercase
- Replace spaces with hyphens
- Remove special characters except hyphens
- Truncate to reasonable length (< 80 chars)

**Examples:**

- `missing-include-BriefSystem-20251110.md`
- `parameter-not-saving-state-EmailProcessing-20251110.md`
- `webview-crash-on-resize-Assistant-20251110.md`
</step>

<step number="5" required="true" depends_on="4" blocking="true">
### Step 5: Validate YAML Schema

**CRITICAL:** All docs require validated YAML frontmatter with enum validation.

<validation_gate name="yaml-schema" blocking="true">

**Validate against schema:**
Load `schema.yaml` and classify the problem against the enum values defined in [yaml-schema.md](../references/yaml-schema.md). Ensure all required fields are present and match allowed values exactly.

**BLOCK if validation fails:**

```
YAML validation failed

Errors:
- problem_type: must be one of schema enums, got "compilation_error"
- severity: must be one of [critical, high, medium, low], got "invalid"
- symptoms: must be array with 1-5 items, got string

Please provide corrected values.
```

**GATE ENFORCEMENT:** Do NOT proceed to Step 6 (Create Documentation) until YAML frontmatter passes all validation rules defined in `schema.yaml`.

</validation_gate>
</step>

<step number="6" required="true" depends_on="5">
### Step 6: Create Documentation

**Determine category from problem_type:** Use the category mapping defined in [yaml-schema.md](../references/yaml-schema.md).

**Create documentation file:**

```bash
PROBLEM_TYPE="[from validated YAML]"
CATEGORY="[mapped from problem_type]"
FILENAME="[generated-filename].md"
DOC_PATH="docs/solutions/${CATEGORY}/${FILENAME}"

# Create directory if needed
mkdir -p "docs/solutions/${CATEGORY}"

# Write documentation using template from assets/resolution-template.md
# (Content populated with Step 2 context and validated YAML frontmatter)
```

**Result:**
- Single file in category directory
- Enum validation ensures consistent categorization

**Create documentation:** Populate the structure from [resolution-template.md](../assets/resolution-template.md) with context gathered in Step 2 and validated YAML frontmatter from Step 5.
</step>

<step number="7" required="false" depends_on="6">
### Step 7: Cross-Reference & Critical Pattern Detection

If similar issues found in Step 3:

**Update existing doc:**

```bash
# Add Related Issues link to similar doc
echo "- See also: [$FILENAME]($REAL_FILE)" >> [similar-doc.md]
```

**Update patterns if applicable:**

If this represents a common pattern (3+ similar issues):

```bash
# Add to docs/solutions/patterns/common-solutions.md
cat >> docs/solutions/patterns/common-solutions.md << 'EOF'

## [Pattern Name]

**Common symptom:** [Description]
**Root cause:** [Technical explanation]
**Solution pattern:** [General approach]

**Examples:**
- [Link to doc 1]
- [Link to doc 2]
- [Link to doc 3]
EOF
```

**Critical Pattern Detection (Optional Proactive Suggestion):**

If this issue has automatic indicators suggesting it might be critical:
- Severity: `critical` in YAML
- Affects multiple modules OR foundational stage (Stage 2 or 3)
- Non-obvious solution

Then in the decision menu, add a note suggesting it might be worth adding to Required Reading. But **NEVER auto-promote**. User decides via decision menu.

**Template for critical pattern addition:**

When user selects "Add to Required Reading", use the template from [critical-pattern-template.md](../assets/critical-pattern-template.md) to structure the pattern entry. Number it sequentially based on existing patterns in `docs/solutions/patterns/critical-patterns.md`.
</step>

</critical_sequence>

---

## Decision Menu Response Handling

After successful documentation, present the decision menu and handle responses:

**Option 1: Continue workflow** - Return to calling skill/workflow. Documentation is complete.

**Option 2: Add to Required Reading** - Extract pattern, format as WRONG vs CORRECT with code examples, add to `docs/solutions/patterns/critical-patterns.md`, add cross-reference back to this doc.

**Option 3: Link related issues** - Prompt for doc to link, search docs/solutions/, add cross-reference to both docs.

**Option 4: Add to existing skill** - Prompt for skill name, determine which reference file to update, add link and brief description.

**Option 5: Create new skill** - Extract into new learning skill.

**Option 6: View documentation** - Display the created doc, then present decision menu again.

**Option 7: Other** - Ask what they'd like to do.
