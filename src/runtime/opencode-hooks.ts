import { spawn } from "node:child_process"

type CommandHook = { type: "command"; command: string; timeout?: number }
type Matcher = { matcher?: string; hooks: CommandHook[] }
type HookConfig = { hooks: Record<string, Matcher[]> }
type ToolInput = { tool: string; sessionID: string; callID: string; args?: Record<string, unknown> }
type BeforeOutput = { args: Record<string, unknown> }
type AfterOutput = { title: string; output: string; metadata: Record<string, unknown> }

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function execute(command: string, payload: unknown, pluginRoot: string, cwd: string, timeout: number): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn("bash", ["-c", command], {
      cwd, env: { ...process.env, CLAUDE_PLUGIN_ROOT: pluginRoot },
      detached: true, stdio: ["pipe", "pipe", "pipe"],
    })
    let stdout = ""
    let stderr = ""
    let bytes = 0
    function terminate(error: Error) {
      try {
        if (child.pid) process.kill(-child.pid, "SIGKILL")
      } catch (killError) {
        if ((killError as NodeJS.ErrnoException).code !== "ESRCH") {
          reject(killError)
          return
        }
      }
      reject(error)
    }
    const timer = setTimeout(() => terminate(new Error(`Converted Claude hook timed out after ${timeout}ms`)), timeout)
    child.on("error", (error) => {
      clearTimeout(timer)
      reject(error)
    })
    child.on("close", (code, signal) => {
      clearTimeout(timer)
      if (code !== 0) reject(new Error(`Converted Claude hook failed: ${stderr.trim() || signal || `exit ${code}`}`))
      else resolve(stdout)
    })
    child.stdout.setEncoding("utf8")
    child.stderr.setEncoding("utf8")
    for (const [stream, append] of [
      [child.stdout, (data: string) => { stdout += data }],
      [child.stderr, (data: string) => { stderr += data }],
    ] as const) {
      stream.on("data", (data: string) => {
        bytes += Buffer.byteLength(data)
        if (bytes > 1024 * 1024) terminate(new Error("Converted Claude hook exceeded output limit"))
        else append(data)
      })
    }
    // Hooks may exit successfully without consuming stdin; stdout still defines their result.
    child.stdin?.on("error", (error: NodeJS.ErrnoException) => {
      if (error.code !== "EPIPE") reject(error)
    })
    child.stdin?.end(JSON.stringify(payload))
  })
}

export function createHooks(config: HookConfig, pluginRoot: string, directory: string) {
  async function run(event: "PreToolUse" | "PostToolUse", input: ToolInput, output: BeforeOutput | AfterOutput) {
    const toolName = input.tool === "task" ? "Task" : input.tool
    for (const matcher of config.hooks[event] ?? []) {
      if (matcher.matcher && matcher.matcher !== "*" && !new RegExp(matcher.matcher, "i").test(toolName)) continue
      for (const hook of matcher.hooks) {
        const toolInput = "args" in output ? output.args : input.args ?? {}
        const payload = {
          hook_event_name: event, session_id: input.sessionID, tool_use_id: input.callID,
          cwd: directory, tool_name: toolName, tool_input: toolInput,
          ...(event === "PostToolUse" ? { tool_response: output } : {}),
        }
        const stdout = await execute(hook.command, payload, pluginRoot, directory, (hook.timeout ?? 60) * 1000)
        if (!stdout.trim()) continue
        let response: unknown
        try { response = JSON.parse(stdout) } catch { throw new Error("Converted Claude hook returned invalid JSON") }
        if (!isRecord(response)) throw new Error("Converted Claude hook response must be an object")
        if (response.continue === false || response.decision === "block") {
          throw new Error(String(response.stopReason ?? response.reason ?? "Blocked by converted Claude hook"))
        }
        const specific = response.hookSpecificOutput
        if (specific === undefined) continue
        if (!isRecord(specific) || specific.hookEventName !== event) {
          throw new Error("Converted Claude hook returned a mismatched hook event")
        }
        if (specific.permissionDecision === "deny" || specific.permissionDecision === "ask") {
          throw new Error(String(specific.permissionDecisionReason ?? "Converted Claude hook requires approval"))
        }
        // An allow decision never overrides OpenCode's own permission policy.
        if (event === "PreToolUse" && "args" in output && specific.updatedInput !== undefined) {
          if (!isRecord(specific.updatedInput)) throw new Error("Converted Claude hook updatedInput must be an object")
          // OpenCode retains the original argument object when dispatching task tools.
          for (const key of Object.keys(output.args)) delete output.args[key]
          Object.defineProperties(output.args, Object.getOwnPropertyDescriptors(specific.updatedInput))
        }
        if (typeof specific.additionalContext === "string") {
          if ("output" in output) output.output += `\n\n${specific.additionalContext}`
          else if (input.tool === "task" && typeof output.args.prompt === "string") {
            output.args.prompt += `\n\n${specific.additionalContext}`
          } else throw new Error("Cannot attach converted hook context to this OpenCode tool")
        }
      }
    }
  }

  return {
    "tool.execute.before": (input: ToolInput, output: BeforeOutput) => run("PreToolUse", input, output),
    "tool.execute.after": (input: ToolInput, output: AfterOutput) => run("PostToolUse", input, output),
  }
}
