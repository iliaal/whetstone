import { mkdtemp, mkdir, rm, writeFile } from "fs/promises"
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
