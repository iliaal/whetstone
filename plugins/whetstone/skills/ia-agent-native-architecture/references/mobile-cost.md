<overview>
Cost-aware design for mobile agents: model-tier selection, token budgets, network-aware execution, batching, caching, and surfacing costs to users.
</overview>

<cost_awareness>
## Cost-Aware Design

Mobile users may be on cellular data or concerned about API costs. Design agents to be efficient.

### Model Tier Selection

Use the cheapest model that achieves the outcome:

```typescript
type ModelTier = "fast" | "balanced" | "powerful";
type ModelChoice = {
  id: string;
  inputUSDPerMillion: number;
  outputUSDPerMillion: number;
};

function configuredModel(
  tier: ModelTier,
  settings: Record<string, string | undefined>,
): ModelChoice {
  const prefix = `AGENT_${tier.toUpperCase()}`;
  const id = settings[`${prefix}_MODEL`]?.trim();
  const input = Number(settings[`${prefix}_INPUT_USD_PER_MILLION`]);
  const output = Number(settings[`${prefix}_OUTPUT_USD_PER_MILLION`]);
  if (!id || !Number.isFinite(input) || input <= 0 ||
      !Number.isFinite(output) || output <= 0) {
    throw new Error(`Configure an active model and both token rates for ${tier}`);
  }
  return { id, inputUSDPerMillion: input, outputUSDPerMillion: output };
}

const taskTiers: Record<string, ModelTier> = {
  quickLookup: "fast",
  chatAssistant: "balanced",
  researchAgent: "balanced",
  profileGenerator: "powerful",
  introductionWriter: "balanced",
};
```

Configure provider-specific IDs and prices from the [model overview](https://platform.claude.com/docs/en/models/overview), [pricing](https://platform.claude.com/docs/en/about-claude/pricing), and [deprecation table](https://platform.claude.com/docs/en/about-claude/model-deprecations). Active direct-API examples verified on 2026-10-03 include `claude-haiku-4-5-20251001`, `claude-sonnet-5-5`, and `claude-opus-5-5`; account availability and partner IDs still require verification. Configuration has no obsolete fallback or zero-price placeholder. Track input, output, and any provider-specific caching charges separately.

### Token Budgets

Limit tokens per agent session:

```swift
struct AgentConfig {
    let modelTier: ModelTier
    let maxInputTokens: Int
    let maxOutputTokens: Int
    let maxTurns: Int

    static let research = AgentConfig(
        modelTier: .balanced,
        maxInputTokens: 50_000,
        maxOutputTokens: 4_000,
        maxTurns: 20
    )

    static let quickChat = AgentConfig(
        modelTier: .fast,
        maxInputTokens: 10_000,
        maxOutputTokens: 1_000,
        maxTurns: 5
    )
}

class AgentSession {
    var totalTokensUsed: Int = 0

    func checkBudget() -> Bool {
        if totalTokensUsed > config.maxInputTokens {
            transition(to: .failed(AgentError.budgetExceeded))
            return false
        }
        return true
    }
}
```

### Network-Aware Execution

Defer heavy operations to WiFi:

```swift
class NetworkMonitor: ObservableObject {
    @Published var isOnWiFi: Bool = false
    @Published var isExpensive: Bool = false  // Cellular or hotspot

    private let monitor = NWPathMonitor()

    func startMonitoring() {
        monitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                self?.isOnWiFi = path.usesInterfaceType(.wifi)
                self?.isExpensive = path.isExpensive
            }
        }
        monitor.start(queue: .global())
    }
}

class AgentOrchestrator {
    @ObservedObject var network = NetworkMonitor()

    func startResearchAgent(for book: Book) async {
        if network.isExpensive {
            // Warn user or defer
            let proceed = await showAlert(
                "Research uses data",
                message: "This will use approximately 1-2 MB of cellular data. Continue?"
            )
            if !proceed { return }
        }

        // Proceed with research
        await runAgent(ResearchAgent.create(book: book))
    }
}
```

### Batch API Calls

Combine multiple small requests:

```swift
// BAD: Many small API calls
for book in books {
    await agent.chat("Summarize \(book.title)")
}

// GOOD: Batch into one request
let bookList = books.map { $0.title }.joined(separator: ", ")
await agent.chat("Summarize each of these books briefly: \(bookList)")
```

### Caching

Cache expensive operations:

```typescript
type SearchRequest = {
  userId: string;
  workspaceId: string;
  bookId: string;
  query: string;
  limit: number;
  source: string;
};
type Research = { summary: string };

class ResearchCache {
  private entries = new Map<string, { research: Research; timestamp: number }>();

  private key(request: SearchRequest): string {
    return JSON.stringify([
      request.userId, request.workspaceId, request.bookId,
      request.query, request.limit, request.source,
    ]);
  }

  get(request: SearchRequest, now = Date.now()): Research | undefined {
    const key = this.key(request);
    const cached = this.entries.get(key);
    if (!cached) return undefined;
    if (now - cached.timestamp >= 86400_000) {
      this.entries.delete(key);
      return undefined;
    }
    return structuredClone(cached.research);
  }

  set(request: SearchRequest, research: Research, now = Date.now()): void {
    this.entries.set(this.key(request), {
      research: structuredClone(research), timestamp: now,
    });
  }
}

async function cachedSearch(
  request: SearchRequest,
  cache: ResearchCache,
  webSearch: (request: SearchRequest) => Promise<Research>,
): Promise<Research> {
  const cached = cache.get(request);
  if (cached !== undefined) return cached;
  const research = await webSearch(request);
  cache.set(request, research);
  return research;
}
```

Authorize the current user and workspace before looking up cached results. Include every option that changes search results in the cache key; invalidate cached content when its access grant changes.

### Cost Visibility

Show users what they're spending:

```swift
struct AgentCostView: View {
    @ObservedObject var session: AgentSession

    var body: some View {
        VStack(alignment: .leading) {
            Text("Session Stats")
                .font(.headline)

            HStack {
                Label("\(session.turnCount) turns", systemImage: "arrow.2.squarepath")
                Spacer()
                Label(formatTokens(session.totalTokensUsed), systemImage: "text.word.spacing")
            }

            if let estimatedCost = session.estimatedCost {
                Text("Est. cost: \(estimatedCost, format: .currency(code: "USD"))")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
    }
}
```
</cost_awareness>
