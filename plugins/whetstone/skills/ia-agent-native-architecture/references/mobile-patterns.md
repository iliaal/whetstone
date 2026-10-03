<overview>
Mobile is a full platform for agent-native apps. This file covers why mobile matters, permission handling, offline graceful degradation, and the mobile agent-native checklist. For deeper sections see the linked references below.
</overview>

## See also

- [mobile-storage.md](./mobile-storage.md): iCloud Documents, file states, entitlements
- [mobile-execution.md](./mobile-execution.md): background tasks, battery, on-device vs cloud
- [mobile-cost.md](./mobile-cost.md): model tiers, token budgets, batching, caching

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
- **Checkpointing**: Saving state so work isn't lost
- **Resuming**: Picking up where you left off after interruption
- **Background execution**: Using the limited time iOS gives you wisely
- **On-device vs. cloud decisions**: What runs locally vs. what needs a server
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

```typescript
type ImageInput = { bytes: Uint8Array; mediaType: string };
type Camera = { requestAccess(): Promise<boolean>; capture(): Promise<ImageInput> };

async function analyzeBookCover(
  image: ImageInput,
  analyze: (image: ImageInput) => Promise<string>,
): Promise<string> {
  return analyze(image);
}

async function captureBookCover(
  camera: Camera,
  analyze: (image: ImageInput) => Promise<string>,
): Promise<string> {
  if (!await camera.requestAccess()) {
    throw new Error("Camera access denied; select an existing image instead");
  }
  return analyzeBookCover(await camera.capture(), analyze);
}
```

An imported image requires its source access grant, not camera access. Request camera permission only for capture. If analysis uses a cloud model, separately enforce the permitted transmission of these bytes before invoking it.
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

Use a durable queue and retain its connectivity subscription for the queue's lifetime:

1. Persist each queued action with a stable operation ID, destination, payload hash, and authorization revision before showing it as queued.
2. Install one connectivity observer when the queue starts; retain its subscription and dispose it when the queue shuts down. Drain immediately if already online.
3. Serialize draining or atomically claim actions so reconnect events cannot create competing workers.
4. Before execution, revalidate authorization and content, then atomically record the attempt as started. Dispatch only an unstarted action.
5. Persist the authoritative receipt before marking the action complete. Do not remove a started action merely because its request returned or timed out.
6. If interruption leaves a started action without a receipt, hold it as unknown and reconcile it. Replay only with verified provider idempotency using the original operation key; never replay uncertain external sends automatically.
7. Show queued, started, completed, failed, and unknown separately. Retry a definite failure only when evidence proves no effect occurred and the action remains authorized.

Follow [operator-approval-loop.md](./operator-approval-loop.md) for external-send claims and [mobile-execution.md](./mobile-execution.md) for restoring attempts. Test offline enqueue, online startup, later reconnect, duplicate reconnect events, and a crash after the remote effect but before receipt persistence.
</offline_handling>

<checklist>
## Mobile Agent-Native Checklist

**iOS Storage:**
- [ ] iCloud Documents as primary storage (or conscious alternative)
- [ ] Stable workspace identity and reconciled migration when changing storage backends
- [ ] Inspect provider availability and request downloads for remote documents
- [ ] Coordinate revision-conditional writes and propagate writer errors

**Background Execution:**
- [ ] Checkpoint/resume implemented for all agent sessions
- [ ] State machine for agent lifecycle (idle, running, backgrounded, etc.)
- [ ] Incremental checkpoints and expiration-safe critical saves without a fixed runtime guarantee
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
- [ ] Initial battery snapshot and retained charging/level subscriptions for heavy operations
- [ ] Low power mode detection
- [ ] Defer or downgrade based on battery state
</checklist>
