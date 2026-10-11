import { mkdtemp, mkdir, readFile, rm } from "fs/promises"
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
