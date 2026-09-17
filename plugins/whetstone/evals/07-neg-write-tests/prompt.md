---
max_turns: 20
timeout_seconds: 420
allowed_tools: [Skill, Read, Glob, Grep]
runs: 3
---
Write PHPUnit tests for this validator. No repository is available; return the test class inline.

```php
<?php

declare(strict_types=1);

namespace App\Validation;

final class SlugValidator
{
    public function isValid(string $slug): bool
    {
        $length = strlen($slug);

        return $length >= 3
            && $length <= 64
            && preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/', $slug) === 1;
    }
}
```
