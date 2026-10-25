<overview>
Testing agent-native apps requires different approaches than traditional unit testing. You're testing whether the agent achieves outcomes, not whether it calls specific functions. This guide provides concrete testing patterns for verifying your app is truly agent-native.
</overview>

<testing_philosophy>
## Testing Philosophy

### Test Outcomes, Not Procedures

**Traditional (procedure-focused):**
```typescript
// Testing that a specific function was called with specific args
expect(mockProcessFeedback).toHaveBeenCalledWith({
  message: "Great app!",
  category: "praise",
  priority: 2
});
```

**Agent-native (outcome-focused):**
```typescript
// Testing that the outcome was achieved
const result = await agent.process("Great app!");
const storedFeedback = await db.feedback.getLatest();

expect(storedFeedback.content).toContain("Great app");
expect(storedFeedback.importance).toBeGreaterThanOrEqual(1);
expect(storedFeedback.importance).toBeLessThanOrEqual(5);
// We don't care exactly how it categorized--just that it's reasonable
```

### Accept Variability

Agents may solve problems differently each time. Your tests should:
- Verify the end state, not the path
- Accept reasonable ranges, not exact values
- Check for presence of required elements, not exact format

When comparing a hook, skill, or prompt intervention, use [intervention-evaluation.md](./intervention-evaluation.md) to distinguish content effects from interruption, ceiling effects, and run-to-run noise.
</testing_philosophy>

<can_agent_do_it_test>
## The "Can Agent Do It?" Test

For each UI feature, write a test prompt and verify the agent can accomplish it.

### Template

Give each test a fresh application workspace and reset service mocks between tests. Research fixtures contain a `question`, immutable `sources` with stable citation IDs and source text, and an independently reviewed `supportedExample`. Configure search/fetch adapters to serve those sources through the agent's normal tools. Use a unique destination per invocation; `readFile` must fail when that artifact is absent.

Implement `gradeResearch({ content, question, sources })` with an independent semantic grader or human-reviewed rubric. Return `{ answersQuestion, claimsSupported }`: require a useful answer to the requested question and citations whose source text supports every material research claim. Do not grade from keywords, length, tool calls, or the agent's completion claim. Accept different wording and layouts. Validate the grader with the positive and negative controls below before relying on its verdicts. These fixture tests do not establish live-source behavior.

Use this assertion in capability, end-to-end, and recovery tests:

```typescript
type ResearchFixture = {
  question: string;
  sources: readonly { id: string; text: string }[];
  supportedExample: string;
};

async function verifyResearchArtifact(path: string, fixture: ResearchFixture): Promise<string> {
  const content = await fileService.readFile(path);
  expect(content.trim()).not.toBe('');
  expect(await gradeResearch({
    content, question: fixture.question, sources: fixture.sources,
  })).toEqual({ answersQuestion: true, claimsSupported: true });
  return content;
}
```

```typescript
describe('Agent Capability Tests', () => {
  test('Agent can add a book to library', async () => {
    const result = await agent.chat("Add 'Moby Dick' by Herman Melville to my library");

    // Verify outcome
    const library = await libraryService.getBooks();
    const mobyDick = library.find(b => b.title.includes("Moby Dick"));

    expect(mobyDick).toBeDefined();
    expect(mobyDick.author).toContain("Melville");
  });

  test('Agent can publish to feed', async () => {
    // Setup: ensure a book exists
    await libraryService.addBook({ id: "book_123", title: "1984" });

    const result = await agent.chat("Write something about surveillance themes in my feed");

    // Verify outcome
    const feed = await feedService.getItems();
    const newItem = feed.find(item => item.bookId === "book_123");

    expect(newItem).toBeDefined();
    expect(newItem.content.toLowerCase()).toMatch(/surveillance|watching|control/);
  });

  test('Agent can search and save research', async () => {
    const fixture = researchFixtures.whaleSymbolism;
    const bookId = `book-${crypto.randomUUID()}`;
    const destination = `Research/${bookId}/${crypto.randomUUID()}.md`;
    await libraryService.addBook({ id: bookId, title: "Moby Dick" });

    await agent.chat(`${fixture.question} Save sourced findings to ${destination}.`);

    await verifyResearchArtifact(destination, fixture);
  });

  test('Research grader distinguishes supported work from plausible wrong output', async () => {
    const fixture = researchFixtures.whaleSymbolism;
    const grade = (content: string) => gradeResearch({
      content, question: fixture.question, sources: fixture.sources,
    });
    expect(await grade(fixture.supportedExample)).toEqual({
      answersQuestion: true, claimsSupported: true,
    });
    for (const content of [
      'Whale symbolism Melville. Research completed.',
      'Whales are machines invented on Mars. No research was performed.',
    ]) {
      const verdict = await grade(content);
      expect(verdict.answersQuestion && verdict.claimsSupported).toBe(false);
    }
  });
});
```

### The "Write to Location" Test

Implement `locationHasNewContent` by reading the named location from the real persistence service and matching the unique marker created by this run. Tool-call assertions are routing diagnostics; they do not replace the persisted-outcome assertion. Keep explicitly authorized exclusions in a separately reviewed list rather than silently mapping missing capabilities to `N/A`.

A key litmus test: can the agent create content in specific app locations?

```typescript
describe('Location Awareness Tests', () => {
  const locations = [
    { userPhrase: "my reading feed", expectedTool: "publish_to_feed" },
    { userPhrase: "my library", expectedTool: "add_book" },
    { userPhrase: "my research folder", expectedTool: "write_file" },
    { userPhrase: "my profile", expectedTool: "write_file" },
  ];

  for (const { userPhrase, expectedTool } of locations) {
    test(`Agent knows how to write to "${userPhrase}"`, async () => {
      const marker = `location-test-${crypto.randomUUID()}`;
      const prompt = `Write a note containing "${marker}" to ${userPhrase}`;
      const result = await agent.chat(prompt);

      expect(result.toolCalls).toContainEqual(
        expect.objectContaining({ name: expectedTool })
      );
      expect(await locationHasNewContent(userPhrase, marker)).toBe(true);
    });
  }
});
```
</can_agent_do_it_test>

<surprise_test>
## The "Surprise Test"

A well-designed agent-native app lets the agent figure out creative approaches. Test this by giving open-ended requests.

### The Test

Seed a known library with *1984*, *Brave New World*, and *Fahrenheit 451*, including the metadata and excerpts needed to judge the task. Fix the clock for date-sensitive requests. Define acceptance criteria before running the agent:

| Request | Required outcome | Plausible output that must fail |
|---------|------------------|---------------------------------|
| "Help me organize my reading for next month" | A usable schedule or ordered plan for the requested month, using the seeded library, respecting any supplied availability, and explaining the ordering | A polished plan for a different month, invented books, or a generic reading essay without a plan |
| "I want to understand the dystopian themes across my sci-fi books" | A comparison across the seeded books, with supported thematic similarities and differences and correctly attributed examples | A long response that swaps the books' examples, mentions dystopia without comparing the books, or only asserts that research was completed |

1. Run the request through the agent and application services under test.
2. Inspect the returned content and read back any persisted document, mind map, or feed items from that run. Grade the delivered artifact, not an agent's description of an artifact.
3. Check library identifiers, dates, and user constraints deterministically where possible. Evaluate thematic support and usefulness against the supplied source material, using human review or an independent semantic grader with the same rubric.
4. Accept different layouts, orderings, and output locations when the request permits them. Require the same outcome criteria for each form.
5. Challenge the grader with the plausible wrong outputs above. Require rejection even when those outputs are long and contain expected keywords or valid tool calls.

Retain response length, tool counts, and library access as diagnostics for investigating a failed run. Those signals do not prove that the requested outcome exists. Label fixture-based results separately from tests using live application services.

### What Failure Looks Like

For "Help me prepare for a book club discussion", require usable discussion material grounded in the relevant books. An empty artifact, an unsupported summary, or a claim of completion without that material fails. A clarification about a genuinely missing book or discussion constraint can be appropriate; a clarification about information already available in context suggests a context or capability gap. Grade the resulting outcome rather than banning particular response phrases.
</surprise_test>

<parity_testing>
## Automated Parity Testing

Ensure every UI action has an agent equivalent.

### Capability Map Testing

Keep all UI actions in the map, including reviewed user-only exclusions. Load exclusions from a separately reviewed source with `reason` and `reviewRef` fields; do not derive them from `N/A` values. Apply the full-inventory and exclusion checks from [action-parity-discipline.md](./action-parity-discipline.md) alongside the required-capability checks below.

```typescript
// capability-map.ts
export const capabilityMap = {
  // UI Action: Agent Tool
  "View library": "read_library",
  "Add book": "add_book",
  "Delete book": "delete_book",
  "Publish insight": "publish_to_feed",
  "Start research": "start_research",
  "View highlights": "read_library",  // same tool, different query
  "Edit profile": "write_file",
  "Search web": "web_search",
  "Export data": "export_data",
};

// parity.test.ts
import { capabilityMap } from './capability-map';
import { getAgentTools } from './agent-config';
import { getSystemPrompt } from './system-prompt';

describe('Action Parity', () => {
  const agentTools = getAgentTools();
  const systemPrompt = getSystemPrompt();
  const exclusions = loadReviewedParityExclusions();

  test('map covers every UI action', () => {
    expect(Object.keys(capabilityMap).sort()).toEqual([...getUIActions()].sort());
  });

  for (const [action, exclusion] of Object.entries(exclusions)) {
    test(`${action} has a current reviewed exclusion`, () => {
      expect(capabilityMap[action]).toBe('N/A');
      expect(exclusion.reason.trim()).not.toBe('');
      expect(exclusion.reviewRef.trim()).not.toBe('');
    });
  }

  for (const [uiAction, toolName] of Object.entries(capabilityMap)) {
    test(`${uiAction} has a capability or reviewed exclusion`, () => {
      if (toolName === 'N/A') {
        expect(Object.hasOwn(exclusions, uiAction)).toBe(true);
        return;
      }
      expect(toolName.trim()).not.toBe('');
      expect(agentTools.map(t => t.name)).toContain(toolName);
      expect(systemPrompt).toContain(toolName);
    });
  }
});
```

### Context Parity Testing

Capture the serialized request at the provider transport boundary. In these examples, `captureProviderRequest` runs the supplied callback and records that outgoing request. Implement `readTrustedInstructions` and `readRuntimeDataMessages` against the provider's actual instruction and data/tool-result fields; return a string and an array of strings, respectively. Do not reconstruct those values from service state or the context builder's output. Use isolated fixtures for each test.

```typescript
describe('Context Parity', () => {
  test('Provider receives UI records only as runtime data', async () => {
    const title = `Test Book ${crypto.randomUUID()}`;
    const content = `Test insight ${crypto.randomUUID()}`;
    await libraryService.addBook({ id: "1", title });
    await feedService.addItem({ id: "f1", content });

    const request = await captureProviderRequest(() =>
      agent.chat("Summarize my library and reading feed")
    );
    const trustedPrompt = readTrustedInstructions(request);
    const runtimeData = readRuntimeDataMessages(request).join("\n");

    for (const record of [title, content]) {
      expect(runtimeData).toContain(record);
      expect(trustedPrompt).not.toContain(record);
    }
  });

  test('Recent activity is visible to agent', async () => {
    const highlightedBookId = `highlight-${crypto.randomUUID()}`;
    const researchedBookId = `research-${crypto.randomUUID()}`;
    await libraryService.addBook({ id: highlightedBookId, title: "Book to highlight" });
    await libraryService.addBook({ id: researchedBookId, title: "Book to research" });
    await activityService.log({ action: "highlighted", bookId: highlightedBookId });
    await activityService.log({ action: "researched", bookId: researchedBookId });

    const request = await captureProviderRequest(() =>
      agent.chat("Summarize my recent reading activity")
    );
    const trustedPrompt = readTrustedInstructions(request);
    const runtimeData = readRuntimeDataMessages(request).join("\n");

    expect(runtimeData).toContain("highlighted");
    expect(runtimeData).toContain("researched");
    for (const bookId of [highlightedBookId, researchedBookId]) {
      expect(runtimeData).toContain(bookId);
      expect(trustedPrompt).not.toContain(bookId);
    }
  });
});
```
</parity_testing>

<integration_testing>
## Integration Testing

Test the full flow from user request to outcome.

### End-to-End Flow Tests

```typescript
describe('End-to-End Flows', () => {
  test('Research flow persists a source-supported answer', async () => {
    const fixture = researchFixtures.whalingHistory;
    const bookId = `book-${crypto.randomUUID()}`;
    const destination = `Research/${bookId}/${crypto.randomUUID()}.md`;
    await libraryService.addBook({ id: bookId, title: "Moby Dick" });

    await agent.chat(`${fixture.question} Save sourced findings to ${destination}.`);

    await verifyResearchArtifact(destination, fixture);
  });

  test('Publish flow: request → tool call → feed update → UI reflects', async () => {
    // Setup
    await libraryService.addBook({ id: "book_1", title: "1984" });

    // Initial state
    const feedBefore = await feedService.getItems();

    // User request
    await agent.chat("Write something about Big Brother for my reading feed");

    // Verify feed updated
    const feedAfter = await feedService.getItems();
    expect(feedAfter.length).toBe(feedBefore.length + 1);

    // Verify content
    const newItem = feedAfter.find(item =>
      !feedBefore.some(old => old.id === item.id)
    );
    expect(newItem).toBeDefined();
    expect(newItem.content.toLowerCase()).toMatch(/big brother|surveillance|watching/);
  });
});
```

### Failure Recovery Tests

For the search examples, configure at most two attempts per read-only search and reset mocks and workspace state before each test. The persistent-outage case has no cached sources. Inspect the settled mock result promises to prove the injected failure was exercised and whether a later attempt succeeded. Allow additional legitimate research queries within the application's overall budget. These observations establish fault coverage; the persisted outcome and final report remain the success oracle. Expose the application's terminal `status` on the result. Implement `gradeOutcomeReport` against the final response and independently observed outcome: accept truthful paraphrases, reject claimed research success without a supported artifact, and require a clear remaining limitation for `partial` or `blocked`. Do not require a particular failure phrase. `fileService.exists` checks the real test workspace.

```typescript
describe('Failure Recovery', () => {
  test('Agent handles missing book gracefully', async () => {
    const result = await agent.chat("Tell me about 'Nonexistent Book'");

    // Agent should not crash
    expect(result.error).toBeUndefined();

    // Agent should acknowledge the issue
    expect(result.response.toLowerCase()).toMatch(
      /not found|don't see|can't find|library/
    );
  });

  test('Agent completes research after a transient search failure', async () => {
    const fixture = researchFixtures.whaleSymbolism;
    const destination = `Research/${crypto.randomUUID()}.md`;
    mockWebSearch.mockResolvedValue(fixture.sources);
    mockWebSearch.mockRejectedValueOnce(new Error('Network error'));

    const result = await agent.chat(`${fixture.question} Search for sources and save to ${destination}.`);

    expect(result.error).toBeUndefined();
    const attempts = await Promise.allSettled(mockWebSearch.mock.results.map(call => call.value));
    expect(attempts[0]?.status).toBe('rejected');
    expect(attempts.slice(1).map(attempt => attempt.status)).toContain('fulfilled');
    const content = await verifyResearchArtifact(destination, fixture);
    expect(result.status).toBe('success');
    expect(await gradeOutcomeReport({
      response: result.response, status: 'success', content,
    })).toBe(true);
  });

  test('Agent reports an unresolved search outage without invented research', async () => {
    const fixture = researchFixtures.whaleSymbolism;
    const destination = `Research/${crypto.randomUUID()}.md`;
    mockWebSearch.mockRejectedValue(new Error('Network error'));

    const result = await agent.chat(`${fixture.question} Use fresh search sources; save sourced research to ${destination} only if search succeeds.`);

    expect(result.error).toBeUndefined();
    const attempts = await Promise.allSettled(mockWebSearch.mock.results.map(call => call.value));
    expect(attempts.map(attempt => attempt.status)).toContain('rejected');
    expect(attempts.every(attempt => attempt.status === 'rejected')).toBe(true);
    expect(['partial', 'blocked']).toContain(result.status);
    expect(await fileService.exists(destination)).toBe(false);
    expect(await gradeOutcomeReport({
      response: result.response, status: result.status, content: null,
    })).toBe(true);
  });
});
```
</integration_testing>

<snapshot_testing>
## Snapshot Testing for System Prompts

Snapshot trusted instructions without app records. Verify runtime sections separately in the captured provider request, using the helpers from Context Parity Testing.

```typescript
describe('System Prompt Stability', () => {
  test('Trusted system prompt matches snapshot', async () => {
    const systemPrompt = await buildSystemPrompt();
    expect(systemPrompt).toMatchSnapshot();
  });

  test('Capabilities and runtime sections use their intended channels', async () => {
    const request = await captureProviderRequest(() =>
      agent.chat("Summarize my available books and recent activity")
    );
    const trustedPrompt = readTrustedInstructions(request);
    const runtimeData = readRuntimeDataMessages(request).join("\n");

    expect(trustedPrompt).toBe(await buildSystemPrompt());
    expect(trustedPrompt).toContain("Your Capabilities");
    for (const section of ["Available Books", "Recent Activity"]) {
      expect(runtimeData).toContain(section);
    }
  });
});
```
</snapshot_testing>

<manual_testing>
## Manual Testing Checklist

Some things are best tested manually during development:

### Natural Language Variation Test

Try multiple phrasings for the same request:

```
"Add this to my feed"
"Write something in my reading feed"
"Publish an insight about this"
"Put this in the feed"
"I want this in my feed"
```

All should work if context injection is correct.

### Edge Case Prompts

```
"What can you do?"
→ Agent should describe capabilities

"Help me with my books"
→ Agent should engage with library, not ask what "books" means

"Write something"
→ Agent should ask WHERE (feed, file, etc.) if not clear

"Delete everything"
→ Agent should confirm before destructive actions
```

### Confusion Test

Ask about things that should exist but might not be properly connected:

```
"What's in my research folder?"
→ Should list files, not ask "what research folder?"

"Show me my recent reading"
→ Should show activity, not ask "what do you mean?"

"Continue where I left off"
→ Should reference recent activity if available
```
</manual_testing>

<ci_integration>
## CI/CD Integration

Add agent-native tests to your CI pipeline:

```yaml
# .github/workflows/test.yml
name: Agent-Native Tests

on: [push, pull_request]

jobs:
  agent-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup
        run: npm install

      - name: Run Parity Tests
        run: npm run test:parity

      - name: Run Capability Tests
        run: npm run test:capabilities
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

      - name: Check System Prompt Completeness
        run: npm run test:system-prompt

      - name: Verify Capability Map
        run: |
          # Ensure capability map is up to date
          npm run generate:capability-map
          git diff --exit-code capability-map.ts
```

### Cost-Aware Testing

Agent tests cost API tokens. Strategies to manage:

```typescript
// Use smaller models for basic tests
const configuredModel = process.env.CI
  ? process.env.AGENT_TEST_MODEL : process.env.AGENT_DEV_MODEL;
if (!configuredModel) throw new Error("Configure an active provider-specific test model");
const testConfig = {
  model: configuredModel,
  maxTokens: 500,  // Limit output length
};

// Cache responses for deterministic tests
const cachedAgent = new CachedAgent({
  cacheDir: ".test-cache",
  ttl: 24 * 60 * 60 * 1000,  // 24 hours
});

// Run expensive tests only on main branch
if (process.env.GITHUB_REF === 'refs/heads/main') {
  describe('Full Integration Tests', () => { ... });
}
```
</ci_integration>

<test_utilities>
## Test Utilities

### Agent Test Harness

```typescript
class AgentTestHarness {
  private agent: Agent;
  private mockServices: MockServices;

  async setup() {
    const model = process.env.AGENT_TEST_MODEL;
    if (!model) throw new Error("AGENT_TEST_MODEL must identify an active model");
    this.mockServices = createMockServices();
    this.agent = await createAgent({
      services: this.mockServices,
      model,
    });
  }

  async chat(message: string): Promise<AgentResponse> {
    return this.agent.chat(message);
  }

  async expectToolCall(toolName: string) {
    const lastResponse = this.agent.getLastResponse();
    expect(lastResponse.toolCalls.map(t => t.name)).toContain(toolName);
  }

  async expectOutcome(check: () => Promise<boolean>) {
    const result = await check();
    expect(result).toBe(true);
  }

  getState() {
    return {
      library: this.mockServices.library.getBooks(),
      feed: this.mockServices.feed.getItems(),
      files: this.mockServices.files.listAll(),
    };
  }
}

// Usage
test('full flow', async () => {
  const harness = new AgentTestHarness();
  await harness.setup();

  await harness.chat("Add 'Moby Dick' to my library");
  await harness.expectToolCall("add_book");
  await harness.expectOutcome(async () => {
    const state = harness.getState();
    return state.library.some(b => b.title.includes("Moby"));
  });
});
```
</test_utilities>

<checklist>
## Testing Checklist

Automated Tests:
- [ ] "Can Agent Do It?" tests for each UI action
- [ ] Location awareness tests ("write to my feed")
- [ ] Parity tests (tool exists, documented in prompt)
- [ ] Context parity tests inspect provider-bound runtime data and exclude app records from trusted instructions
- [ ] End-to-end flow tests
- [ ] Failure recovery tests

Manual Tests:
- [ ] Natural language variation (multiple phrasings work)
- [ ] Edge case prompts (open-ended requests)
- [ ] Confusion test (agent knows app vocabulary)
- [ ] Surprise test (agent can be creative)

CI Integration:
- [ ] Parity tests run on every PR
- [ ] Capability tests run with API key
- [ ] System prompt completeness check
- [ ] Capability map drift detection
</checklist>
