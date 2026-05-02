# Issue Formatting & Creation

## Content Formatting

- [ ] Use clear, descriptive headings with proper hierarchy (##, ###)
- [ ] Include code examples in triple backticks with language syntax highlighting
- [ ] Add screenshots/mockups if UI-related (drag & drop or use image hosting)
- [ ] Use task lists (- [ ]) for trackable items that can be checked off
- [ ] Add collapsible sections for lengthy logs or optional details using `<details>` tags

## Cross-Referencing

- [ ] Link to related issues/PRs using #number format
- [ ] Reference specific commits with SHA hashes when relevant
- [ ] Link to code using GitHub's permalink feature (press 'y' for permanent link)
- [ ] Mention relevant team members with @username if needed
- [ ] Add links to external resources with descriptive text

## Code & Examples

````markdown
# Good example with syntax highlighting and line references


```typescript
// src/services/UserService.ts:42
function processUser(user: User): void {

  // Implementation here

}
```

# Collapsible error logs

<details>
<summary>Full error stacktrace</summary>

`Error details here...`

</details>
````

## AI-Era Considerations

- [ ] Account for accelerated development with AI pair programming
- [ ] Include prompts or instructions that worked well during research
- [ ] Note which AI tools were used for initial exploration (Claude, Copilot, etc.)
- [ ] Emphasize comprehensive testing given rapid implementation
- [ ] Document any AI-generated code that needs human review

## Issue Creation

When user selects "Create Issue", detect their project tracker from CLAUDE.md:

1. **Check for tracker preference** in user's CLAUDE.md (global or project):
   - Look for `project_tracker: github` or `project_tracker: linear`
   - Or look for mentions of "GitHub Issues" or "Linear" in their workflow section

2. **If GitHub:**

   Use the title and type from Step 2 (already in context - no need to re-read the file):

   ```bash
   gh issue create --title "<type>: <title>" --body-file <plan_path>
   ```

3. **If Linear:**

   ```bash
   linear issue create --title "<title>" --description "$(cat <plan_path>)"
   ```

4. **If no tracker configured:**
   Ask user: "Which project tracker do you use? (GitHub/Linear/Other)"
   - Suggest adding `project_tracker: github` or `project_tracker: linear` to their CLAUDE.md

5. **After creation:**
   - Display the issue URL
   - Ask if they want to proceed to `/ia-work` or `/ia-review`
