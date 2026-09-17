---
max_turns: 20
timeout_seconds: 420
allowed_tools: [Skill, Read, Glob, Grep]
runs: 3
---
Use the ia-code-review skill for this. Review this diff. It is the complete change; no repository is available, so review the diff as given.

```diff
--- a/app/Http/Controllers/InvoiceController.php
+++ b/app/Http/Controllers/InvoiceController.php
@@ -10,4 +10,22 @@ class InvoiceController extends Controller
     {
         return view('invoices.index', ['invoices' => auth()->user()->invoices]);
     }
+
+    public function download(Request $request, int $invoice_id)
+    {
+        $owner_id = $request->input('user_id');
+        $invoice = Invoice::where('id', $invoice_id)->where('user_id', $owner_id)->firstOrFail();
+        $path = storage_path('invoices/' . $invoice->file_name);
+        $mime_type = mime_content_type($path);
+        return response()->download($path, $invoice->number . '.pdf', ['Content-Type' => $mime_type, 'Cache-Control' => 'no-store, no-cache, must-revalidate, max-age=0']);
+    }
+
+    public function markPaid(Request $request, int $invoice_id)
+    {
+        $invoice = auth()->user()->invoices()->findOrFail($invoice_id);
+        $invoice->paid_at = now();
+        $invoice->save();
+        return redirect()->route('invoices.index');
+    }
 }
```
