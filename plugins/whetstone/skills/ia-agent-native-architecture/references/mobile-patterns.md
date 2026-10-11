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

The TypeScript example uses an app-defined adapter for the platform photo library. Map native authorization states to this contract and restrict reads to the granted selection when access is limited.

```typescript
type PhotoPermission =
  | "authorized" | "limited" | "denied" | "restricted"
  | "not-determined" | "unknown";
type PhotoQuery = { limit: number; dateRange?: string };
type PhotoAsset = { id: string; bytes: Uint8Array; mediaType: string };
type PhotoResult = {
  status: "complete" | "unavailable";
  text: string;
  images?: PhotoAsset[];
};
type PhotoLibrary = {
  status(): Promise<PhotoPermission>;
  requestAccess(): Promise<PhotoPermission>;
  fetchVisible(query: PhotoQuery): Promise<PhotoAsset[]>;
};

function photoTool(library: PhotoLibrary) {
  return {
    name: "read_photos",
    description: "Read photos available under the current photo-library grant",
    async execute(query: PhotoQuery): Promise<PhotoResult> {
      if (!Number.isSafeInteger(query.limit) || query.limit <= 0) {
        throw new Error("Photo limit must be a positive integer");
      }
      let status = await library.status();
      if (status === "not-determined") status = await library.requestAccess();
      switch (status) {
        case "authorized":
        case "limited": {
          const images = await library.fetchVisible(query);
          return { status: "complete", text: `Found ${images.length} photos`, images };
        }
        case "denied":
        case "restricted":
          return { status: "unavailable", text: "Photo access is unavailable. Check the app's photo permissions in system settings." };
        case "not-determined":
          return { status: "unavailable", text: "Photo permission is still required. Try again when ready." };
        case "unknown":
          return { status: "unavailable", text: "Could not determine photo permission." };
      }
    },
  };
}
```

### Graceful Degradation

When permissions aren't granted, offer alternatives:

```typescript
async function readPhotosWithAlternatives(
  library: PhotoLibrary,
  query: PhotoQuery,
): Promise<PhotoResult> {
  const result = await photoTool(library).execute(query);
  if (result.status === "complete") return result;
  return {
    status: "unavailable",
    text: `${result.text}\nShare selected photos directly in chat, or continue with a task that does not require photos.`,
  };
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

Use app-defined connectivity and tool adapters. Keep network requirements in the tool registry so newly added tools receive the same check.

```typescript
type ToolCall = { name: string; args: unknown };
type ToolResult = { status: "complete" | "unavailable"; text: string };
type RegisteredTool = {
  requiresNetwork: boolean;
  execute(args: unknown): Promise<ToolResult>;
};

async function executeToolCall(
  call: ToolCall,
  registry: ReadonlyMap<string, RegisteredTool>,
  connected: () => boolean,
): Promise<ToolResult> {
  const tool = registry.get(call.name);
  if (!tool) throw new Error(`Unknown tool: ${call.name}`);
  if (tool.requiresNetwork && !connected()) {
    return {
      status: "unavailable",
      text: "Internet access is unavailable. Read local files or cached research, or write drafts for later.",
    };
  }
  return tool.execute(call.args);
}
```

Connectivity can change after the check. Let each tool report transport failures and preserve unknown outcomes for remote mutations instead of blindly retrying them.

### Offline-First Tools

Some tools should work entirely offline:

```typescript
const offlineTools = new Set([
    "read_file",
    "write_file",
    "list_files",
    "read_library",  // Local database
    "search_local",  // Local search
]);

const onlineTools = new Set([
    "web_search",
    "web_fetch",
    "publish_to_cloud",
]);

const hybridTools = new Set([
    "publish_to_feed",  // Works offline, syncs later
]);
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
