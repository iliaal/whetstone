# Reader test

## Step 7: Reader Test (Optional)

For standalone documents that must be self-contained (onboarding guides, ADRs, external-facing docs), dispatch a zero-context sub-agent to simulate a first-time reader. The sub-agent has no conversation history — it sees only what a future reader would see.

**How to run the test:**

1. **Predict 5-10 reader questions** from the document's stated goals — one per major section or decision. Mix three kinds:
   - Concrete retrieval: "What command sets up the dev environment?"
   - Decision rationale: "Why did we pick X over Y?"
   - Ambiguity probe: "Could a reader interpret <specific phrase> in more than one way?"
2. **Dispatch a fresh sub-agent** with the document attached and the questions. No prior context, no session history.
3. **Compare the sub-agent's answers** against author intent. Also ask the sub-agent directly: "What feels ambiguous? What prior knowledge does this assume? Are there internal contradictions?"

**Interpret results:**

- Correct, confident answers → document is self-contained for that question.
- Wrong answer with high confidence → document actively misleads. Highest-priority fix.
- Hedged or "insufficient information" → the document has a gap the author didn't notice. Fill it.
- Sub-agent flags ambiguity the author didn't intend → reword for precision.

Skip for context-dependent docs (brainstorm notes, plan files, internal working docs) where the reader will always have prior context. The sub-agent test only adds value when the real reader has no other channel.
