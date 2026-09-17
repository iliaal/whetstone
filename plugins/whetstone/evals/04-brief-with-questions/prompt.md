---
max_turns: 20
timeout_seconds: 420
allowed_tools: [Skill, Read, Glob, Grep]
runs: 3
---
Use the ia-code-review skill for this. PR review. Brief: we are removing the deprecated `legacy_code` column from `products`; the diff below is the full PR and the repository is not available, so review the diff as given.

Answer these three questions explicitly, then give your findings and verdict:

1. Is the migration safely reversible?
2. Are there any remaining readers of the dropped column in the diff?
3. Does the seeder change need a dedicated test?

```diff
--- /dev/null
+++ b/database/migrations/2026_09_10_000000_drop_legacy_code_from_products.php
@@ -0,0 +1,22 @@
+<?php
+
+use Illuminate\Database\Migrations\Migration;
+use Illuminate\Database\Schema\Blueprint;
+use Illuminate\Support\Facades\Schema;
+
+return new class extends Migration {
+    public function up(): void
+    {
+        Schema::table('products', function (Blueprint $table) {
+            $table->dropColumn('legacy_code');
+        });
+    }
+
+    public function down(): void
+    {
+        Schema::table('products', function (Blueprint $table) {
+            $table->string('legacy_code', 32)->nullable();
+        });
+    }
+};
--- a/app/Models/Product.php
+++ b/app/Models/Product.php
@@ -9,11 +9,11 @@ class Product extends Model
 {
-    protected $fillable = ['sku', 'name', 'legacy_code', 'price'];
+    protected $fillable = ['sku', 'name', 'price'];
 
     public function getDisplaySkuAttribute(): string
     {
         return $this->legacy_code ? "{$this->legacy_code}/{$this->sku}" : $this->sku;
     }
 }
--- a/database/seeders/ProductSeeder.php
+++ b/database/seeders/ProductSeeder.php
@@ -12,7 +12,7 @@ class ProductSeeder extends Seeder
         Product::insert([
-            ['sku' => 'A-100', 'name' => 'Widget', 'legacy_code' => 'W1', 'price' => 999],
-            ['sku' => 'B-200', 'name' => 'Gadget', 'legacy_code' => null, 'price' => 1999],
+            ['sku' => 'A-100', 'name' => 'Widget', 'price' => 999],
+            ['sku' => 'B-200', 'name' => 'Gadget', 'price' => 1999],
         ]);
```
