import { expect, test } from "bun:test"
import { createHooks } from "./opencode-hooks"
import { mkdtemp, readFile, rm } from "node:fs/promises"
import os from "node:os"
import path from "node:path"

const input = { tool: "task", sessionID: "session-1", callID: "call-1" }

test("hook commands receive literal prompt data on stdin and use project cwd", async () => {
  const command = "node -e 'let data=\"\";process.stdin.on(\"data\",x=>data+=x);process.stdin.on(\"end\",()=>{const p=JSON.parse(data);console.log(JSON.stringify({hookSpecificOutput:{hookEventName:p.hook_event_name,updatedInput:{...p.tool_input,session:p.session_id,tool:p.tool_name,cwd:process.cwd()}}}))})'"
  const hooks = createHooks({ hooks: { PreToolUse: [{ matcher: "^Task$", hooks: [{ type: "command", command }] }] } }, process.cwd(), process.cwd())
  const prompt = "literal `not-a-command` ${UNDEFINED} $(not-a-command) 'quoted'\nsecond line"
  const output: { args: Record<string, unknown> } = { args: { prompt, subagent_type: "general" } }
  await hooks["tool.execute.before"](input, output)
  expect(output.args).toEqual({ prompt, subagent_type: "general", session: "session-1", tool: "Task", cwd: process.cwd() })
})

test("nonmatching hook does not run its command", async () => {
  const hooks = createHooks({ hooks: { PreToolUse: [{ matcher: "^Read$", hooks: [{ type: "command", command: "exit 2" }] }] } }, process.cwd(), process.cwd())
  const output = { args: { prompt: "unchanged" } }
  await hooks["tool.execute.before"](input, output)
  expect(output.args.prompt).toBe("unchanged")
  await expect(hooks["tool.execute.before"]({ ...input, tool: "read" }, output)).rejects.toThrow("Converted Claude hook failed")
})

test("deny response blocks execution without applying updated arguments", async () => {
  const response = JSON.stringify({ hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: "fixture denied", updatedInput: { prompt: "changed" } } })
  const hooks = createHooks({ hooks: { PreToolUse: [{ hooks: [{ type: "command", command: `printf '%s' '${response}'` }] }] } }, process.cwd(), process.cwd())
  const output = { args: { prompt: "unchanged" } }
  await expect(hooks["tool.execute.before"](input, output)).rejects.toThrow("fixture denied")
  expect(output.args.prompt).toBe("unchanged")
})

test("invalid response is reported instead of silently treated as successful injection", async () => {
  const hooks = createHooks({ hooks: { PreToolUse: [{ hooks: [{ type: "command", command: "printf invalid" }] }] } }, process.cwd(), process.cwd())
  await expect(hooks["tool.execute.before"](input, { args: {} })).rejects.toThrow("invalid JSON")
})

test("hook timeout bounds a command that never returns", async () => {
  const hooks = createHooks({ hooks: { PreToolUse: [{ hooks: [{ type: "command", command: "exec sleep 5", timeout: 0.05 }] }] } }, process.cwd(), process.cwd())
  await expect(hooks["tool.execute.before"](input, { args: {} })).rejects.toThrow("timed out")
}, 1000)

test("updated input reaches the argument object retained by OpenCode", async () => {
  const response = JSON.stringify({ hookSpecificOutput: { hookEventName: "PreToolUse", updatedInput: { prompt: "injected", description: "new task" } } })
  const hooks = createHooks({ hooks: { PreToolUse: [{ hooks: [{ type: "command", command: `printf '%s' '${response}'` }] }] } }, process.cwd(), process.cwd())
  const args: Record<string, unknown> = { prompt: "original", removed: true }
  const output = { args }
  await hooks["tool.execute.before"](input, output)
  expect(output.args).toBe(args)
  expect(args).toEqual({ prompt: "injected", description: "new task" })
})

test("hook timeout terminates descendants before delayed side effects", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "whetstone-timeout-"))
  try {
    const hooks = createHooks({ hooks: { PreToolUse: [{ hooks: [{ type: "command", command: "(sleep 0.3; echo changed > marker) & wait", timeout: 0.05 }] }] } }, root, root)
    await expect(hooks["tool.execute.before"](input, { args: {} })).rejects.toThrow("timed out")
    await Bun.sleep(500)
    await expect(readFile(path.join(root, "marker"))).rejects.toMatchObject({ code: "ENOENT" })
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test("post-tool context is appended to the actual tool output", async () => {
  const response = JSON.stringify({ hookSpecificOutput: { hookEventName: "PostToolUse", additionalContext: "Follow-up context" } })
  const hooks = createHooks({ hooks: { PostToolUse: [{ hooks: [{ type: "command", command: `printf '%s' '${response}'` }] }] } }, process.cwd(), process.cwd())
  const output = { title: "Result", output: "Tool output", metadata: {} }
  await hooks["tool.execute.after"]({ ...input, args: {} }, output)
  expect(output.output).toBe("Tool output\n\nFollow-up context")
})
