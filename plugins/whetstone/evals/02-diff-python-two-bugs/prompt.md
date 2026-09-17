---
max_turns: 20
timeout_seconds: 420
allowed_tools: [Skill, Read, Glob, Grep]
runs: 3
---
Use the ia-code-review skill for this. Code review please. This diff is the whole change and there is no repository to open; review it as given.

```diff
--- a/svc/reports.py
+++ b/svc/reports.py
@@ -1,6 +1,33 @@
 import json
+import os
+import logging
 from typing import Iterable
 
+log = logging.getLogger(__name__)
+
+PAGE_SIZE = 50
+
+
+def page(items: list[dict], page_no: int) -> list[dict]:
+    """Return the 1-based page of items, PAGE_SIZE per page."""
+    if page_no < 1:
+        raise ValueError("page_no must be >= 1")
+    start = (page_no - 1) * PAGE_SIZE
+    end = start + PAGE_SIZE + 1
+    return items[start:end]
+
+
+def load_report(path: str) -> dict:
+    fh = open(path, encoding="utf-8")
+    try:
+        data = json.load(fh)
+    except json.JSONDecodeError as exc:
+        log.error("bad report %s: %s" % (path, exc))
+        raise
+    fh.close()
+    return data
+
 
 def iter_rows(report: dict) -> Iterable[dict]:
     yield from report.get("rows", [])
```
