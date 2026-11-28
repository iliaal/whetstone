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

Separate the per-request output cap from the session budget. Use the prompt to request concise answers. Leave enough output capacity for a complete attempt; for providers that count reasoning toward the output limit, include reasoning headroom. Treat a `max_tokens` stop as an incomplete attempt, never a successful answer or a reason to retry at the same cap.

Reserve a conservative input, output, and currency bound before every paid attempt. The following TypeScript uses app-defined provider adapters; `bound` must cover the exact request and configured output cap, including applicable caching and other charges.

```typescript
type Usage = { inputTokens: number; outputTokens: number; usd: number };
type Limits = {
  outputTokenCap: number;
  maxSessionTokens: number;
  maxSessionUSD: number;
  maxAttempts: number;
  maxRetries: number;
};
type BudgetSession = { charged: Usage; attempts: number; stopped: boolean };
type AttemptResult = {
  status: "complete" | "retryable-failure" | "failed" | "truncated";
  text: string;
  usage?: Usage;
};
type PaidAttempt = {
  bound: Usage;
  call(outputTokenCap: number): Promise<AttemptResult>;
};

function validUsage(usage: Usage): boolean {
  return [usage.inputTokens, usage.outputTokens].every(
    value => Number.isSafeInteger(value) && value >= 0,
  ) && Number.isFinite(usage.usd) && usage.usd >= 0;
}

async function runWithFallback(
  limits: Limits,
  session: BudgetSession,
  candidates: PaidAttempt[],
): Promise<string> {
  if (![limits.outputTokenCap, limits.maxSessionTokens, limits.maxAttempts]
      .every(value => Number.isSafeInteger(value) && value > 0) ||
      !Number.isSafeInteger(limits.maxRetries) || limits.maxRetries < 0 ||
      !Number.isFinite(limits.maxSessionUSD) || limits.maxSessionUSD <= 0 ||
      !validUsage(session.charged) ||
      !Number.isSafeInteger(session.attempts) || session.attempts < 0) {
    throw new Error("Invalid budget configuration or session ledger");
  }

  for (const attempt of candidates.slice(0, limits.maxRetries + 1)) {
    const bound = attempt.bound;
    const charged = session.charged;
    if (session.stopped || !validUsage(bound) ||
        bound.outputTokens < limits.outputTokenCap ||
        session.attempts >= limits.maxAttempts ||
        charged.inputTokens + charged.outputTokens +
          bound.inputTokens + bound.outputTokens > limits.maxSessionTokens ||
        charged.usd + bound.usd > limits.maxSessionUSD) {
      session.stopped = true;
      throw new Error("No budget for another paid attempt");
    }

    session.charged = {
      inputTokens: charged.inputTokens + bound.inputTokens,
      outputTokens: charged.outputTokens + bound.outputTokens,
      usd: charged.usd + bound.usd,
    };
    session.attempts += 1;
    let result: AttemptResult;
    try {
      result = await attempt.call(limits.outputTokenCap);
    } catch (error) {
      session.stopped = true;
      throw error;
    }
    const actual = result.usage;
    if (!actual || !validUsage(actual)) {
      session.stopped = true;
      throw new Error("Unknown billing; retain the reservation and reconcile");
    }
    session.charged = {
      inputTokens: charged.inputTokens + actual.inputTokens,
      outputTokens: charged.outputTokens + actual.outputTokens,
      usd: charged.usd + actual.usd,
    };
    if (actual.inputTokens > bound.inputTokens ||
        actual.outputTokens > bound.outputTokens || actual.usd > bound.usd) {
      session.stopped = true;
      throw new Error("Attempt exceeded its reserved bound");
    }
    if (result.status === "complete") return result.text;
    if (result.status !== "retryable-failure") {
      throw new Error(`Attempt ${result.status}; revise the request before retrying`);
    }
  }
  throw new Error("No successful attempt within the retry limit");
}
```

Keep the same session ledger across turns and provider fallbacks. Count actual input and output tokens and charges for failed attempts too. Serialize access to the ledger; persist reservations before dispatch and settlements before another attempt. A client timeout leaves remote billing unresolved, so retain the reservation and stop until reconciliation. Unknown or non-finite charges must never trigger provider fallback. A truncated attempt needs a revised plan or larger cap and a fresh budget check before retrying. Give optional shadow evaluations a separate budget and await or cancel them before returning the production result.

### Network-Aware Execution

Defer heavy operations to WiFi:

Use an app-defined adapter for native connectivity state; TypeScript has no portable API for determining whether a mobile connection is metered.

```typescript
type NetworkState = { connected: boolean; metered: boolean | null };
type NetworkMonitor = { current(): NetworkState };

async function startResearch(
  network: NetworkMonitor,
  confirmDataUse: () => Promise<boolean>,
  runResearch: () => Promise<void>,
): Promise<"completed" | "deferred"> {
  const state = network.current();
  if (!state.connected) return "deferred";
  if (state.metered !== false && !await confirmDataUse()) return "deferred";
  await runResearch();
  return "completed";
}
```

### Batch API Calls

Combine multiple small requests:

```typescript
// BAD: Many small API calls
for (const book of books) {
  await agent.chat(`Summarize ${book.title}`);
}

// GOOD: Batch into one request
const bookList = books.map(book => book.title).join(", ");
await agent.chat(`Summarize each of these books briefly: ${bookList}`);
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

Build a framework-independent view model, then render it with the app's UI components. Keep unresolved reservations distinct from confirmed usage.

```typescript
type SessionStats = {
  turns: number;
  inputTokens: number;
  outputTokens: number;
  estimatedUSD: number | null;
  billingPending: boolean;
};

function costLabels(stats: SessionStats, locale: string): string[] {
  const count = new Intl.NumberFormat(locale);
  const currency = new Intl.NumberFormat(locale, {
    style: "currency", currency: "USD",
  });
  const labels = [
    `${count.format(stats.turns)} turns`,
    `${count.format(stats.inputTokens)} input tokens`,
    `${count.format(stats.outputTokens)} output tokens`,
  ];
  if (stats.estimatedUSD !== null) {
    labels.push(`Est. cost: ${currency.format(stats.estimatedUSD)}`);
  }
  if (stats.billingPending) labels.push("Billing reconciliation pending");
  return labels;
}
```
</cost_awareness>
