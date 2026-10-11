<overview>
Architectural patterns for building agent-native systems. These patterns emerge from the five core principles: Parity, Granularity, Composability, Emergent Capability, and Improvement Over Time.

Features are outcomes achieved by agents operating in a loop, not functions you write. Tools are atomic primitives. The agent applies judgment; the prompt defines the outcome.

See also:
- [files-universal-interface.md](./files-universal-interface.md) for file organization and context.md patterns
- [agent-execution-patterns.md](./agent-execution-patterns.md) for completion signals and partial completion
- [product-implications.md](./product-implications.md) for progressive disclosure and approval patterns
</overview>

<pattern name="event-driven-agent">
## Event-Driven Agent Architecture

The agent runs as a long-lived process that responds to events. Events become prompts.

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Loop                                │
├─────────────────────────────────────────────────────────────┤
│  Event Source → Agent (Claude) → Tool Calls → Response      │
└─────────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌─────────┐    ┌──────────┐    ┌───────────┐
    │ Content │    │   Self   │    │   Data    │
    │  Tools  │    │  Tools   │    │   Tools   │
    └─────────┘    └──────────┘    └───────────┘
    (write_file)   (read_source)   (store_item)
                   (restart)       (list_items)
```

**Key characteristics:**
- Events (messages, webhooks, timers) trigger agent turns
- Agent decides how to respond based on system prompt
- Tools are primitives for IO, not business logic
- State persists between events via data tools

**Example: Discord feedback bot**
```typescript
// Event source
client.on("messageCreate", (message) => {
  if (!message.author.bot) {
    runAgent({
      userMessage: `New message from ${message.author}: "${message.content}"`,
      channelId: message.channelId,
    });
  }
});

// System prompt defines behavior
const systemPrompt = `
When someone shares feedback:
1. Acknowledge their feedback warmly
2. Ask clarifying questions if needed
3. Store it using the feedback tools
4. Update the feedback site

Use your judgment about importance and categorization.
`;
```
</pattern>

<pattern name="two-layer-git">
## Two-Layer Git Architecture

For self-modifying agents, separate code (shared) from data (instance-specific).

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub (shared repo)                     │
│  - src/           (agent code)                              │
│  - site/          (web interface)                           │
│  - package.json   (dependencies)                            │
│  - .gitignore     (excludes data/, logs/)                   │
└─────────────────────────────────────────────────────────────┘
                          │
                     git clone
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Instance (Server)                           │
│                                                              │
│  FROM GITHUB (tracked):                                      │
│  - src/           → pushed back on code changes             │
│  - site/          → pushed, triggers deployment             │
│                                                              │
│  LOCAL ONLY (untracked):                                     │
│  - data/          → instance-specific storage               │
│  - logs/          → runtime logs                            │
│  - .env           → secrets                                 │
└─────────────────────────────────────────────────────────────┘
```

**Why this works:**
- Code and site are version controlled (GitHub)
- Raw data stays local (instance-specific)
- Site is generated from data, so reproducible
- Automatic rollback via git history
</pattern>

<pattern name="multi-instance">
## Multi-Instance Branching

Each agent instance gets its own branch while sharing core code.

```
main                        # Shared features, bug fixes
├── instance/feedback-bot   # Every Reader feedback bot
├── instance/support-bot    # Customer support bot
└── instance/research-bot   # Research assistant
```

**Change flow:**
| Change Type | Work On | Then |
|-------------|---------|------|
| Core features | main | Merge to instance branches |
| Bug fixes | main | Merge to instance branches |
| Instance config | instance branch | Done |
| Instance data | instance branch | Done |

**Sync tools:**
```typescript
tool("self_deploy", "Pull latest from main, rebuild, restart", ...)
tool("sync_from_instance", "Merge from another instance", ...)
tool("propose_to_main", "Create PR to share improvements", ...)
```
</pattern>

<pattern name="site-as-output">
## Site as Agent Output

The agent generates and maintains a website as a natural output, not through specialized site tools.

```
Discord Message
      ↓
Agent processes it, extracts insights
      ↓
Agent decides what site updates are needed
      ↓
Agent writes files using write_file primitive
      ↓
Git commit + push triggers deployment
      ↓
Site updates automatically
```

**Key insight:** Don't build site generation tools. Give the agent file tools and teach it in the prompt how to create good sites.

```markdown
## Site Management

You maintain a public feedback site. When feedback comes in:
1. Use write_file to update site/public/content/feedback.json
2. If the site's React components need improvement, modify them
3. Commit changes and push to trigger Vercel deploy

The site should be:
- Clean, modern dashboard aesthetic
- Clear visual hierarchy
- Status organization (Inbox, Active, Done)

You decide the structure. Make it good.
```
</pattern>

<pattern name="approval-gates">
## Approval Gates Pattern

Separate "propose" from "apply" for dangerous operations.

Use this transaction contract in the trusted application service. Agent tools may propose or inspect drafts; the authenticated approval UI supplies approval records. An agent argument such as `approved: true` grants no authority.

1. Resolve the proposed destination through the workspace service, check the caller's write grant, and read its current revision.
2. Persist one draft with an ID, canonical destination, baseline revision, content bytes, content hash, and monotonically increasing draft revision. Any edit invalidates existing approval.
3. Show the exact destination and diff to the approving user. Store authenticated approval referencing that draft ID, revision, content hash, and destination.
4. For an apply request, acquire the destination's write lock and load the current draft and approval from trusted storage. Reject missing, stale, or differently scoped approval before writing.
5. Recompute the content hash and validate the exact destination and baseline revision. If the target changed, keep the draft pending and return a conflict for rereading and review.
6. Atomically claim that draft revision so only one worker can apply it. Write those approved bytes through the workspace's revision-conditional replacement while retaining the lock.
7. Persist the resulting revision and receipt before reporting applied. A crash after the write but before the receipt requires reconciliation against the recorded claim and artifact; do not blindly retry.
8. Clear only the applied draft. Other pending drafts retain their individual approval state.

Expose `apply_pending({ draftId, revision })` as a request to this service, never as a loop over all pending changes. The same destination lock or database transaction must cover approval validation, the claim, baseline comparison, and replacement. Verify the positive approved path, missing approval, changed content, stale baseline, unrelated pending drafts, concurrent claims, and interruption after replacement.

**What requires approval:**
- src/*.ts (agent code)
- package.json (dependencies)
- system prompt changes

**What doesn't:**
- data/* (instance data)
- site/* (generated content)
- docs/* (documentation)
</pattern>

<pattern name="unified-agent-architecture">
## Unified Agent Architecture

One execution engine, many agent types. All agents use the same orchestrator but with different configurations.

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentOrchestrator                         │
├─────────────────────────────────────────────────────────────┤
│  - Lifecycle management (start, pause, resume, stop)        │
│  - Checkpoint/restore (for background execution)            │
│  - Tool execution                                            │
│  - Chat integration                                          │
└─────────────────────────────────────────────────────────────┘
          │                    │                    │
    ┌─────┴─────┐        ┌─────┴─────┐        ┌─────┴─────┐
    │ Research  │        │   Chat    │        │  Profile  │
    │   Agent   │        │   Agent   │        │   Agent   │
    └───────────┘        └───────────┘        └───────────┘
    - web_search         - read_library       - read_photos
    - write_file         - publish_to_feed    - write_file
    - read_file          - web_search         - analyze_image
```

**Implementation:**

`AgentOrchestrator` and the tool registry below are application contracts. Implement lifecycle, checkpointing, authorization, and tool execution in the shared orchestrator; inject each agent's configuration.

```typescript
type Book = { id: string; title: string; author: string };
type AgentTool = {
  name: string;
  execute(input: unknown): Promise<unknown>;
};
type AgentSetup = {
  config: { name: string };
  tools: AgentTool[];
  context: string;
};

interface AgentOrchestrator {
  startAgent(setup: AgentSetup): Promise<{ sessionId: string }>;
}

declare const orchestrator: AgentOrchestrator;
declare const tools: Record<
  "readFile" | "writeFile" | "webSearch" | "webFetch" |
  "readLibrary" | "publishToFeed", AgentTool
>;

function researchAgent(book: Book): AgentSetup {
  return {
    config: { name: "research" },
    tools: [tools.readFile, tools.writeFile, tools.webSearch, tools.webFetch],
    context: `Research "${book.title}" by ${book.author}.
Save findings to Documents/Research/${book.id}/`,
  };
}

function chatAgent(library: Book[]): AgentSetup {
  return {
    config: { name: "chat" },
    tools: [tools.readFile, tools.writeFile, tools.readLibrary,
      tools.publishToFeed, tools.webSearch],
    context: `Help the user with their reading.
Available books: ${library.map(book => book.title).join(", ")}`,
  };
}

declare const book: Book;
const session = await orchestrator.startAgent(researchAgent(book));
```

**Benefits:**
- Consistent lifecycle management across all agent types
- Automatic checkpoint/resume (critical for mobile)
- Shared tool protocol
- Easy to add new agent types
- Centralized error handling and logging
</pattern>

<pattern name="agent-to-ui-communication">
## Agent-to-UI Communication

When agents take actions, the UI should reflect them immediately. The user should see what the agent did.

**Pattern 1: Shared Data Store (Recommended)**

Agent writes through the same service the UI observes:

Use an application-owned store whose `addFeedItem` persists the item, updates its snapshot, and notifies subscribers before resolving. The renderer and tool registration are application adapters; both use the same store instance.

```typescript
type FeedItem = { bookId: string; content: string; headline: string };
interface BookLibraryService {
  getFeedItems(): readonly FeedItem[];
  subscribe(listener: () => void): () => void;
  addFeedItem(item: FeedItem): Promise<void>;
}

declare const library: BookLibraryService;
declare function renderFeed(items: readonly FeedItem[]): void;

async function publishToFeed(item: FeedItem) {
  await library.addFeedItem(item);
  return { text: "Published to feed" };
}

function mountFeed(): () => void {
  const render = () => renderFeed(library.getFeedItems());
  const unsubscribe = library.subscribe(render);
  render();
  return unsubscribe;
}
```

**Pattern 2: File System Observation**

For file-based data, watch the file system:

`ResearchFiles` is an app-defined adapter over the scoped workspace service. Implement provider or filesystem observation behind `subscribe`; return a cleanup function and report observation errors. Register `writeResearchFile` as the tool handler after validating its arguments and caller grants.

```typescript
interface ResearchFiles {
  list(bookId: string): Promise<string[]>;
  subscribe(bookId: string, changed: () => void, failed: (error: unknown) => void): () => void;
  replace(path: string, content: string, expectedRevision: string | null): Promise<string>;
}

declare const files: ResearchFiles;
declare function renderFiles(paths: string[]): void;
declare function reportError(error: unknown): void;

function watchResearch(bookId: string): () => void {
  let active = true;
  let generation = 0;
  const reload = async () => {
    const request = ++generation;
    try {
      const paths = await files.list(bookId);
      if (active && request === generation) renderFiles(paths);
    } catch (error) {
      if (active && request === generation) reportError(error);
    }
  };
  const stop = files.subscribe(bookId, () => { void reload(); }, reportError);
  void reload();
  return () => { active = false; stop(); };
}

async function writeResearchFile(path: string, content: string, expectedRevision: string | null) {
  const revision = await files.replace(path, content, expectedRevision);
  return { text: "File saved", revision };
}
```

**Pattern 3: Event Bus (Cross-Component)**

For complex apps with multiple independent components:

```tsx
type FeedItem = { bookId: string; content: string; headline: string };

// Shared event bus
const agentEvents = new EventEmitter();

// Agent tool emits events
tool("publish_to_feed", async ({ content }: { content: string }) => {
    const item: FeedItem = await feedService.add(content);
    agentEvents.emit('feed:new-item', item);
    return { text: "Published" };
});

// UI components subscribe
function FeedView() {
    const [items, setItems] = useState<FeedItem[]>([]);

    useEffect(() => {
        const handler = (item: FeedItem) => setItems(prev => [...prev, item]);
        agentEvents.on('feed:new-item', handler);
        return () => {
            agentEvents.off('feed:new-item', handler);
        };
    }, []);

    return <FeedList items={items} />;
}
```

**What to avoid:**

```typescript
declare const database: {
  insert(table: "feed", content: string): Promise<void>;
  query(table: "feed"): Promise<string[]>;
};
declare function renderFeed(items: string[]): void;

async function publishToFeed(content: string) {
  await database.insert("feed", content);
}

async function mountFeed() {
  const items = await database.query("feed");
  renderFeed(items);
}
```

This counterexample loads the feed once and never subscribes to changes. Later tool writes leave the UI stale.
</pattern>

<pattern name="model-tier-selection">
## Model Tier Selection

Different agents need different intelligence levels. Use the cheapest model that achieves the outcome.

| Agent Type | Recommended Tier | Reasoning |
|------------|-----------------|-----------|
| Chat/Conversation | Balanced | Fast responses, good reasoning |
| Research | Balanced | Tool loops, not ultra-complex synthesis |
| Content Generation | Balanced | Creative but not synthesis-heavy |
| Complex Analysis | Powerful | Multi-document synthesis, nuanced judgment |
| Profile/Onboarding | Powerful | Photo analysis, complex pattern recognition |
| Simple Queries | Fast/Haiku | Quick lookups, simple transformations |

**Implementation:**

```typescript
type ModelTier = "fast" | "balanced" | "powerful";
type AgentTool = { name: string; execute(input: unknown): Promise<unknown> };
type AgentConfig = {
  modelTier: ModelTier;
  tools: AgentTool[];
  systemPrompt: string;
};

declare const researchTools: AgentTool[], profileTools: AgentTool[];
declare const researchPrompt: string, profilePrompt: string;
declare const readLibrary: AgentTool;

const researchConfig: AgentConfig = {
  modelTier: "balanced",
  tools: researchTools,
  systemPrompt: researchPrompt,
};

const profileConfig: AgentConfig = {
  modelTier: "powerful",
  tools: profileTools,
  systemPrompt: profilePrompt,
};

const lookupConfig: AgentConfig = {
  modelTier: "fast",
  tools: [readLibrary],
  systemPrompt: "Answer quick questions about the user's library.",
};
```

Resolve tiers through the active provider configuration in [mobile-cost.md](./mobile-cost.md); a tier is not a fixed model ID.

**Cost optimization strategies:**
- Start with balanced tier, only upgrade if quality insufficient
- Use fast tier for tool-heavy loops where each turn is simple
- Reserve powerful tier for synthesis tasks (comparing multiple sources)
- Consider token limits per turn to control costs
</pattern>

<design_questions>
## Questions to Ask When Designing

1. **What events trigger agent turns?** (messages, webhooks, timers, user requests)
2. **What primitives does the agent need?** (read, write, call API, restart)
3. **What decisions should the agent make?** (format, structure, priority, action)
4. **What decisions should be hardcoded?** (security boundaries, approval requirements)
5. **How does the agent verify its work?** (health checks, build verification)
6. **How does the agent recover from mistakes?** (git rollback, approval gates)
7. **How does the UI know when agent changes state?** (shared store, file watching, events)
8. **What model tier does each agent type need?** (fast, balanced, powerful)
9. **How do agents share infrastructure?** (unified orchestrator, shared tools)
</design_questions>
