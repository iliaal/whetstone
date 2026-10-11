import { chmod, mkdtemp, readdir, readFile, rm, stat, symlink, writeFile } from "fs/promises"
import os from "os"
import path from "path"
import { afterEach, expect, spyOn, test } from "bun:test"
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

async function tempRoot(): Promise<string> {
  const root = await mkdtemp(path.join(os.tmpdir(), "whetstone-sync-"))
  tempRoots.push(root)
  return root
}

const userSettings = [
  'approval_policy = "untrusted"',
  'sandbox_mode = "read-only"',
  "",
  '[projects."/work/demo"]',
  'trust_level = "untrusted"',
  "",
].join("\n")

test("Codex sync preserves user settings and the tail after a legacy marker, with a backup", async () => {
  const root = await tempRoot()
  const configPath = path.join(root, "config.toml")
  const legacy = [
    'approval_policy = "untrusted"',
    'sandbox_mode = "read-only"',
    "",
    "# MCP servers synced from Claude Code",
    "[mcp_servers.old]",
    'command = "old-server"',
    "",
    "[mcp_servers.old.env]",
    'TOKEN = "stale"',
    "",
    '[projects."/work/demo"]',
    'trust_level = "untrusted"',
    "",
  ].join("\n")
  await writeFile(configPath, legacy, { mode: 0o644 })
  await chmod(configPath, 0o644)

  await syncToCodex({ skills: [], mcpServers: { current: { command: "node" } } }, root)

  const updated = await readFile(configPath, "utf8")
  expect(Bun.TOML.parse(updated)).toEqual({
    approval_policy: "untrusted",
    sandbox_mode: "read-only",
    projects: { "/work/demo": { trust_level: "untrusted" } },
    mcp_servers: { old: { command: "old-server", env: { TOKEN: "stale" } }, current: { command: "node" } },
  })
  expect(updated).not.toContain("# MCP servers synced from Claude Code")
  expect((await stat(configPath)).mode & 0o777).toBe(0o600)
  const backups = (await readdir(root)).filter((name) => name.startsWith("config.toml.bak."))
  expect(backups).toHaveLength(1)
  expect(await readFile(path.join(root, backups[0]), "utf8")).toBe(legacy)
  expect((await stat(path.join(root, backups[0]))).mode & 0o777).toBe(0o600)
})

test("Codex sync keeps content after its managed block and removes the block when servers are gone", async () => {
  const root = await tempRoot()
  const configPath = path.join(root, "config.toml")
  await writeFile(configPath, userSettings)
  await syncToCodex({ skills: [], mcpServers: { demo: { command: "node" } } }, root)
  await writeFile(configPath, (await readFile(configPath, "utf8")) + '\n[profiles.fast]\nmodel = "fast-model"\n')

  await syncToCodex({ skills: [], mcpServers: { demo: { command: "python" } } }, root)
  expect(Bun.TOML.parse(await readFile(configPath, "utf8"))).toEqual({
    approval_policy: "untrusted",
    sandbox_mode: "read-only",
    projects: { "/work/demo": { trust_level: "untrusted" } },
    profiles: { fast: { model: "fast-model" } },
    mcp_servers: { demo: { command: "python" } },
  })

  await syncToCodex({ skills: [], mcpServers: {} }, root)
  const emptied = await readFile(configPath, "utf8")
  expect(emptied).not.toContain("WHETSTONE MANAGED")
  expect(Bun.TOML.parse(emptied)).toEqual({
    approval_policy: "untrusted",
    sandbox_mode: "read-only",
    projects: { "/work/demo": { trust_level: "untrusted" } },
    profiles: { fast: { model: "fast-model" } },
  })
})

test("Codex sync refuses to move keys that TOML assigns to the managed table", async () => {
  const root = await tempRoot()
  const configPath = path.join(root, "config.toml")
  const original = [
    'approval_policy = "untrusted"',
    "",
    "# MCP servers synced from Claude Code",
    "[mcp_servers.current]",
    'command = "/usr/bin/true"',
    "",
    'sandbox_mode = "danger-full-access"',
    "",
  ].join("\n")
  await writeFile(configPath, original)

  await expect(syncToCodex({ skills: [], mcpServers: { current: { command: "node" } } }, root))
    .rejects.toThrow("directly after the whetstone-managed MCP section")
  expect(await readFile(configPath, "utf8")).toBe(original)
  expect((await readdir(root)).filter((name) => name.startsWith("config.toml.bak."))).toEqual([])
})

test("Codex sync quotes server names and env keys instead of emitting TOML structure", async () => {
  const root = await tempRoot()
  const configPath = path.join(root, "config.toml")
  const injectedKey = 'SAFE = "x"\n\n[projects."/workspace/demo"]\ntrust_level'
  const injectedName = 'evil]\n[projects."/workspace/demo"]\ntrust_level = "trusted"\n[x'
  const env = { [injectedKey]: "trusted", "\u007fDEL": "a\u007fb" }

  await syncToCodex({
    skills: [],
    mcpServers: { [injectedName]: { command: "/usr/bin/true", env } },
  }, root)

  const parsed = Bun.TOML.parse(await readFile(configPath, "utf8")) as Record<string, unknown>
  expect(Object.keys(parsed)).toEqual(["mcp_servers"])
  expect(parsed.mcp_servers).toEqual({ [injectedName]: { command: "/usr/bin/true", env } })
})

test("Codex sync rejects non-string MCP values without touching the config", async () => {
  const root = await tempRoot()
  const configPath = path.join(root, "config.toml")
  await writeFile(configPath, userSettings)
  const bad = { command: "node", env: { PORT: 3000 } } as unknown as { command: string }

  await expect(syncToCodex({ skills: [], mcpServers: { bad } }, root)).rejects.toThrow("expected a string")
  expect(await readFile(configPath, "utf8")).toBe(userSettings)
})

test("Codex sync refuses a symlinked config.toml", async () => {
  const root = await tempRoot()
  const outside = await tempRoot()
  const target = path.join(outside, "real.toml")
  await writeFile(target, userSettings)
  await symlink(target, path.join(root, "config.toml"))

  await expect(syncToCodex({ skills: [], mcpServers: { demo: { command: "node" } } }, root))
    .rejects.toThrow("symlink")
  expect(await readFile(target, "utf8")).toBe(userSettings)
  expect(await readdir(outside)).toEqual(["real.toml"])
})

test("Codex sync repairs duplicate tables left by the original unmarked sync format", async () => {
  const root = await tempRoot()
  const configPath = path.join(root, "config.toml")
  await writeFile(configPath, [
    'model = "user-model"',
    "# Codex config - synced from Claude Code",
    "",
    "[mcp_servers.demo]",
    'command = "first"',
    "",
    "# MCP servers synced from Claude Code",
    "[mcp_servers.demo]",
    'command = "second"',
    "",
  ].join("\n"))

  await syncToCodex({ skills: [], mcpServers: { demo: { command: "node" } } }, root)

  const updated = await readFile(configPath, "utf8")
  expect(Bun.TOML.parse(updated)).toEqual({ model: "user-model", mcp_servers: { demo: { command: "node" } } })
  expect(updated.startsWith('model = "user-model"\n')).toBe(true)
})

test("Codex sync keeps a user table appended after a legacy marker and warns about it", async () => {
  const root = await tempRoot()
  const configPath = path.join(root, "config.toml")
  await writeFile(configPath, [
    'model = "user-model"',
    "",
    "# MCP servers synced from Claude Code",
    "[mcp_servers.old]",
    'command = "old-server"',
    "",
    "[mcp_servers.user]",
    'command = "/opt/user-server"',
    "",
    "[mcp_servers.user.env]",
    'USER_TOKEN = "mine"',
    "",
  ].join("\n"))
  const warn = spyOn(console, "warn").mockImplementation(() => {})
  try {
    await syncToCodex({ skills: [], mcpServers: { current: { command: "node" } } }, root)
    const warnings = warn.mock.calls.map((call) => String(call[0]))
    expect(warnings.some((message) => message.includes("[mcp_servers.user]"))).toBe(true)
  } finally {
    warn.mockRestore()
  }

  expect(Bun.TOML.parse(await readFile(configPath, "utf8"))).toEqual({
    model: "user-model",
    mcp_servers: {
      old: { command: "old-server" },
      user: { command: "/opt/user-server", env: { USER_TOKEN: "mine" } },
      current: { command: "node" },
    },
  })
})

test("Codex sync tightens an unchanged config to 0600", async () => {
  const root = await tempRoot()
  const configPath = path.join(root, "config.toml")
  const config = { skills: [], mcpServers: { demo: { command: "node", env: { API_TOKEN: "secret" } } } }
  await syncToCodex(config, root)
  const written = await readFile(configPath, "utf8")
  await chmod(configPath, 0o644)

  await syncToCodex(config, root)

  expect(await readFile(configPath, "utf8")).toBe(written)
  expect((await stat(configPath)).mode & 0o777).toBe(0o600)
  expect((await readdir(root)).filter((name) => name.startsWith("config.toml.bak."))).toEqual([])
})

test("Codex sync keeps an MCP server named __proto__", async () => {
  const root = await tempRoot()
  const configPath = path.join(root, "config.toml")
  const mcpServers = JSON.parse('{"__proto__": {"command": "node", "env": {"__proto__": "x"}}, "ok": {"command": "python"}}')

  await syncToCodex({ skills: [], mcpServers }, root)

  const parsed = Bun.TOML.parse(await readFile(configPath, "utf8")) as { mcp_servers: Record<string, unknown> }
  expect(Object.keys(parsed.mcp_servers).sort()).toEqual(["__proto__", "ok"])
  expect(Object.hasOwn(parsed.mcp_servers, "__proto__")).toBe(true)
  const proto = Object.getOwnPropertyDescriptor(parsed.mcp_servers, "__proto__")!.value as Record<string, unknown>
  expect(proto.command).toBe("node")
  expect(Object.getOwnPropertyDescriptor(proto.env, "__proto__")?.value).toBe("x")
})
