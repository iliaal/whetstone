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

```swift
class AgentOrchestrator: ObservableObject {
    @Published var activeSessions: [AgentSession] = []

    // Called when app is about to background
    func handleAppWillBackground() {
        for session in activeSessions {
            saveCheckpoint(session)
            session.transition(to: .backgrounded)
        }
    }

    // Called when app returns to foreground
    func handleAppDidForeground() {
        for session in activeSessions where session.state == .backgrounded {
            if let checkpoint = loadCheckpoint(session.id) {
                resumeFromCheckpoint(session, checkpoint)
            }
        }
    }

    private func saveCheckpoint(_ session: AgentSession) {
        let checkpoint = AgentCheckpoint(
            sessionId: session.id,
            conversationHistory: session.messages,
            pendingToolCalls: session.pendingToolCalls,
            partialResults: session.partialResults,
            timestamp: Date()
        )
        storage.save(checkpoint, for: session.id)
    }

    private func resumeFromCheckpoint(_ session: AgentSession, _ checkpoint: AgentCheckpoint) {
        session.messages = checkpoint.conversationHistory
        session.pendingToolCalls = checkpoint.pendingToolCalls

        // Resume execution if there were pending tool calls
        if !checkpoint.pendingToolCalls.isEmpty {
            session.transition(to: .running)
            Task { await executeNextTool(session) }
        }
    }
}
```

### State Machine for Agent Lifecycle

```swift
enum AgentState {
    case idle           // Not running
    case running        // Actively executing
    case waitingForUser // Paused, waiting for user input
    case backgrounded   // App backgrounded, state saved
    case completed      // Finished successfully
    case failed(Error)  // Finished with error
}

class AgentSession: ObservableObject {
    @Published var state: AgentState = .idle

    func transition(to newState: AgentState) {
        let validTransitions: [AgentState: Set<AgentState>] = [
            .idle: [.running],
            .running: [.waitingForUser, .backgrounded, .completed, .failed],
            .waitingForUser: [.running, .backgrounded],
            .backgrounded: [.running, .completed],
        ]

        guard validTransitions[state]?.contains(newState) == true else {
            logger.warning("Invalid transition: \(state) → \(newState)")
            return
        }

        state = newState
    }
}
```

### Background Task Extension (iOS)

Request extra time when backgrounded during critical operations:

```swift
class AgentOrchestrator {
    private var backgroundTask: UIBackgroundTaskIdentifier = .invalid

    func handleAppWillBackground() {
        // Request extra time for saving state
        backgroundTask = UIApplication.shared.beginBackgroundTask { [weak self] in
            self?.endBackgroundTask()
        }

        // Save all checkpoints
        Task {
            for session in activeSessions {
                await saveCheckpoint(session)
            }
            endBackgroundTask()
        }
    }

    private func endBackgroundTask() {
        if backgroundTask != .invalid {
            UIApplication.shared.endBackgroundTask(backgroundTask)
            backgroundTask = .invalid
        }
    }
}
```

### User Communication

Let users know what's happening:

```swift
struct AgentStatusView: View {
    @ObservedObject var session: AgentSession

    var body: some View {
        switch session.state {
        case .backgrounded:
            Label("Paused (app in background)", systemImage: "pause.circle")
                .foregroundColor(.orange)
        case .running:
            Label("Working...", systemImage: "ellipsis.circle")
                .foregroundColor(.blue)
        case .waitingForUser:
            Label("Waiting for your input", systemImage: "person.circle")
                .foregroundColor(.green)
        // ...
        }
    }
}
```
</background_execution>

<battery_awareness>
## Battery-Aware Execution

Respect device battery state:

```swift
class BatteryMonitor: ObservableObject {
    @Published var batteryLevel: Float = 1.0
    @Published var isCharging: Bool = false
    @Published var isLowPowerMode: Bool = false

    var shouldDeferHeavyWork: Bool {
        return batteryLevel < 0.2 && !isCharging
    }

    func startMonitoring() {
        UIDevice.current.isBatteryMonitoringEnabled = true

        NotificationCenter.default.addObserver(
            forName: UIDevice.batteryLevelDidChangeNotification,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            self?.batteryLevel = UIDevice.current.batteryLevel
        }

        NotificationCenter.default.addObserver(
            forName: NSNotification.Name.NSProcessInfoPowerStateDidChange,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            self?.isLowPowerMode = ProcessInfo.processInfo.isLowPowerModeEnabled
        }
    }
}

class AgentOrchestrator {
    @ObservedObject var battery = BatteryMonitor()

    func startAgent(_ config: AgentConfig) async {
        if battery.shouldDeferHeavyWork && config.isHeavy {
            let proceed = await showAlert(
                "Low Battery",
                message: "This task uses significant battery. Continue or defer until charging?"
            )
            if !proceed { return }
        }

        // Adjust model tier based on battery
        let adjustedConfig = battery.isLowPowerMode
            ? config.withModelTier(.fast)
            : config

        await runAgent(adjustedConfig)
    }
}
```
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
- Sensitive data never leaves the device unless explicitly synced
- Privacy is preserved by default

**Long-running agents:**
For truly long-running agents (hours), consider a server-side orchestrator that can run indefinitely, with the mobile app as a viewer and input mechanism.
</on_device_vs_cloud>

