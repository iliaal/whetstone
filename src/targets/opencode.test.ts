import { chmod, mkdtemp, mkdir, readdir, readFile, rm, stat, symlink, writeFile } from "fs/promises"
import os from "os"
import path from "path"
import { pathToFileURL } from "url"
import { afterEach, expect, test } from "bun:test"
import { loadClaudePlugin } from "../parsers/claude"
import { convertClaudeToOpenCode } from "../converters/claude-to-opencode"
import { copyDir, writeJson, writeText } from "../utils/files"
import type { OpenCodeBundle } from "../types/opencode"
import { writeOpenCodeBundle } from "./opencode"
import { syncToOpenCode } from "../sync/opencode"

const tempRoots: string[] = []
afterEach(async () => {
  await Promise.all(tempRoots.splice(0).map((root) => rm(root, { recursive: true, force: true })))
})

test("installed bundle preserves supported hooks and skills without queuing tasks after source removal", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "whetstone opencode "))
  tempRoots.push(root)
  const source = path.join(root, "source plugin")
  const project = path.join(root, "project")
  await copyDir(path.resolve("plugins/whetstone"), source)
  await mkdir(project)
  const plugin = await loadClaudePlugin(source)
  const command = 'test -f "${CLAUDE_PLUGIN_ROOT}/skills/ia-debugging/SKILL.md" && printf \'{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"Bundled skill is readable"}}\''
  plugin.hooks!.hooks.PostToolUse = [{ hooks: [{ type: "command", command }] }]
  const bundle = convertClaudeToOpenCode(plugin, {
    agentMode: "subagent", inferTemperature: false, permissions: "none",
  })
  await writeOpenCodeBundle(project, bundle)
  await rm(source, { recursive: true })
  const installed = await import(pathToFileURL(path.join(project, ".opencode/plugins/converted-hooks.ts")).href)
  const hooks = await installed.default({ directory: project })
  const args = { prompt: "Debug the failing test and find its root cause", subagent_type: "general", description: "investigate", custom: 42 }
  const taskArgs = { ...args }
  const output = { args: taskArgs }
  await hooks["tool.execute.before"]({ tool: "task", sessionID: "test-session", callID: "call-1" }, output)
  expect(output.args).toBe(taskArgs)
  expect(output.args).toEqual(args)
  expect(bundle.plugins[0].content).not.toContain("inject-skills.sh")
  expect(bundle.plugins[0].content).not.toContain("subagent-start.sh")
  const afterOutput = { title: "Result", output: "Completed", metadata: {} }
  await hooks["tool.execute.after"]({ tool: "task", sessionID: "test-session", callID: "call-1", args }, afterOutput)
  expect(afterOutput.output).toBe("Completed\n\nBundled skill is readable")
  expect(await readFile(path.join(project, ".opencode/skills/ia-debugging/SKILL.md"), "utf8")).toContain("name: ia-debugging")
})

async function tempRoot(): Promise<string> {
  const root = await mkdtemp(path.join(os.tmpdir(), "whetstone-opencode-"))
  tempRoots.push(root)
  return root
}

function bundle(overrides: Partial<OpenCodeBundle> = {}): OpenCodeBundle {
  return {
    config: { $schema: "https://opencode.ai/config.json", mcp: { demo: { type: "local", command: ["node"], environment: { API_TOKEN: "secret" }, enabled: true } } },
    agents: [{ name: "helper", content: "Agent" }],
    commandFiles: [{ name: "run", content: "Command" }],
    plugins: [],
    skillDirs: [],
    ...overrides,
  }
}

for (const [label, setup] of [
  ["agent file", async (project: string, outside: string) => {
    await mkdir(path.join(project, ".opencode", "agents"), { recursive: true })
    await symlink(path.join(outside, "victim.md"), path.join(project, ".opencode", "agents", "helper.md"))
  }],
  ["agents directory", async (project: string, outside: string) => {
    await mkdir(path.join(project, ".opencode"), { recursive: true })
    await symlink(outside, path.join(project, ".opencode", "agents"))
  }],
  ["command file", async (project: string, outside: string) => {
    await mkdir(path.join(project, ".opencode", "commands"), { recursive: true })
    await symlink(path.join(outside, "victim.md"), path.join(project, ".opencode", "commands", "run.md"))
  }],
  [".opencode directory", async (project: string, outside: string) => {
    await symlink(outside, path.join(project, ".opencode"))
  }],
  ["opencode.json", async (project: string, outside: string) => {
    await symlink(path.join(outside, "victim.md"), path.join(project, "opencode.json"))
  }],
] as const) {
  test(`writeOpenCodeBundle refuses a symlinked ${label}`, async () => {
    const root = await tempRoot()
    const project = path.join(root, "project")
    const outside = path.join(root, "outside")
    await mkdir(project)
    await mkdir(outside)
    await writeFile(path.join(outside, "victim.md"), "outside secret\n")
    await setup(project, outside)

    await expect(writeOpenCodeBundle(project, bundle())).rejects.toThrow("Refusing to write through symlink")

    expect(await readFile(path.join(outside, "victim.md"), "utf8")).toBe("outside secret\n")
    expect(await readdir(outside)).toEqual(["victim.md"])
    expect((await readdir(project)).filter((name) => name.includes(".bak."))).toEqual([])
    if (label !== "opencode.json") expect(await readdir(project)).not.toContain("opencode.json")
  })
}

test("writeOpenCodeBundle refuses copying a skill into a symlinked skill directory", async () => {
  const root = await tempRoot()
  const project = path.join(root, "project")
  const outside = path.join(root, "outside")
  const source = path.join(root, "source", "ia-demo")
  await mkdir(path.join(project, ".opencode", "skills"), { recursive: true })
  await mkdir(outside)
  await mkdir(source, { recursive: true })
  await writeFile(path.join(source, "SKILL.md"), "Skill\n")
  await symlink(outside, path.join(project, ".opencode", "skills", "ia-demo"))

  await expect(writeOpenCodeBundle(project, bundle({ skillDirs: [{ name: "ia-demo", sourceDir: source }] })))
    .rejects.toThrow("Refusing to write through symlink")
  expect(await readdir(outside)).toEqual([])
})

test("writeOpenCodeBundle keeps traversal names inside the output root", async () => {
  const root = await tempRoot()
  const project = path.join(root, "project")
  const source = path.join(root, "skill")
  await mkdir(project)
  await mkdir(source)
  await writeFile(path.join(source, "SKILL.md"), "Skill\n")

  for (const overrides of [
    { agents: [{ name: "../../../outside-agent", content: "x" }] },
    { commandFiles: [{ name: "../../outside-command", content: "x" }] },
    { skillDirs: [{ name: "../../outside-skill", sourceDir: source }] },
  ]) {
    await expect(writeOpenCodeBundle(project, bundle(overrides))).rejects.toThrow("Invalid component name")
  }
  expect((await readdir(root)).sort()).toEqual(["project", "skill"])
})

test("writeOpenCodeBundle writes opencode.json as 0600 and tightens an existing config", async () => {
  const root = await tempRoot()
  const project = path.join(root, "project")
  await mkdir(project)
  const configPath = path.join(project, "opencode.json")
  await writeFile(configPath, JSON.stringify({ model: "user-model" }))
  await chmod(configPath, 0o644)

  await writeOpenCodeBundle(project, bundle())

  expect((await stat(configPath)).mode & 0o777).toBe(0o600)
  const written = JSON.parse(await readFile(configPath, "utf8"))
  expect(written.model).toBe("user-model")
  expect(written.mcp.demo.environment).toEqual({ API_TOKEN: "secret" })
  const backups = (await readdir(project)).filter((name) => name.startsWith("opencode.json.bak."))
  expect(backups).toHaveLength(1)
  expect((await stat(path.join(project, backups[0]))).mode & 0o777).toBe(0o600)

  const fresh = path.join(root, "fresh")
  await mkdir(fresh)
  await writeOpenCodeBundle(fresh, bundle())
  expect((await stat(path.join(fresh, "opencode.json"))).mode & 0o777).toBe(0o600)
})

test("OpenCode sync and conversion keep an MCP server named __proto__", async () => {
  const root = await tempRoot()
  const mcpServers = JSON.parse('{"__proto__": {"command": "node"}, "remote": {"url": "https://example.com/mcp"}}')

  await syncToOpenCode({ skills: [], mcpServers }, root)
  const synced = JSON.parse(await readFile(path.join(root, "opencode.json"), "utf8"))
  expect(Object.keys(synced.mcp).sort()).toEqual(["__proto__", "remote"])
  expect(Object.getOwnPropertyDescriptor(synced.mcp, "__proto__")?.value.command).toEqual(["node"])

  const converted = convertClaudeToOpenCode({
    root,
    manifest: { name: "demo", version: "1.0.0" },
    agents: [],
    commands: [],
    skills: [],
    mcpServers,
  }, { agentMode: "subagent", inferTemperature: false, permissions: "none" })
  expect(Object.keys(converted.config.mcp ?? {}).sort()).toEqual(["__proto__", "remote"])
})

for (const command of ["convert", "install"]) {
  for (const secondary of [false, true]) {
    test(`bundled CLI ${command} installs standalone hooks as ${secondary ? "secondary" : "primary"} target`, async () => {
      const root = await mkdtemp(path.join(os.tmpdir(), "whetstone bundled cli "))
      tempRoots.push(root)
      const source = path.join(root, "source plugin")
      const project = path.join(root, "project")
      await writeJson(path.join(source, ".claude-plugin/plugin.json"), {
        name: "demo",
        hooks: { hooks: { PostToolUse: [{ hooks: [{
          type: "command",
          command: `test -f "\${CLAUDE_PLUGIN_ROOT}/marker.txt" && printf '%s' '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"Bundled hook ran"}}'`,
        }] }] } },
      })
      await writeText(path.join(source, "marker.txt"), "Bundled resource")
      const build = await Bun.build({
        entrypoints: [path.resolve("src/index.ts")],
        target: "bun",
        outdir: path.join(root, "standalone"),
      })
      expect(build.success).toBe(true)
      const cli = Bun.spawn([
        process.execPath, build.outputs[0].path, command, source,
        "--to", secondary ? "codex" : "opencode",
        ...(secondary ? ["--also", "opencode"] : []),
        "--output", project, "--codex-home", path.join(root, ".codex"),
        "--permissions", "none",
      ], { cwd: root, stdout: "pipe", stderr: "pipe" })
      const [exitCode, stdout, stderr] = await Promise.all([
        cli.exited, new Response(cli.stdout).text(), new Response(cli.stderr).text(),
      ])
      expect({ exitCode, stderr }).toEqual({ exitCode: 0, stderr: "" })
      expect(stdout).toContain(command === "convert" ? "Converted demo to opencode" : "Installed demo to")
      await rm(source, { recursive: true })
      const output = secondary ? path.join(project, "opencode") : project
      const installed = await import(pathToFileURL(path.join(output, ".opencode/plugins/converted-hooks.ts")).href)
      const hooks = await installed.default({ directory: root })
      const result = { title: "Result", output: "Completed", metadata: {} }
      await hooks["tool.execute.after"]({ tool: "read", sessionID: "test", callID: "call", args: {} }, result)
      expect(result.output).toBe("Completed\n\nBundled hook ran")
    })
  }
}
