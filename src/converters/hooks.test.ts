import { expect, spyOn, test } from "bun:test"
import { convertClaudeToCodex } from "./claude-to-codex"
import { convertClaudeToOpenCode } from "./claude-to-opencode"
import type { ClaudeHooks, ClaudePlugin } from "../types/claude"

const options = {
  agentMode: "subagent" as const,
  inferTemperature: false,
  permissions: "none" as const,
}

function pluginWithHooks(hooks: ClaudeHooks, name = "demo"): ClaudePlugin {
  return {
    root: "/unused", manifest: { name, version: "1.0.0" },
    agents: [], commands: [], skills: [], hooks,
  }
}

test("OpenCode skips SubagentStart visibly while preserving both supported hook events", () => {
  const pre = { hooks: [{ type: "command" as const, command: "echo pre-marker" }] }
  const post = { hooks: [{ type: "command" as const, command: "echo post-marker" }] }
  const hooks = { hooks: {
    PreToolUse: [pre], PostToolUse: [post],
    SubagentStart: [{ hooks: [{ type: "command" as const, command: "echo start-marker" }] }],
  } }
  const warning = spyOn(console, "warn").mockImplementation(() => {})
  try {
    const bundle = convertClaudeToOpenCode(pluginWithHooks(hooks), options)
    expect(bundle.plugins[0].content).toContain(JSON.stringify({ hooks: { PreToolUse: [pre], PostToolUse: [post] } }))
    expect(bundle.plugins[0].content).not.toContain("start-marker")
    expect(warning).toHaveBeenCalledWith(expect.stringContaining("skipping Claude SubagentStart"))
    expect(hooks.hooks.SubagentStart).toHaveLength(1)
  } finally {
    warning.mockRestore()
  }
})

test("OpenCode omits only Whetstone's dependent recorder, retaining other hooks in its matcher", () => {
  const retained = { type: "command" as const, command: "echo retained-marker" }
  const hooks = { hooks: {
    PreToolUse: [{ matcher: "Task|Agent", hooks: [
      { type: "command" as const, command: 'bash "${CLAUDE_PLUGIN_ROOT}/hooks/inject-skills.sh"' },
      retained,
    ] }],
    SubagentStart: [{ hooks: [{ type: "command" as const, command: "echo start-marker" }] }],
  } }
  const warning = spyOn(console, "warn").mockImplementation(() => {})
  try {
    const bundle = convertClaudeToOpenCode(pluginWithHooks(hooks, "whetstone"), options)
    expect(bundle.plugins[0].content).toContain(JSON.stringify({ hooks: { PreToolUse: [{ matcher: "Task|Agent", hooks: [retained] }] } }))
    expect(bundle.plugins[0].content).not.toContain("inject-skills.sh")
    expect(warning).toHaveBeenCalledWith(expect.stringContaining("prompts will not be queued"))
  } finally {
    warning.mockRestore()
  }
})

test("OpenCode continues rejecting other unsupported events and supported-event hook types", () => {
  expect(() => convertClaudeToOpenCode(pluginWithHooks({ hooks: {
    SessionStart: [{ hooks: [{ type: "command", command: "true" }] }],
  } }), options)).toThrow("does not support Claude hook event SessionStart")
  expect(() => convertClaudeToOpenCode(pluginWithHooks({ hooks: {
    PreToolUse: [{ hooks: [{ type: "prompt", prompt: "Evaluate the call" }] }],
  } }), options)).toThrow("does not support prompt hooks")
})

test("OpenCode preserves another plugin's recorder-shaped command", () => {
  const recorder = { type: "command" as const, command: 'bash "${CLAUDE_PLUGIN_ROOT}/hooks/inject-skills.sh"' }
  const warning = spyOn(console, "warn").mockImplementation(() => {})
  try {
    const bundle = convertClaudeToOpenCode(pluginWithHooks({ hooks: {
      PreToolUse: [{ hooks: [recorder] }],
      SubagentStart: [{ hooks: [{ type: "command", command: "true" }] }],
    } }), options)
    expect(bundle.plugins[0].content).toContain(JSON.stringify(recorder))
    expect(warning).toHaveBeenCalledTimes(1)
  } finally {
    warning.mockRestore()
  }
})

test("Codex visibly skips SubagentStart without losing converted skills", () => {
  const plugin = pluginWithHooks({ hooks: { SubagentStart: [{ hooks: [{ type: "command", command: "true" }] }] } })
  plugin.agents.push({ name: "helper", description: "Help", body: "Read the task.", sourcePath: "/unused/helper.md" })
  const warning = spyOn(console, "warn").mockImplementation(() => {})
  try {
    const bundle = convertClaudeToCodex(plugin, options)
    expect(bundle.generatedSkills[0].name).toBe("helper")
    expect(warning).toHaveBeenCalledWith(expect.stringContaining("skipping Claude SubagentStart"))
  } finally {
    warning.mockRestore()
  }
})
