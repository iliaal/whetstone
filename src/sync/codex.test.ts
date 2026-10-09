import { mkdtemp, readFile, rm, writeFile } from "fs/promises"
import os from "os"
import path from "path"
import { afterEach, expect, test } from "bun:test"
import { syncToCodex } from "./codex"

const tempRoots: string[] = []

afterEach(async () => {
  await Promise.all(tempRoots.splice(0).map((dir) => rm(dir, { recursive: true, force: true })))
})

for (const initial of [undefined, "", 'model = "test-model"\n']) {
  test(`Codex sync is idempotent with ${initial === undefined ? "missing" : initial === "" ? "empty" : "existing"} config`, async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "whetstone-sync-"))
    tempRoots.push(root)
    const configPath = path.join(root, "config.toml")
    if (initial !== undefined) await writeFile(configPath, initial)
    const config = {
      skills: [],
      mcpServers: { demo: { command: "node", args: ["server.js"], env: { MODE: "test" } } },
    }

    await syncToCodex(config, root)
    const first = await readFile(configPath, "utf8")
    await syncToCodex(config, root)
    const second = await readFile(configPath, "utf8")

    expect(second).toBe(first)
    expect(Bun.TOML.parse(second)).toEqual({
      ...(initial ? { model: "test-model" } : {}),
      mcp_servers: { demo: { command: "node", args: ["server.js"], env: { MODE: "test" } } },
    })

    await syncToCodex({ skills: [], mcpServers: { replacement: { command: "python" } } }, root)
    const updated = await readFile(configPath, "utf8")
    expect(Bun.TOML.parse(updated)).toEqual({
      ...(initial ? { model: "test-model" } : {}),
      mcp_servers: { replacement: { command: "python" } },
    })
    await syncToCodex({ skills: [], mcpServers: { replacement: { command: "python" } } }, root)
    expect(await readFile(configPath, "utf8")).toBe(updated)
  })
}
