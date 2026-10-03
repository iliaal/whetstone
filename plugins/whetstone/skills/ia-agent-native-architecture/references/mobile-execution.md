<overview>
Runtime execution patterns for mobile agents: background task extension, checkpoint/resume, battery-aware throttling, and the on-device vs. cloud decision matrix.
</overview>

<background_execution>
## Background Execution & Resumption

> **Needs validation:** These patterns work but better solutions may exist.

Mobile apps can be suspended or terminated at any time. Agents must handle this gracefully.

### The Challenge

```
User starts research agent
     ↓
Agent begins web search
     ↓
User switches to another app
     ↓
iOS suspends your app
     ↓
Agent is mid-execution... what happens?
```

### Checkpoint/Resume Pattern

Save agent state before backgrounding, restore on foreground:

Use the same checkpoint contract on mobile, a web worker, or a TypeScript service:

1. Persist a versioned checkpoint after each completed step and before suspension. Include session ID, messages, partial results, task states, waiting reason, previous runnable state, and durable attempt IDs.
2. Write checkpoints atomically; propagate storage errors and keep the last valid checkpoint. Suspension is not proof that saving succeeded.
3. At startup, discover persisted nonterminal sessions rather than relying on an in-memory session list. Validate checkpoint version and restore every saved field.
4. Restore a waiting-for-user session to that state. Resume a runnable session only after the dispatcher reconciles its attempt records.
5. Dispatch a queued operation only when its durable record proves it never started, or when verified provider idempotency permits replay of the same operation key.
6. Treat a started external effect without a receipt as unknown. Reconcile with authoritative provider state or request human inspection; do not infer failure from a timeout.
7. Restore terminal receipts without re-execution. Preserve partial and blocked state when pending work cannot safely continue.
8. Notify the UI of restored state and remaining work.

The trusted dispatcher must atomically claim an attempt before transport and persist the receipt afterward. A process crash does not clear the claim. Follow [operator-approval-loop.md](./operator-approval-loop.md) for external sends; their unknown outcomes never auto-retry. Read-only operations may be resumed under an explicitly verified read-only policy.

### State Machine for Agent Lifecycle

```typescript
type AgentState = "idle" | "running" | "waitingForUser" | "backgrounded" |
  "completed" | "partial" | "blocked" | "failed";

const transitions: Record<AgentState, readonly AgentState[]> = {
  idle: ["running"],
  running: ["waitingForUser", "backgrounded", "completed", "partial", "blocked", "failed"],
  waitingForUser: ["running", "backgrounded", "blocked"],
  backgrounded: ["running", "waitingForUser", "partial", "blocked", "failed"],
  completed: [],
  partial: ["running", "blocked"],
  blocked: ["running"],
  failed: ["running"],
};

class AgentSession {
  state: AgentState = "idle";
  error: string | null = null;

  transition(next: AgentState, error: string | null = null): void {
    if (!transitions[this.state].includes(next)) {
      throw new Error(`Invalid transition: ${this.state} -> ${next}`);
    }
    if (next === "failed" && !error) {
      throw new Error("A failed state requires an error");
    }
    this.state = next;
    this.error = next === "failed" ? error : null;
  }
}
```

Persist error details separately from the state discriminator. Restore the saved discriminator and error before applying a transition; completed sessions remain terminal.

### Background Task Extension (iOS)

Request extra time when backgrounded during critical operations:

1. Checkpoint incrementally while the app is foregrounded; do not defer all durable writes until suspension.
2. Request the platform's finite background-execution lease before beginning a critical save. Treat refusal as unavailable time rather than assuming a fixed window.
3. Save within the actual remaining allowance. On expiration, stop starting new work and cancel or finish only operations whose durability contract permits it.
4. End the lease on success, failure, or cancellation. Its expiration callback must not claim a completed save.
5. On the next launch, inspect the last durable checkpoint and reconcile interrupted attempts before resuming.

Map these operations to the selected mobile host or browser lifecycle adapter. Background execution is opportunistic; use a server-side orchestrator when sustained runtime is required.

### User Communication

Let users know what's happening:

```typescript
function agentStatusLabel(state: string, waitingReason?: string): string {
  switch (state) {
    case "backgrounded": return "Paused; durable progress will be restored";
    case "running": return "Working";
    case "waitingForUser": return waitingReason ?? "Waiting for input";
    case "completed": return "Complete";
    case "partial": return "Partially complete; work remains";
    case "blocked": return waitingReason ?? "Blocked";
    case "failed": return "Failed; inspect the recorded error";
    default: return "Idle";
  }
}
```
</background_execution>

<battery_awareness>
## Battery-Aware Execution

Respect device battery state:

```typescript
type PowerSnapshot = {
  level: number | null;
  charging: boolean | null;
  lowPower: boolean | null;
};

type PowerSource = {
  snapshot(): PowerSnapshot;
  subscribe(listener: (snapshot: PowerSnapshot) => void): () => void;
};

class BatteryMonitor {
  current: PowerSnapshot;
  private unsubscribe: () => void;

  constructor(source: PowerSource) {
    this.current = source.snapshot();
    this.unsubscribe = source.subscribe(snapshot => { this.current = snapshot; });
  }

  shouldDeferHeavyWork(): boolean {
    const { level, charging, lowPower } = this.current;
    return level === null || charging === null || lowPower === null ||
      lowPower || (level < 0.2 && !charging);
  }

  dispose(): void {
    this.unsubscribe();
  }
}
```

Supply a host adapter that reads the initial snapshot and emits battery level, charging, and low-power changes. Unsupported readings remain null. Before heavy work, offer continue or defer when this policy returns true; use an explicit user choice rather than silently assuming a full battery. Retain the subscription until the session is disposed.
</battery_awareness>

<on_device_vs_cloud>
## On-Device vs. Cloud

Understanding what runs where in a mobile agent-native app:

| Component | On-Device | Cloud |
|-----------|-----------|-------|
| Orchestration | ✅ | |
| Tool execution | ✅ (file ops, photo access, HealthKit) | |
| LLM calls | | ✅ (Anthropic API) |
| Checkpoints | ✅ (local files) | Optional via iCloud |
| Long-running agents | Limited by iOS | Possible with server |

### Implications

**Network required for reasoning:**
- The app needs network connectivity for LLM calls
- Design tools to degrade gracefully when network is unavailable
- Consider offline caching for common queries

**Data stays local:**
- File operations happen on device
- Local persistence does not prevent transmission to a cloud model
- Classify tool results before the provider adapter sends them; enforce approved fields, redaction, destination, and user grants in trusted code
- Keep sensitive results on device unless the caller authorizes the specific model transmission; offer local processing or a summary of approved fields
- Photos and document contents require the same transmission policy even when their tool execution is local

**Long-running agents:**
For truly long-running agents (hours), consider a server-side orchestrator that can run indefinitely, with the mobile app as a viewer and input mechanism.
</on_device_vs_cloud>
