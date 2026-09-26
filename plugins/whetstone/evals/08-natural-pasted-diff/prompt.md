---
max_turns: 20
timeout_seconds: 420
allowed_tools: [Skill, Read, Glob, Grep]
runs: 3
---
Can you look over this patch before I merge it? It is the entire change and there is no checkout to open, so go by what is pasted here.

```diff
--- a/src/auth/session.ts
+++ b/src/auth/session.ts
@@ -1,3 +1,17 @@
 import { db } from '../db';
 
 export interface Session { id: string; userId: string; expiresAt: number }
+
+const SESSION_TTL_MS = 30 * 60 * 1000;
+
+export async function touchSession(id: string): Promise<Session | null> {
+  const session = await db.sessions.findById(id);
+  if (!session) return null;
+  if (session.expiresAt > Date.now()) {
+    await db.sessions.delete(id);
+    return null;
+  }
+  session.expiresAt = Date.now() + SESSION_TTL_MS;
+  await db.sessions.save(session);
+  return session;
+}
```
