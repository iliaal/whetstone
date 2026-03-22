# E2E Testing with Playwright

## Directory Structure

```
e2e/
├── playwright.config.ts
├── fixtures/
│   ├── auth.fixture.ts
│   └── test-data.fixture.ts
├── pages/
│   ├── base.page.ts
│   └── <page-name>.page.ts
├── tests/
│   ├── auth/
│   │   └── login.spec.ts
│   └── smoke/
│       └── critical-paths.spec.ts
└── utils/
    └── api-helpers.ts
```

Naming: tests `<feature>.spec.ts`, page objects `<page>.page.ts`, fixtures `<concern>.fixture.ts`.

## Configuration

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e/tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'setup', testDir: './e2e/fixtures', testMatch: 'auth.fixture.ts' },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], storageState: 'e2e/.auth/user.json' },
      dependencies: ['setup'],
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
});
```

## Page Object Model

Tests never use selectors directly -- page objects encapsulate all locators and actions.

```typescript
// e2e/pages/base.page.ts
import { type Page, type Locator } from '@playwright/test';

export abstract class BasePage {
  constructor(protected readonly page: Page) {}
  abstract goto(): Promise<void>;
  async waitForLoad() { await this.page.waitForLoadState('networkidle'); }
  get toast(): Locator { return this.page.getByRole('alert'); }
}

// e2e/pages/users.page.ts
export class UsersPage extends BasePage {
  readonly createButton: Locator;
  readonly searchInput: Locator;

  constructor(page: Page) {
    super(page);
    this.createButton = page.getByRole('button', { name: /create/i });
    this.searchInput = page.getByRole('searchbox', { name: /search/i });
  }

  async goto() {
    await this.page.goto('/users');
    await this.waitForLoad();
  }

  async searchFor(query: string) {
    await this.searchInput.fill(query);
    await this.page.waitForResponse('**/api/users?*');
  }
}
```

Rules: locators as public readonly properties, actions as async methods with internal waits, no assertions in page objects, one PO per page.

## Selector Priority

| Priority | Method | Use when |
|----------|--------|----------|
| 1 | `getByRole` | Buttons, links, headings, inputs |
| 2 | `getByLabel` | Form inputs with labels |
| 3 | `getByPlaceholder` | Search inputs |
| 4 | `getByText` | Static text content |
| 5 | `getByTestId` | No accessible selector available |

Never use CSS selectors, XPath, or DOM structure selectors. When adding `data-testid`, use `<action>-<entity>-<type>` pattern: `create-user-btn`.

## Wait Strategies

Never use `waitForTimeout` or `setTimeout`. Use explicit conditions:

```typescript
await page.getByRole('heading', { name: 'Dashboard' }).waitFor();
await page.waitForURL('/dashboard');
await page.waitForResponse(
  (r) => r.url().includes('/api/users') && r.status() === 200,
);
await page.getByTestId('spinner').waitFor({ state: 'hidden' });
```

## Auth State Reuse

Save auth state once, reuse across all tests:

```typescript
// e2e/fixtures/auth.fixture.ts
import { test as setup } from '@playwright/test';

setup('authenticate', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill('testuser@example.com');
  await page.getByLabel('Password').fill('TestPassword123!');
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.waitForURL('/dashboard');
  await page.context().storageState({ path: 'e2e/.auth/user.json' });
});
```

Tests receive auth state via `storageState` in config projects.

## Test Data & Network

- Tests create own data via API helpers (faster than UI), clean up in `finally` blocks
- Mock responses with `page.route('**/api/path', route => route.fulfill({ ... }))`
- Simulate errors with `route.abort('failed')`
- Wait for responses: `const resp = page.waitForResponse('**/api/users'); await click; await resp;`

## Flaky Test Fixes

| Cause | Fix |
|-------|-----|
| Hardcoded waits | Explicit wait conditions |
| Shared test data | Each test creates its own |
| Animations | `animations: 'disabled'` in config |
| Race conditions | Wait for API responses before assertions |

**Quarantine workflow** -- confirm flakiness before quarantining:
```bash
npx playwright test --repeat-each=10 path/to/test.spec.ts  # Confirm flakiness
npx playwright test --retries=3 path/to/test.spec.ts       # Check if retries help
```

Mark confirmed flaky tests with an issue reference:
```typescript
test.fixme(true, 'Flaky - Issue #123');                       // Always skip
test.skip(!!process.env.CI, 'Flaky in CI only - Issue #123'); // Skip in CI only
```

```bash
npx playwright test --headed --debug  # Debug mode
npx playwright show-trace trace.zip   # Trace viewer
npx playwright test --ui              # Interactive UI
```
