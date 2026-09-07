import { mkdtemp, mkdir, readFile, rm, writeFile } from "fs/promises"
import os from "os"
import path from "path"
import { pathToFileURL } from "url"
import { afterEach, expect, test } from "bun:test"
import { loadClaudePlugin } from "../parsers/claude"
import { convertClaudeToOpenCode } from "../converters/claude-to-opencode"
import { copyDir } from "../utils/files"
import { writeOpenCodeBundle } from "./opencode"

const tempRoots: string[] = []
afterEach(async () => {
  await Promise.all(tempRoots.splice(0).map((root) => rm(root, { recursive: true, force: true })))
})

test("installed hook injects readable skill paths after the source checkout disappears", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "whetstone opencode "))
  tempRoots.push(root)
  const source = path.join(root, "source plugin")
  const project = path.join(root, "project")
  await copyDir(path.resolve("plugins/whetstone"), source)
  await mkdir(project)
  const plugin = await loadClaudePlugin(source)
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
  expect(output.args.prompt).toContain("BEFORE STARTING:")
  expect(output.args).toBe(taskArgs)
  expect(taskArgs.prompt).toContain("BEFORE STARTING:")
  expect(output.args.prompt).toEndWith(args.prompt)
  expect({ ...output.args, prompt: args.prompt }).toEqual(args)
  const skillPaths = [...output.args.prompt.matchAll(/^- (.+\/SKILL\.md)$/gm)].map((match) => match[1])
  expect(skillPaths.length).toBeGreaterThan(0)
  for (const skillPath of skillPaths) {
    expect(skillPath.startsWith(project)).toBe(true)
    expect(await readFile(skillPath, "utf8")).toContain("name:")
  }
})
