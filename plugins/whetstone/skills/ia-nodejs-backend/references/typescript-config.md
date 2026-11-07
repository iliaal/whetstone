# TypeScript Configuration & Patterns

> When to read: when setting up tsconfig, picking strictness flags, or choosing between branded types / discriminated unions / utility types for a backend service.

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

ESM-first: set `"type": "module"` in package.json. Detect the entry module with `import.meta.main` (Node v24.2.0+ or v22.18.0+). Never compare `import.meta.url` with `pathToFileURL(process.argv[1])`: Node resolves the main module's symlinks but leaves `argv[1]` as invoked, so through an npm `.bin` shim or any symlinked install the check is false and the CLI exits 0 having done nothing. On older Node, compare `realpathSync(fileURLToPath(import.meta.url))` with `realpathSync(process.argv[1])`, and run the installed bin once before release.

Dev: `tsx watch src/server.ts` | Build: `tsc` | Node 22.18+/23.6+: type stripping on by default; Node 22.6-22.17/23.0-23.5: `--experimental-strip-types` for scripts

NestJS and other decorator-DI frameworks read constructor types from `emitDecoratorMetadata`, which tsx and esbuild never emit: through NestJS v12.4.0 every dependency without `@Inject()` is silently `undefined`, and later versions only log a warning. For such apps, run and test with `tsc` or SWC with `emitDecoratorMetadata` enabled, or name every constructor dependency with `@Inject()`, and verify with a startup test that calls one injected service.

Type stripping only erases syntax, so a TypeScript construct with runtime semantics fails at Node startup instead of at build time: enum declarations, namespaces/modules carrying runtime code, constructor parameter properties, and non-ECMAScript `import =` / `export =` assignments are the confirmed offenders. Enable `erasableSyntaxOnly` in tsconfig to catch them at `tsc` type-check time instead of at `node` runtime.

Type-safe env at startup, with a Zod schema as source of truth:
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

**Branded types**: prevent mixing domain primitives:
```typescript
type Brand<K, T> = K & { __brand: T };
type UserId = Brand<string, 'UserId'>;
type OrderId = Brand<string, 'OrderId'>;
// Compiler prevents passing OrderId where UserId expected
```

**Discriminated unions**: make illegal states unrepresentable:
```typescript
type Result<T> = { ok: true; data: T } | { ok: false; error: string };
```

**Exhaustive switch**: catch missing cases at compile time:
```typescript
default: { const _: never = status; throw new Error(`Unhandled: ${_}`); }
```

**Type guards** for runtime narrowing:
```typescript
function isAppError(err: unknown): err is AppError { return err instanceof AppError; }
```

**`satisfies`**: validate constraints, preserve literal types:
```typescript
const config = { port: 3000, host: 'localhost' } satisfies Record<string, string | number>;
```

**`as const`**: literal unions from arrays:
```typescript
const ROLES = ['admin', 'user', 'guest'] as const;
type Role = typeof ROLES[number]; // 'admin' | 'user' | 'guest'
```

## Compiler Performance

- `incremental: true`: 50-90% faster rebuilds
- `skipLibCheck: true`: skip .d.ts checking
- `isolatedModules: true`: enables fast single-file transpilation
- Avoid deeply nested generics and large unions (>100 members)
- Diagnose: `npx tsc --extendedDiagnostics`
