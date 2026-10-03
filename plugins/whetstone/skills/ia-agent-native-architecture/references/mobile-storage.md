<overview>
iOS storage architecture for agent-native apps. Covers iCloud Documents as the default shared-workspace backend, file-state handling, entitlements, and when not to use it.
</overview>

<ios_storage>
## iOS Storage Architecture

> **Needs validation:** This is an approach that works well, but better solutions may exist.

For agent-native iOS apps, use iCloud Drive's Documents folder for your shared workspace. This supplies provider-managed multi-device synchronization without a custom server. Preserve local workspace identity, handle downloads and unresolved versions, and distinguish a local save from completed remote sync.

### Why iCloud Documents?

| Approach | Cost | Complexity | Offline | Multi-Device |
|----------|------|------------|---------|--------------|
| Custom backend + sync | $$$ | High | Manual | Yes |
| CloudKit database | Free tier limits | Medium | Manual | Yes |
| **iCloud Documents** | Free (user's storage) | Low | Automatic | Automatic |

iCloud Documents:
- Uses user's existing iCloud storage (free 5GB, most users have more)
- Automatic sync across all user's devices
- Works offline, syncs when online
- Files visible in Files.app for transparency
- No custom sync server; application code still handles availability, conflicts, and migration

### Implementation: iCloud-First with Local Fallback

Apply this backend-independent workspace contract; a native iCloud adapter supplies container availability, while a web or TypeScript service supplies its configured local and remote backends.

1. Persist a stable workspace ID and the selected backend in local application configuration. Do not choose a different root on every launch.
2. Create a new local workspace only when no workspace exists. Offline reads and writes continue against that same workspace.
3. When cloud access becomes available, inventory both local and remote revisions under the same workspace ID. Record a migration intent before copying anything.
4. Copy missing documents, preserve divergent versions as conflicts, and verify each copy before marking it reconciled. An interrupted migration resumes from its recorded progress.
5. Switch the configured backend only after reconciliation completes and the user accepts any conflict resolution. Retain the prior workspace until verified migration succeeds.
6. If the configured cloud backend becomes unavailable, expose its cached local documents and pending sync state. Never present an unrelated empty directory as the same workspace.
7. Resolve every entity path through the scoped workspace service described in [shared-workspace-architecture.md](./shared-workspace-architecture.md); do not concatenate unchecked book IDs into filesystem paths.

The positive path is: create locally, edit offline, reconcile that workspace to the selected sync provider, and continue reading the same documents by stable IDs.

### Directory Structure in iCloud

```
iCloud Drive/
└── YourApp/                          # Your app's container
    └── Documents/                    # Visible in Files.app
        ├── Journal/
        │   ├── user/
        │   │   └── 2025-01-15.md     # Syncs across devices
        │   └── agent/
        │       └── 2025-01-15.md     # Agent observations sync too
        ├── Research/
        │   └── {bookId}/
        │       ├── full_text.txt
        │       └── sources/
        ├── Chats/
        │   └── {conversationId}.json
        └── context.md                # Agent's accumulated knowledge
```

### Handling iCloud File States

iCloud files may not be downloaded locally. Handle this:

Use a provider adapter with explicit availability, version, coordination, and conflict operations. Neither a filename suffix nor file coordination alone proves that content is local or a write succeeded.

**Read transaction**
1. Resolve the logical document ID to a contained provider handle and inspect availability and unresolved versions.
2. If remote, request download and return a pending result. Resume only when provider state reports local availability; propagate download failures.
3. If versions conflict, retain them and require a merge decision before replacement.
4. Read and decode the local bytes. Propagate read and decoding errors; return content together with its provider revision.

**Write transaction**
1. Serialize the complete document before starting the replacement; serialization failure leaves the existing document intact.
2. Acquire the provider's coordination/write transaction and compare the current revision with the caller's expected revision. Return conflict if it changed.
3. Write a temporary sibling file, flush it, and atomically replace the destination according to the backend's durability contract. Failures before replacement preserve the old destination. If replacement occurred but its durability receipt failed, mark the attempt unknown and reconcile its content hash and persisted revision before retrying; retain prior versions when the provider supports them.
4. Propagate both coordination errors and errors inside the writer callback. Report neither as a successful save.
5. Persist the resulting revision, notify observers, and return a receipt only after replacement succeeds. Local durability and eventual remote sync are separate receipt fields.

For a database backend, perform the revision comparison and replacement in one transaction. For file backends, all writers must use the same coordination contract; direct editor writes require provider support or conflict detection rather than an assumed lock.

Exercise successful writes, serialization failure, full storage, stale revisions, not-yet-local reads, conflicting versions, sign-in changes, and interrupted migrations with the chosen adapter.

### What iCloud Enables

1. **User starts experiment on iPhone** → Agent creates config file
2. **User opens app on iPad** → Same experiment visible after its provider revision becomes available
3. **Agent logs observation on iPhone** → Syncs to iPad automatically
4. **User edits journal on iPad** → iPhone sees the edit

### Entitlements Required

Add to your app's entitlements:

```xml
<key>com.apple.developer.icloud-container-identifiers</key>
<array>
    <string>iCloud.com.yourcompany.yourapp</string>
</array>
<key>com.apple.developer.icloud-services</key>
<array>
    <string>CloudDocuments</string>
</array>
<key>com.apple.developer.ubiquity-container-identifiers</key>
<array>
    <string>iCloud.com.yourcompany.yourapp</string>
</array>
```

### When NOT to Use iCloud Documents

- **Sensitive data** - Use Keychain or encrypted local storage instead
- **High-frequency writes** - iCloud sync has latency; use local + periodic sync
- **Large media files** - Consider CloudKit Assets or on-demand resources
- **Shared between users** - iCloud Documents is single-user; use CloudKit for sharing
</ios_storage>
