import { mkdtemp, mkdir, rm, symlink, writeFile } from "fs/promises"
import os from "os"
import path from "path"
import { afterEach, expect, test } from "bun:test"
import { loadClaudePlugin } from "./claude"
import { convertClaudeToOpenCode } from "../converters/claude-to-opencode"
import { renderCodexConfig } from "../targets/codex"

const tempRoots: string[] = []

afterEach(async () => {
  await Promise.all(tempRoots.splice(0).map((dir) => rm(dir, { recursive: true, force: true })))
})

test("loadClaudePlugin ignores command support markdown", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "whetstone-parser-"))
  tempRoots.push(root)

  await mkdir(path.join(root, ".claude-plugin"), { recursive: true })
  await mkdir(path.join(root, "commands", "references"), { recursive: true })
  await mkdir(path.join(root, "agents"), { recursive: true })
  await mkdir(path.join(root, "skills", "ia-demo"), { recursive: true })

  await writeFile(
    path.join(root, ".claude-plugin", "plugin.json"),
    JSON.stringify({ name: "demo", version: "1.0.0" }),
  )
  await writeFile(
    path.join(root, "commands", "ia-demo.md"),
    "---\nname: ia-demo\ndescription: Demo command\n---\n\nRun the demo.\n",
  )
  await writeFile(
    path.join(root, "commands", "references", "template.md"),
    "# Template\n\nThis support document is not invocable.\n",
  )
  await writeFile(
    path.join(root, "agents", "ia-helper.md"),
    "---\nname: ia-helper\ndescription: Helper agent\n---\n\nHelp.\n",
  )
  await writeFile(
    path.join(root, "skills", "ia-demo", "SKILL.md"),
    "---\nname: ia-demo\ndescription: Use when testing parser behavior.\n---\n\n# Demo\n",
  )

  const plugin = await loadClaudePlugin(root)

  expect(plugin.commands.map((command) => command.name)).toEqual(["ia-demo"])
})

test("loadClaudePlugin loads overlapping component paths only once", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "whetstone-parser-"))
  tempRoots.push(root)
  await mkdir(path.join(root, ".claude-plugin"), { recursive: true })
  await writeFile(path.join(root, ".claude-plugin", "plugin.json"), JSON.stringify({
    name: "demo",
    agents: ["./agents", "agents/nested", "extra-agents", "./extra-agents"],
    commands: ["./commands", "commands/nested", "extra-commands"],
    skills: ["./skills", "skills/ia-demo", "extra-skills"],
  }))
  const files = [
    "agents/nested/ia-demo.md", "extra-agents/ia-demo.md",
    "commands/nested/ia-demo.md", "extra-commands/ia-demo.md",
    "skills/ia-demo/SKILL.md", "extra-skills/ia-demo/SKILL.md",
  ]
  for (const file of files) {
    await mkdir(path.dirname(path.join(root, file)), { recursive: true })
    await writeFile(path.join(root, file), "---\nname: ia-demo\n---\nInstructions.\n")
  }

  const plugin = await loadClaudePlugin(root)

  // Distinct files with the same declared name must remain available to converters.
  expect(plugin.agents.map((agent) => path.relative(root, agent.sourcePath))).toEqual(files.slice(0, 2))
  expect(plugin.commands.map((command) => path.relative(root, command.sourcePath))).toEqual(files.slice(2, 4))
  expect(plugin.skills.map((skill) => path.relative(root, skill.skillPath))).toEqual(files.slice(4, 6))
})

for (const hooks of ["./hooks/hooks.json", ["./hooks/hooks.json", "hooks/../hooks/hooks.json", "extra.json", "./extra.json"]]) {
  test(`loadClaudePlugin loads each resolved hook config once: ${JSON.stringify(hooks)}`, async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "whetstone-parser-"))
    tempRoots.push(root)
    await mkdir(path.join(root, ".claude-plugin"), { recursive: true })
    await mkdir(path.join(root, "hooks"), { recursive: true })
    await writeFile(path.join(root, ".claude-plugin", "plugin.json"), JSON.stringify({ name: "demo", hooks }))
    const matcher = { matcher: "Bash", hooks: [{ type: "command", command: "echo default" }] }
    const extraMatcher = { matcher: "Write", hooks: [{ type: "command", command: "echo extra" }] }
    await writeFile(path.join(root, "hooks", "hooks.json"), JSON.stringify({ hooks: { PreToolUse: [matcher] } }))
    // Identical entries from distinct files are intentional and must remain in order.
    await writeFile(path.join(root, "extra.json"), JSON.stringify({ hooks: { PreToolUse: [matcher, extraMatcher] } }))

    const plugin = await loadClaudePlugin(root)

    expect(plugin.hooks?.hooks.PreToolUse).toEqual(Array.isArray(hooks) ? [matcher, matcher, extraMatcher] : [matcher])
  })
}

test("loadClaudePlugin preserves inline hooks after the default config", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "whetstone-parser-"))
  tempRoots.push(root)
  await mkdir(path.join(root, ".claude-plugin"), { recursive: true })
  await mkdir(path.join(root, "hooks"), { recursive: true })
  const matcher = { matcher: "Bash", hooks: [{ type: "command", command: "echo hook" }] }
  const hooks = { hooks: { PreToolUse: [matcher] } }
  await writeFile(path.join(root, ".claude-plugin", "plugin.json"), JSON.stringify({ name: "demo", hooks }))
  await writeFile(path.join(root, "hooks", "hooks.json"), JSON.stringify(hooks))

  const plugin = await loadClaudePlugin(root)

  expect(plugin.hooks?.hooks.PreToolUse).toEqual([matcher, matcher])
})

for (const source of ["default", "path", "paths", "inline"] as const) {
  for (const wrapped of [false, true]) {
    if (source === "inline" && wrapped) continue
    test(`loadClaudePlugin loads ${wrapped ? "wrapped" : "bare"} MCP config from ${source}`, async () => {
      const root = await mkdtemp(path.join(os.tmpdir(), "whetstone-parser-"))
      tempRoots.push(root)
      await mkdir(path.join(root, ".claude-plugin"), { recursive: true })
      const servers = {
        remote: { type: "http", url: "https://example.com/mcp", headers: { "X-Test": "demo" } },
        local: { command: "node", args: ["server.js"], env: { MODE: "test" } },
      }
      const config = wrapped ? { mcpServers: servers } : servers
      const mcpServers = source === "inline" ? servers
        : source === "path" ? "custom.json"
        : source === "paths" ? ["custom.json", "override.json"] : undefined
      await writeFile(path.join(root, ".claude-plugin", "plugin.json"), JSON.stringify({ name: "demo", mcpServers }))
      await writeFile(path.join(root, source === "default" ? ".mcp.json" : "custom.json"), JSON.stringify(config))
      const override = { remote: { url: "https://example.com/override" } }
      await writeFile(path.join(root, "override.json"), JSON.stringify(override))

      const plugin = await loadClaudePlugin(root)

      const expected = source === "paths" ? { ...servers, ...override } : servers
      expect(plugin.mcpServers).toEqual(expected)
      const bundle = convertClaudeToOpenCode(plugin, {
        agentMode: "subagent", inferTemperature: false, permissions: "none",
      })
      expect(bundle.config.mcp?.remote?.url).toBe(expected.remote.url)
      expect(bundle.config.mcp?.local?.command).toEqual(["node", "server.js"])
      const toml = renderCodexConfig(plugin.mcpServers)
      expect(toml).toContain("[mcp_servers.remote]")
      expect(toml).toContain(`url = "${expected.remote.url}"`)
      expect(toml).toContain('[mcp_servers.local]')
      expect(toml).not.toContain('[mcp_servers.mcpServers]')
    })
  }
}

test("loadClaudePlugin preserves a bare MCP server named mcpServers", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "whetstone-parser-"))
  tempRoots.push(root)
  await mkdir(path.join(root, ".claude-plugin"), { recursive: true })
  await writeFile(path.join(root, ".claude-plugin", "plugin.json"), JSON.stringify({ name: "demo" }))
  const servers = { mcpServers: { command: "node", args: ["server.js"] } }
  await writeFile(path.join(root, ".mcp.json"), JSON.stringify(servers))

  expect((await loadClaudePlugin(root)).mcpServers).toEqual(servers)
})

for (const component of ["agents", "commands"] as const) {
  for (const form of ["file", "mixed"] as const) {
    test(`loadClaudePlugin accepts ${form} ${component} paths`, async () => {
      const root = await mkdtemp(path.join(os.tmpdir(), "whetstone-parser-"))
      tempRoots.push(root)
      await mkdir(path.join(root, ".claude-plugin"), { recursive: true })
      const customFile = `custom-${component}/ia-custom.md`
      const paths = form === "file" ? `./${customFile}` : [
        `./${customFile}`, customFile, `custom-${component}`,
        `missing-${component}.md`, `custom-${component}/notes.txt`,
        `custom-${component}/references/template.md`,
      ]
      await writeFile(path.join(root, ".claude-plugin", "plugin.json"), JSON.stringify({
        name: "demo", [component]: paths,
      }))
      for (const file of [`${component}/ia-default.md`, customFile]) {
        await mkdir(path.dirname(path.join(root, file)), { recursive: true })
        await writeFile(path.join(root, file), `---\ndescription: Custom component\n---\nInstructions for ${file}.\n`)
      }
      await writeFile(path.join(root, `custom-${component}/notes.txt`), "Not a component.\n")
      // Command support documents remain excluded even when their parent is also listed.
      await mkdir(path.join(root, `custom-${component}/references`))
      await writeFile(path.join(root, `custom-${component}/references/template.md`), "Support only.\n")

      const plugin = await loadClaudePlugin(root)
      const loaded = plugin[component]
      const expected = [`${component}/ia-default.md`, customFile]
      if (component === "agents" && form === "mixed") {
        expected.push(`custom-${component}/references/template.md`)
      }
      expect(loaded.map((item) => path.relative(root, item.sourcePath))).toEqual(expected)
      expect(loaded[1].name).toBe("ia-custom")
      expect(loaded[1].description).toBe("Custom component")
      expect(loaded[1].body).toBe(`Instructions for ${customFile}.`)
    })
  }
}

async function pluginRoot(manifest: Record<string, unknown> = {}): Promise<string> {
  const root = await mkdtemp(path.join(os.tmpdir(), "whetstone-parser-"))
  tempRoots.push(root)
  await mkdir(path.join(root, ".claude-plugin"), { recursive: true })
  await writeFile(path.join(root, ".claude-plugin", "plugin.json"), JSON.stringify({ name: "demo", ...manifest }))
  return root
}

for (const [component, file] of [
  ["agent", "agents/ia-demo.md"],
  ["command", "commands/ia-demo.md"],
  ["skill", "skills/ia-demo/SKILL.md"],
] as const) {
  for (const name of ['"../../../outside"', '"..\\\\outside"', '"a/b"', '".."', "[a, b]", "42", '"bad\\nname"']) {
    test(`loadClaudePlugin rejects ${component} name ${name}`, async () => {
      const root = await pluginRoot()
      await mkdir(path.dirname(path.join(root, file)), { recursive: true })
      await writeFile(path.join(root, file), `---\nname: ${name}\ndescription: Demo\n---\nBody.\n`)

      await expect(loadClaudePlugin(root)).rejects.toThrow(`Invalid ${component} name`)
    })
  }
}

test("loadClaudePlugin rejects a plugin name that is not a safe path segment", async () => {
  const root = await pluginRoot({ name: "../escape" })
  await expect(loadClaudePlugin(root)).rejects.toThrow("Invalid plugin name")
})

for (const [label, setup] of [
  ["default agents directory", async (root: string, outside: string) => {
    await symlink(outside, path.join(root, "agents"))
  }],
  ["manifest agents path", async (root: string, outside: string) => {
    await writeFile(path.join(root, ".claude-plugin", "plugin.json"), JSON.stringify({ name: "demo", agents: "borrowed" }))
    await symlink(outside, path.join(root, "borrowed"))
  }],
  ["default skills directory", async (root: string, outside: string) => {
    await symlink(outside, path.join(root, "skills"))
  }],
  ["default .mcp.json", async (root: string, outside: string) => {
    await symlink(path.join(outside, "servers.json"), path.join(root, ".mcp.json"))
  }],
  ["manifest mcpServers path", async (root: string, outside: string) => {
    await writeFile(path.join(root, ".claude-plugin", "plugin.json"), JSON.stringify({ name: "demo", mcpServers: "mcp.json" }))
    await symlink(path.join(outside, "servers.json"), path.join(root, "mcp.json"))
  }],
  ["default hooks directory", async (root: string, outside: string) => {
    await symlink(outside, path.join(root, "hooks"))
  }],
] as const) {
  test(`loadClaudePlugin refuses a symlinked ${label} that leaves the plugin root`, async () => {
    const root = await pluginRoot()
    const outside = await mkdtemp(path.join(os.tmpdir(), "whetstone-outside-"))
    tempRoots.push(outside)
    await writeFile(path.join(outside, "borrowed.md"), "---\nname: borrowed\n---\nOutside instructions.\n")
    await mkdir(path.join(outside, "ia-borrowed"))
    await writeFile(path.join(outside, "ia-borrowed", "SKILL.md"), "---\nname: ia-borrowed\n---\nOutside skill.\n")
    await writeFile(path.join(outside, "servers.json"), JSON.stringify({ outside: { command: "outside" } }))
    await writeFile(path.join(outside, "hooks.json"), JSON.stringify({ hooks: {} }))
    await setup(root, outside)

    await expect(loadClaudePlugin(root)).rejects.toThrow("resolves outside the plugin root")
  })
}

test("loadClaudePlugin accepts component symlinks that stay inside the plugin root", async () => {
  const root = await pluginRoot({ agents: "linked-agents" })
  await mkdir(path.join(root, "shared"))
  await writeFile(path.join(root, "shared", "ia-shared.md"), "---\nname: ia-shared\n---\nShared.\n")
  await symlink(path.join(root, "shared"), path.join(root, "linked-agents"))

  const plugin = await loadClaudePlugin(root)

  expect(plugin.agents.map((agent) => agent.name)).toEqual(["ia-shared"])
})

test("loadClaudePlugin keeps a hook event named __proto__ as data", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "whetstone-parser-"))
  tempRoots.push(root)
  await mkdir(path.join(root, ".claude-plugin"), { recursive: true })
  await mkdir(path.join(root, "hooks"), { recursive: true })
  await writeFile(path.join(root, ".claude-plugin", "plugin.json"), JSON.stringify({ name: "demo" }))
  await writeFile(
    path.join(root, "hooks", "hooks.json"),
    '{"hooks": {"__proto__": [{"hooks": [{"type": "command", "command": "echo x"}]}]}}',
  )

  const plugin = await loadClaudePlugin(root)

  expect(Object.keys(plugin.hooks!.hooks)).toEqual(["__proto__"])
  expect(Object.getPrototypeOf(plugin.hooks!.hooks)).toBe(Object.prototype)
})
