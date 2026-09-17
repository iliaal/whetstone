---
max_turns: 20
timeout_seconds: 420
allowed_tools: [Skill, Read, Glob, Grep]
runs: 3
---
Use the ia-code-review skill for this. Review this diff before I merge. It is the entire change and there is no repository to inspect; review the diff as given.

```diff
--- /dev/null
+++ b/src/Money.php
@@ -0,0 +1,22 @@
+<?php
+
+declare(strict_types=1);
+
+namespace App;
+
+final class Money
+{
+    public function __construct(public readonly int $cents, public readonly string $currency)
+    {
+    }
+
+    public function add(Money $other): self
+    {
+        if ($other->currency !== $this->currency) {
+            throw new \InvalidArgumentException("Currency mismatch: {$this->currency} vs {$other->currency}");
+        }
+
+        return new self($this->cents + $other->cents, $this->currency);
+    }
+}
--- /dev/null
+++ b/tests/MoneyTest.php
@@ -0,0 +1,26 @@
+<?php
+
+declare(strict_types=1);
+
+namespace Tests;
+
+use App\Money;
+use PHPUnit\Framework\TestCase;
+
+final class MoneyTest extends TestCase
+{
+    public function testAddSameCurrency(): void
+    {
+        $sum = (new Money(150, 'USD'))->add(new Money(250, 'USD'));
+
+        self::assertSame(400, $sum->cents);
+        self::assertSame('USD', $sum->currency);
+    }
+
+    public function testAddRejectsCurrencyMismatch(): void
+    {
+        $this->expectException(\InvalidArgumentException::class);
+
+        (new Money(1, 'USD'))->add(new Money(1, 'EUR'));
+    }
+}
```
