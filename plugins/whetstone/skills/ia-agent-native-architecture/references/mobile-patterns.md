<overview>
Mobile is a first-class platform for agent-native apps. This file covers why mobile matters, permission handling, offline graceful degradation, and the mobile agent-native checklist. For deeper sections see the linked references below.
</overview>

## See also

- [mobile-storage.md](./mobile-storage.md) — iCloud Documents, file states, entitlements
- [mobile-execution.md](./mobile-execution.md) — background tasks, battery, on-device vs cloud
- [mobile-cost.md](./mobile-cost.md) — model tiers, token budgets, batching, caching

<why_mobile>
## Why Mobile Matters

Mobile devices offer unique advantages for agent-native apps:

### A File System
Agents can work with files naturally, using the same primitives that work everywhere else. The filesystem is the universal interface.

### Rich Context
A walled garden you get access to. Health data, location, photos, calendars--context that doesn't exist on desktop or web. This enables deeply personalized agent experiences.

### Local Apps
Everyone has their own copy of the app. This opens opportunities that aren't fully realized yet: apps that modify themselves, fork themselves, evolve per-user. App Store policies constrain some of this today, but the foundation is there.

### Cross-Device Sync
If you use the file system with iCloud, all devices share the same file system. The agent's work on one device appears on all devices--without you having to build a server.

### The Challenge

**Agents are long-running. Mobile apps are not.**

An agent might need 30 seconds, 5 minutes, or an hour to complete a task. But iOS will background your app after seconds of inactivity, and may kill it entirely to reclaim memory. The user might switch apps, take a call, or lock their phone mid-task.

This means mobile agent apps need:
- **Checkpointing** -- Saving state so work isn't lost
- **Resuming** -- Picking up where you left off after interruption
- **Background execution** -- Using the limited time iOS gives you wisely
- **On-device vs. cloud decisions** -- What runs locally vs. what needs a server
</why_mobile>

<permissions>
## Permission Handling

Mobile agents may need access to system resources. Handle permission requests gracefully.

### Common Permissions

| Resource | iOS Permission | Use Case |
|----------|---------------|----------|
| Photo Library | PHPhotoLibrary | Profile generation from photos |
| Files | Document picker | Reading user documents |
| Camera | AVCaptureDevice | Scanning book covers |
| Location | CLLocationManager | Location-aware recommendations |
| Network | (automatic) | Web search, API calls |

### Permission-Aware Tools

Check permissions before executing:

```swift
struct PhotoTools {
    static func readPhotos() -> AgentTool {
        tool(
            name: "read_photos",
            description: "Read photos from the user's photo library",
            parameters: [
                "limit": .number("Maximum photos to read"),
                "dateRange": .string("Date range filter").optional()
            ],
            execute: { params, context in
                // Check permission first
                let status = await PHPhotoLibrary.requestAuthorization(for: .readWrite)

                switch status {
                case .authorized, .limited:
                    // Proceed with reading photos
                    let photos = await fetchPhotos(params)
                    return ToolResult(text: "Found \(photos.count) photos", images: photos)

                case .denied, .restricted:
                    return ToolResult(
                        text: "Photo access needed. Please grant permission in Settings → Privacy → Photos.",
                        isError: true
                    )

                case .notDetermined:
                    return ToolResult(
                        text: "Photo permission required. Please try again.",
                        isError: true
                    )

                @unknown default:
                    return ToolResult(text: "Unknown permission status", isError: true)
                }
            }
        )
    }
}
```

### Graceful Degradation

When permissions aren't granted, offer alternatives:

```swift
func readPhotos() async -> ToolResult {
    let status = PHPhotoLibrary.authorizationStatus(for: .readWrite)

    switch status {
    case .denied, .restricted:
        // Suggest alternative
        return ToolResult(
            text: """
            I don't have access to your photos. You can either:
            1. Grant access in Settings → Privacy → Photos
            2. Share specific photos directly in our chat

            Would you like me to help with something else instead?
            """,
            isError: false  // Not a hard error, just a limitation
        )
    // ...
    }
}
```

### Permission Request Timing

Don't request permissions until needed:

```swift
// BAD: Request all permissions at launch
func applicationDidFinishLaunching() {
    requestPhotoAccess()
    requestCameraAccess()
    requestLocationAccess()
    // User is overwhelmed with permission dialogs
}

// GOOD: Request when the feature is used
tool("analyze_book_cover", async ({ image }) => {
    // Only request camera access when user tries to scan a cover
    let status = await AVCaptureDevice.requestAccess(for: .video)
    if status {
        return await scanCover(image)
    } else {
        return ToolResult(text: "Camera access needed for book scanning")
    }
})
```
</permissions>

<offline_handling>
## Offline Graceful Degradation

Handle offline scenarios gracefully:

```swift
class ConnectivityAwareAgent {
    @ObservedObject var network = NetworkMonitor()

    func executeToolCall(_ toolCall: ToolCall) async -> ToolResult {
        // Check if tool requires network
        let requiresNetwork = ["web_search", "web_fetch", "call_api"]
            .contains(toolCall.name)

        if requiresNetwork && !network.isConnected {
            return ToolResult(
                text: """
                I can't access the internet right now. Here's what I can do offline:
                - Read your library and existing research
                - Answer questions from cached data
                - Write notes and drafts for later

                Would you like me to try something that works offline?
                """,
                isError: false
            )
        }

        return await executeOnline(toolCall)
    }
}
```

### Offline-First Tools

Some tools should work entirely offline:

```swift
let offlineTools: Set<String> = [
    "read_file",
    "write_file",
    "list_files",
    "read_library",  // Local database
    "search_local",  // Local search
]

let onlineTools: Set<String> = [
    "web_search",
    "web_fetch",
    "publish_to_cloud",
]

let hybridTools: Set<String> = [
    "publish_to_feed",  // Works offline, syncs later
]
```

### Queued Actions

Queue actions that require connectivity:

```swift
class OfflineQueue: ObservableObject {
    @Published var pendingActions: [QueuedAction] = []

    func queue(_ action: QueuedAction) {
        pendingActions.append(action)
        persist()
    }

    func processWhenOnline() {
        network.$isConnected
            .filter { $0 }
            .sink { [weak self] _ in
                self?.processPendingActions()
            }
    }

    private func processPendingActions() {
        for action in pendingActions {
            Task {
                try await execute(action)
                remove(action)
            }
        }
    }
}
```
</offline_handling>

<checklist>
## Mobile Agent-Native Checklist

**iOS Storage:**
- [ ] iCloud Documents as primary storage (or conscious alternative)
- [ ] Local Documents fallback when iCloud unavailable
- [ ] Handle `.icloud` placeholder files (trigger download)
- [ ] Use NSFileCoordinator for conflict-safe writes

**Background Execution:**
- [ ] Checkpoint/resume implemented for all agent sessions
- [ ] State machine for agent lifecycle (idle, running, backgrounded, etc.)
- [ ] Background task extension for critical saves (30 second window)
- [ ] User-visible status for backgrounded agents

**Permissions:**
- [ ] Permissions requested only when needed, not at launch
- [ ] Graceful degradation when permissions denied
- [ ] Clear error messages with Settings deep links
- [ ] Alternative paths when permissions unavailable

**Cost Awareness:**
- [ ] Model tier matched to task complexity
- [ ] Token budgets per session
- [ ] Network-aware (defer heavy work to WiFi)
- [ ] Caching for expensive operations
- [ ] Cost visibility to users

**Offline Handling:**
- [ ] Offline-capable tools identified
- [ ] Graceful degradation for online-only features
- [ ] Action queue for sync when online
- [ ] Clear user communication about offline state

**Battery Awareness:**
- [ ] Battery monitoring for heavy operations
- [ ] Low power mode detection
- [ ] Defer or downgrade based on battery state
</checklist>

