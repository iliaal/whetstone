# Core Principles

### 1. Parity

**Whatever the user can do through the UI, the agent should be able to achieve through tools.**

This is the foundational principle. Without it, nothing else matters. Ensure the agent has tools (or combinations of tools) that can accomplish anything the UI can do. This isn't about 1:1 mapping of UI buttons to tools -- it's about ensuring the agent can **achieve the same outcomes**.

| User Action | How Agent Achieves It |
|-------------|----------------------|
| Create a note | `write_file` to notes directory, or `create_note` tool |
| Tag a note as urgent | `update_file` metadata, or `tag_note` tool |
| Search notes | `search_files` or `search_notes` tool |
| Delete a note | `delete_file` or `delete_note` tool |

**The test:** Pick any action a user can take in your UI. Describe it to the agent. Can it accomplish the outcome?

---

### 2. Granularity

**Prefer atomic primitives. Features are outcomes achieved by an agent operating in a loop.**

A tool is a primitive capability: read a file, write a file, run a bash command, store a record, send a notification. A **feature** is not a function you write. It's an outcome you describe in a prompt, achieved by an agent that has tools and operates in a loop until the outcome is reached.

**Less granular (limits the agent):**
```
Tool: classify_and_organize_files(files)
-> You wrote the decision logic
-> To change behavior, you refactor
```

**More granular (empowers the agent):**
```
Tools: read_file, write_file, move_file, list_directory, bash
Prompt: "Organize the user's downloads folder by content and recency."
-> Agent makes the decisions
-> To change behavior, you edit the prompt
```

**The test:** To change how a feature behaves, do you edit prose or refactor code?

---

### 3. Composability

**With atomic tools and parity, you can create new features just by writing new prompts.**

This is the payoff of the first two principles. When your tools are atomic and the agent can do anything users can do, new features are just new prompts:

```
"Review files modified this week. Summarize key changes. Based on
incomplete items and approaching deadlines, suggest three priorities
for next week."
```

**The test:** Can you add a new feature by writing a new prompt section, without adding new code?

---

### 4. Emergent Capability

**The agent can accomplish things you didn't explicitly design for.**

When tools are atomic, parity is maintained, and prompts are composable, users will ask the agent for things you never anticipated. And often, the agent can figure it out.

*"Cross-reference my meeting notes with my task list and tell me what I've committed to but haven't scheduled."*

You didn't build a "commitment tracker" feature. But if the agent can read notes, read tasks, and reason about them -- operating in a loop until it has an answer -- it can accomplish this.

**The flywheel:**
1. Build with atomic tools and parity
2. Users ask for things you didn't anticipate
3. Agent composes tools to accomplish them (or fails, revealing a gap)
4. You observe patterns in what's being requested
5. Add domain tools or prompts to make common patterns efficient
6. Repeat

**The test:** Give the agent an open-ended request relevant to your domain. Can it figure out a reasonable approach? If it just says "I don't have a feature for that," your architecture is too constrained.

---

### 5. Improvement Over Time

**Agent-native applications get better through accumulated context and prompt refinement.**

**Accumulated context:** The agent can maintain state across sessions. A `context.md` file the agent reads and updates is layer one. More sophisticated approaches involve structured memory and learned preferences.

**Prompt refinement at multiple levels:**
- **Developer level:** You ship updated prompts that change agent behavior for all users
- **User level:** Users customize prompts for their workflow
- **Agent level:** The agent modifies its own prompts based on feedback (advanced)

**The test:** Does the application work better after a month of use than on day one, even without code changes?
