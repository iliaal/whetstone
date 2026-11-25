import path from "path"
import { expect, test } from "bun:test"
import pkg from "../package.json"

test("--version reports the package version", async () => {
  const proc = Bun.spawn([process.execPath, "run", path.resolve("src/index.ts"), "--version"], {
    stdout: "pipe",
    stderr: "pipe",
    // consola silences log output when NODE_ENV=test, which bun test sets
    env: { ...process.env, NODE_ENV: "production" },
  })
  const [out, code] = await Promise.all([new Response(proc.stdout).text(), proc.exited])
  expect(code).toBe(0)
  expect(out.trim()).toBe(pkg.version)
})
