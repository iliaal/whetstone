import { formatFrontmatter } from "../utils/frontmatter"
import type {
  ClaudeAgent,
  ClaudeCommand,
  ClaudeHooks,
  ClaudePlugin,
  ClaudeMcpServer,
} from "../types/claude"
import type {
  OpenCodeBundle,
  OpenCodeCommandFile,
  OpenCodeConfig,
  OpenCodeMcpServer,
} from "../types/opencode"

export type PermissionMode = "none" | "broad" | "from-commands"

export type ClaudeToOpenCodeOptions = {
  agentMode: "primary" | "subagent"
  inferTemperature: boolean
  permissions: PermissionMode
}

const TOOL_MAP: Record<string, string> = {
  bash: "bash",
  read: "read",
  write: "write",
  edit: "edit",
  grep: "grep",
  glob: "glob",
  list: "list",
  webfetch: "webfetch",
  skill: "skill",
  patch: "patch",
  task: "task",
  question: "question",
  todowrite: "todowrite",
  todoread: "todoread",
}


export function convertClaudeToOpenCode(
  plugin: ClaudePlugin,
  options: ClaudeToOpenCodeOptions,
): OpenCodeBundle {
  const agentFiles = plugin.agents.map((agent) => convertAgent(agent, options))
  const cmdFiles = convertCommands(plugin.commands)
  const mcp = plugin.mcpServers ? convertMcp(plugin.mcpServers) : undefined
  const plugins = plugin.hooks ? [convertHooks(plugin.hooks, plugin.manifest.name)] : []

  const config: OpenCodeConfig = {
    $schema: "https://opencode.ai/config.json",
    mcp: mcp && Object.keys(mcp).length > 0 ? mcp : undefined,
  }

  applyPermissions(config, plugin.commands, options.permissions)

  return {
    hookSource: plugin.hooks ? { name: plugin.manifest.name, root: plugin.root } : undefined,
    config,
    agents: agentFiles,
    commandFiles: cmdFiles,
    plugins,
    skillDirs: plugin.skills.map((skill) => ({ sourceDir: skill.sourceDir, name: skill.name })),
  }
}

function convertAgent(agent: ClaudeAgent, options: ClaudeToOpenCodeOptions) {
  const frontmatter: Record<string, unknown> = {
    description: agent.description,
    mode: options.agentMode,
  }

  if (agent.model && agent.model !== "inherit") {
    frontmatter.model = normalizeModel(agent.model)
  }

  if (options.inferTemperature) {
    const temperature = inferTemperature(agent)
    if (temperature !== undefined) {
      frontmatter.temperature = temperature
    }
  }

  const content = formatFrontmatter(frontmatter, rewriteClaudePaths(agent.body))

  return {
    name: agent.name,
    content,
  }
}

// Commands are written as individual .md files rather than entries in opencode.json.
// Chosen over JSON map because opencode resolves commands by filename at runtime (ADR-001).
function convertCommands(commands: ClaudeCommand[]): OpenCodeCommandFile[] {
  const files: OpenCodeCommandFile[] = []
  for (const command of commands) {
    if (command.disableModelInvocation) continue
    const frontmatter: Record<string, unknown> = {
      description: command.description,
    }
    if (command.model && command.model !== "inherit") {
      frontmatter.model = normalizeModel(command.model)
    }
    const content = formatFrontmatter(frontmatter, rewriteClaudePaths(command.body))
    files.push({ name: command.name, content })
  }
  return files
}

function convertMcp(servers: Record<string, ClaudeMcpServer>): Record<string, OpenCodeMcpServer> {
  const result: Record<string, OpenCodeMcpServer> = {}
  for (const [name, server] of Object.entries(servers)) {
    if (server.command) {
      result[name] = {
        type: "local",
        command: [server.command, ...(server.args ?? [])],
        environment: server.env,
        enabled: true,
      }
      continue
    }

    if (server.url) {
      result[name] = {
        type: "remote",
        url: server.url,
        headers: server.headers,
        enabled: true,
      }
    }
  }
  return result
}

function convertHooks(hooks: ClaudeHooks, pluginName: string) {
  if (!/^[a-z0-9][a-z0-9_-]*$/i.test(pluginName)) throw new Error("Invalid plugin name for hook installation")
  for (const [event, matchers] of Object.entries(hooks.hooks)) {
    if (event !== "PreToolUse" && event !== "PostToolUse") {
      throw new Error(`OpenCode conversion does not support Claude hook event ${event}`)
    }
    for (const matcher of matchers) {
      if (matcher.matcher && matcher.matcher !== "*") new RegExp(matcher.matcher)
      for (const hook of matcher.hooks) {
        if (hook.type !== "command") throw new Error(`OpenCode conversion does not support ${hook.type} hooks`)
        if (hook.timeout !== undefined && (!Number.isFinite(hook.timeout) || hook.timeout <= 0)) {
          throw new Error("Hook timeout must be a positive number")
        }
      }
    }
  }
  const supportPath = `../.whetstone/${pluginName}`
  return {
    name: "converted-hooks.ts",
    content: `import { fileURLToPath } from "node:url"
import { createHooks } from ${JSON.stringify(`${supportPath}/opencode-hooks.ts`)}

export default async function ({ directory }: { directory: string }) {
  const root = fileURLToPath(new URL(${JSON.stringify(`${supportPath}/plugin/`)}, import.meta.url))
  return createHooks(${JSON.stringify(hooks)}, root, directory)
}`,
  }
}

function rewriteClaudePaths(body: string): string {
  return body
    .replace(/~\/\.claude\//g, "~/.config/opencode/")
    .replace(/\.claude\//g, ".opencode/")
}

// Bare Claude family aliases used in Claude Code (e.g. `model: haiku`).
// Update these when new model generations are released.
const CLAUDE_FAMILY_ALIASES: Record<string, string> = {
  haiku: "claude-haiku-4-5",
  sonnet: "claude-sonnet-4-5",
  opus: "claude-opus-4-6",
}

function normalizeModel(model: string): string {
  if (model.includes("/")) return model
  if (CLAUDE_FAMILY_ALIASES[model]) {
    const resolved = `anthropic/${CLAUDE_FAMILY_ALIASES[model]}`
    console.warn(
      `Warning: bare model alias "${model}" mapped to "${resolved}". ` +
        `Update CLAUDE_FAMILY_ALIASES if a newer version is available.`,
    )
    return resolved
  }
  if (/^claude-/.test(model)) return `anthropic/${model}`
  if (/^(gpt-|o1-|o3-)/.test(model)) return `openai/${model}`
  if (/^gemini-/.test(model)) return `google/${model}`
  return `anthropic/${model}`
}

function inferTemperature(agent: ClaudeAgent): number | undefined {
  const sample = `${agent.name} ${agent.description ?? ""}`.toLowerCase()
  if (/(review|audit|security|sentinel|oracle|lint|verification|guardian)/.test(sample)) {
    return 0.1
  }
  if (/(plan|planning|architecture|strategist|analysis|research)/.test(sample)) {
    return 0.2
  }
  if (/(doc|readme|changelog|editor|writer)/.test(sample)) {
    return 0.3
  }
  if (/(brainstorm|creative|ideate|design|concept)/.test(sample)) {
    return 0.6
  }
  return 0.3
}

function applyPermissions(
  config: OpenCodeConfig,
  commands: ClaudeCommand[],
  mode: PermissionMode,
) {
  if (mode === "none") return

  const sourceTools = [
    "read",
    "write",
    "edit",
    "bash",
    "grep",
    "glob",
    "list",
    "webfetch",
    "skill",
    "patch",
    "task",
    "question",
    "todowrite",
    "todoread",
  ]
  let enabled = new Set<string>()
  const patterns: Record<string, Set<string>> = {}

  if (mode === "broad") {
    enabled = new Set(sourceTools)
  } else {
    for (const command of commands) {
      if (!command.allowedTools) continue
      for (const tool of command.allowedTools) {
        const parsed = parseToolSpec(tool)
        if (!parsed.tool) continue
        enabled.add(parsed.tool)
        if (parsed.pattern) {
          const normalizedPattern = normalizePattern(parsed.tool, parsed.pattern)
          if (!patterns[parsed.tool]) patterns[parsed.tool] = new Set()
          patterns[parsed.tool].add(normalizedPattern)
        }
      }
    }
  }

  const permission: Record<string, "allow" | "deny" | Record<string, "allow" | "deny">> = {}
  const tools: Record<string, boolean> = {}

  for (const tool of sourceTools) {
    tools[tool] = mode === "broad" ? true : enabled.has(tool)
  }

  if (mode === "broad") {
    for (const tool of sourceTools) {
      permission[tool] = "allow"
    }
  } else {
    for (const tool of sourceTools) {
      const toolPatterns = patterns[tool]
      if (toolPatterns && toolPatterns.size > 0) {
        const patternPermission: Record<string, "allow" | "deny"> = { "*": "deny" }
        for (const pattern of toolPatterns) {
          patternPermission[pattern] = "allow"
        }
        permission[tool] = patternPermission
      } else {
        permission[tool] = enabled.has(tool) ? "allow" : "deny"
      }
    }
  }

  if (mode !== "broad") {
    for (const [tool, toolPatterns] of Object.entries(patterns)) {
      if (!toolPatterns || toolPatterns.size === 0) continue
      const patternPermission: Record<string, "allow" | "deny"> = { "*": "deny" }
      for (const pattern of toolPatterns) {
        patternPermission[pattern] = "allow"
      }
      permission[tool] = patternPermission
    }
  }

  if (enabled.has("write") || enabled.has("edit")) {
    if (typeof permission.edit === "string") permission.edit = "allow"
    if (typeof permission.write === "string") permission.write = "allow"
  }
  if (patterns.write || patterns.edit) {
    const combined = new Set<string>()
    for (const pattern of patterns.write ?? []) combined.add(pattern)
    for (const pattern of patterns.edit ?? []) combined.add(pattern)
    const combinedPermission: Record<string, "allow" | "deny"> = { "*": "deny" }
    for (const pattern of combined) {
      combinedPermission[pattern] = "allow"
    }
    permission.edit = combinedPermission
    permission.write = combinedPermission
  }

  config.permission = permission
  config.tools = tools
}

function normalizeTool(raw: string): string | null {
  return parseToolSpec(raw).tool
}

function parseToolSpec(raw: string): { tool: string | null; pattern?: string } {
  const trimmed = raw.trim()
  if (!trimmed) return { tool: null }
  const [namePart, patternPart] = trimmed.split("(", 2)
  const name = namePart.trim().toLowerCase()
  const tool = TOOL_MAP[name] ?? null
  if (!patternPart) return { tool }
  const normalizedPattern = patternPart.endsWith(")")
    ? patternPart.slice(0, -1).trim()
    : patternPart.trim()
  return { tool, pattern: normalizedPattern }
}

function normalizePattern(tool: string, pattern: string): string {
  if (tool === "bash") {
    return pattern.replace(/:/g, " ").trim()
  }
  return pattern
}
