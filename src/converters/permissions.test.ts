import { expect, test } from "bun:test"
import { convertClaudeToOpenCode, type PermissionMode } from "./claude-to-opencode"
import type { ClaudePlugin } from "../types/claude"

const tools = [
  "bash", "read", "write", "edit", "grep", "glob", "list", "webfetch", "skill",
  "patch", "task", "question", "todowrite", "todoread",
]

function permissions(allowedTools: string[], mode: PermissionMode = "from-commands") {
  const plugin: ClaudePlugin = {
    root: "/unused", manifest: { name: "demo", version: "1.0.0" }, agents: [], skills: [],
    commands: [{ name: "example", body: "Example.", sourcePath: "/unused/example.md", allowedTools }],
  }
  return convertClaudeToOpenCode(plugin, {
    agentMode: "subagent", inferTemperature: false, permissions: mode,
  }).config
}

test.each(tools)("patterned %s permissions retain their allowlist and default denial", (tool) => {
  const config = permissions([`${tool.toUpperCase()}(allowed-*)`, `${tool}(second-*)`, `${tool}(allowed-*)`])
  const allowlist = { "*": "deny", "allowed-*": "allow", "second-*": "allow" }
  const permitted = tool === "write" || tool === "edit" ? ["write", "edit"] : [tool]
  expect(config.permission).toEqual(Object.fromEntries(
    tools.map((name) => [name, permitted.includes(name) ? allowlist : "deny"]),
  ))
  expect(config.tools).toEqual(Object.fromEntries(tools.map((name) => [name, name === tool])))
})

test.each(tools)("bare %s permissions retain unpatterned behavior", (tool) => {
  const config = permissions([tool])
  const permitted = tool === "write" || tool === "edit" ? ["write", "edit"] : [tool]
  expect(config.permission).toEqual(Object.fromEntries(
    tools.map((name) => [name, permitted.includes(name) ? "allow" : "deny"]),
  ))
  expect(config.tools).toEqual(Object.fromEntries(tools.map((name) => [name, name === tool])))
})

test("unknown and empty tool specifications do not create permissions", () => {
  const config = permissions(["", "  ", "UnknownTool(allowed-*)", "constructor(*)", "__proto__(*)"])
  expect(config.permission).toEqual(Object.fromEntries(tools.map((name) => [name, "deny"])))
  expect(config.tools).toEqual(Object.fromEntries(tools.map((name) => [name, false])))
})

test("Bash normalization and write/edit pattern union remain intact", () => {
  const config = permissions(["Bash(git:status)", "Bash", "Write(src/*)", "Edit(tests/*)", "Edit(src/*)"])
  expect(config.permission?.bash).toEqual({ "*": "deny", "git status": "allow" })
  const combined = { "*": "deny", "src/*": "allow", "tests/*": "allow" }
  expect(config.permission?.write).toEqual(combined)
  expect(config.permission?.edit).toEqual(combined)
})

test("literal wildcard and prototype-like patterns remain own allowlist entries", () => {
  const config = permissions(["Read(*)", "Read(__proto__)", "Read(constructor)", "Read(toString)"])
  expect(config.permission?.read).toEqual(Object.fromEntries(
    ["*", "__proto__", "constructor", "toString"].map((pattern) => [pattern, "allow"]),
  ))
  expect(Object.getOwnPropertyDescriptor(config.permission!.read, "__proto__")?.value).toBe("allow")
})

test("none and broad modes do not use command allowlists", () => {
  const allowedTools = ["Bash(git:status)", "Write(src/*)"]
  const none = permissions(allowedTools, "none")
  expect(none.permission).toBeUndefined()
  expect(none.tools).toBeUndefined()
  const broad = permissions(allowedTools, "broad")
  expect(broad.permission).toEqual(Object.fromEntries(tools.map((name) => [name, "allow"])))
  expect(broad.tools).toEqual(Object.fromEntries(tools.map((name) => [name, true])))
})
