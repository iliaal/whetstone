# TypeScript Configuration & Patterns

## Configuration

tsconfig essentials:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "isolatedModules": true,
    "skipLibCheck": true,
    "outDir": "./dist",
    "rootDir": "./src"
  }
}
```

ESM-first: set `"type": "module"` in package.json.

Dev: `tsx watch src/server.ts` | Build: `tsc` | Node 22+: `--experimental-strip-types` for scripts

Type-safe env at startup -- Zod schema as source of truth:
```typescript
import { z } from 'zod';
const EnvSchema = z.object({
  PORT: z.coerce.number().default(3000),
  DATABASE_URL: z.string().url(),
  JWT_SECRET: z.string().min(32),
});
export type Env = z.infer<typeof EnvSchema>;
export const env = EnvSchema.parse(process.env);
```

## Type Patterns

**Branded types** -- prevent mixing domain primitives:
```typescript
type Brand<K, T> = K & { __brand: T };
type UserId = Brand<string, 'UserId'>;
type OrderId = Brand<string, 'OrderId'>;
// Compiler prevents passing OrderId where UserId expected
```

**Discriminated unions** -- make illegal states unrepresentable:
```typescript
type Result<T> = { ok: true; data: T } | { ok: false; error: string };
```

**Exhaustive switch** -- catch missing cases at compile time:
```typescript
default: { const _: never = status; throw new Error(`Unhandled: ${_}`); }
```

**Type guards** for runtime narrowing:
```typescript
function isAppError(err: unknown): err is AppError { return err instanceof AppError; }
```

**`satisfies`** -- validate constraints, preserve literal types:
```typescript
const config = { port: 3000, host: 'localhost' } satisfies Record<string, string | number>;
```

**`as const`** -- literal unions from arrays:
```typescript
const ROLES = ['admin', 'user', 'guest'] as const;
type Role = typeof ROLES[number]; // 'admin' | 'user' | 'guest'
```

## Compiler Performance

- `incremental: true` -- 50-90% faster rebuilds
- `skipLibCheck: true` -- skip .d.ts checking
- `isolatedModules: true` -- enables fast single-file transpilation
- Avoid deeply nested generics and large unions (>100 members)
- Diagnose: `npx tsc --extendedDiagnostics`
