import { formatFrontmatter } from "../utils/frontmatter"
import type { ClaudeAgent, ClaudeCommand, ClaudePlugin } from "../types/claude"
import type { CodexBundle, CodexGeneratedSkill } from "../types/codex"
import type { ClaudeToOpenCodeOptions } from "./claude-to-opencode"

export type ClaudeToCodexOptions = ClaudeToOpenCodeOptions

const CODEX_DESCRIPTION_MAX_LENGTH = 1024

export function convertClaudeToCodex(
  plugin: ClaudePlugin,
  _options: ClaudeToCodexOptions,
): CodexBundle {
  const promptNames = new Set<string>()
  const skillDirs = plugin.skills.map((skill) => ({
    name: skill.name,
    sourceDir: skill.sourceDir,
  }))

  const usedSkillNames = new Set<string>(skillDirs.map((skill) => normalizeName(skill.name)))
  const commandSkills: CodexGeneratedSkill[] = []
  const invocableCommands = plugin.commands.filter((command) => !command.disableModelInvocation)
  const prompts = invocableCommands.map((command) => {
    const promptName = uniqueName(normalizeName(command.name), promptNames)
    const commandSkill = convertCommandSkill(command, usedSkillNames)
    commandSkills.push(commandSkill)
    const content = renderPrompt(command, commandSkill.name)
    return { name: promptName, content }
  })

  const agentSkills = plugin.agents.map((agent) => convertAgent(agent, usedSkillNames))
  const generatedSkills = [...commandSkills, ...agentSkills]

  return {
    prompts,
    skillDirs,
    generatedSkills,
    mcpServers: plugin.mcpServers,
  }
}

function convertAgent(agent: ClaudeAgent, usedNames: Set<string>): CodexGeneratedSkill {
  const name = uniqueName(normalizeName(agent.name), usedNames)
  const description = sanitizeDescription(
    agent.description ?? `Converted from Claude agent ${agent.name}`,
  )
  const frontmatter: Record<string, unknown> = { name, description }

  let body = transformContentForCodex(agent.body.trim())
  if (agent.capabilities && agent.capabilities.length > 0) {
    const capabilities = agent.capabilities.map((capability) => `- ${capability}`).join("\n")
    body = `## Capabilities\n${capabilities}\n\n${body}`.trim()
  }
  if (body.length === 0) {
    body = `Instructions converted from the ${agent.name} agent.`
  }

  const content = formatFrontmatter(frontmatter, body)
  return { name, content }
}

function convertCommandSkill(command: ClaudeCommand, usedNames: Set<string>): CodexGeneratedSkill {
  const name = uniqueName(normalizeName(command.name), usedNames)
  const frontmatter: Record<string, unknown> = {
    name,
    description: sanitizeDescription(
      command.description ?? `Converted from Claude command ${command.name}`,
    ),
  }
  const sections: string[] = []
  if (command.argumentHint) {
    sections.push(`## Arguments\n${command.argumentHint}`)
  }
  if (command.allowedTools && command.allowedTools.length > 0) {
    sections.push(`## Allowed tools\n${command.allowedTools.map((tool) => `- ${tool}`).join("\n")}`)
  }
  const transformedBody = transformTaskCalls(command.body.trim())
  sections.push(transformedBody)
  const body = sections.filter(Boolean).join("\n\n").trim()
  const content = formatFrontmatter(frontmatter, body.length > 0 ? body : command.body)
  return { name, content }
}

/**
 * Rewrite Claude Code invocation syntax for Codex:
 * 1. Task agent calls: Task agent-name(args) → Use the $agent-name skill to: args
 * 2. Slash commands: /command-name → /prompts:command-name
 * 3. .claude/ paths → .codex/
 * 4. Agent references: @agent-name → $agent-name skill
 */
function transformContentForCodex(body: string): string {
  let result = body

  // Matches "Task repo-research-analyst(args)" and "- Task best-practices-researcher(args)".
  const taskPattern = /^(\s*-?\s*)Task\s+([a-z][a-z0-9-]*)\(([^)]+)\)/gm
  result = result.replace(taskPattern, (_match, prefix: string, agentName: string, args: string) => {
    const skillName = normalizeName(agentName)
    const trimmedArgs = args.trim()
    return `${prefix}Use the $${skillName} skill to: ${trimmedArgs}`
  })

  // Matches /command-name and /ns:command; the lookbehind excludes URLs (://) and path segments.
  const slashCommandPattern = /(?<![:\w])\/([a-z][a-z0-9_:-]*?)(?=[\s,."')\]}`]|$)/gi
  result = result.replace(slashCommandPattern, (match, commandName: string) => {
    if (commandName.includes('/')) return match
    if (['dev', 'tmp', 'etc', 'usr', 'var', 'bin', 'home'].includes(commandName)) return match
    const normalizedName = normalizeName(commandName)
    return `/prompts:${normalizedName}`
  })

  result = result
    .replace(/~\/\.claude\//g, "~/.codex/")
    .replace(/\.claude\//g, ".codex/")

  // The required role suffix keeps email addresses from matching.
  const agentRefPattern = /@([a-z][a-z0-9-]*-(?:agent|reviewer|researcher|analyst|specialist|oracle|sentinel|guardian|strategist))/gi
  result = result.replace(agentRefPattern, (_match, agentName: string) => {
    const skillName = normalizeName(agentName)
    return `$${skillName} skill`
  })

  return result
}

const transformTaskCalls = transformContentForCodex

function renderPrompt(command: ClaudeCommand, skillName: string): string {
  const frontmatter: Record<string, unknown> = {
    description: command.description,
    "argument-hint": command.argumentHint,
  }
  const instructions = `Use the $${skillName} skill for this command and follow its instructions.`
  const transformedBody = transformTaskCalls(command.body)
  const body = [instructions, "", transformedBody].join("\n").trim()
  return formatFrontmatter(frontmatter, body)
}

function normalizeName(value: string): string {
  const trimmed = value.trim()
  if (!trimmed) return "item"
  const normalized = trimmed
    .toLowerCase()
    .replace(/[\\/]+/g, "-")
    .replace(/[:\s]+/g, "-")
    .replace(/[^a-z0-9_-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "")
  return normalized || "item"
}

function sanitizeDescription(value: string, maxLength = CODEX_DESCRIPTION_MAX_LENGTH): string {
  const normalized = value.replace(/\s+/g, " ").trim()
  if (normalized.length <= maxLength) return normalized
  const ellipsis = "..."
  return normalized.slice(0, Math.max(0, maxLength - ellipsis.length)).trimEnd() + ellipsis
}

function uniqueName(base: string, used: Set<string>): string {
  if (!used.has(base)) {
    used.add(base)
    return base
  }
  let index = 2
  while (used.has(`${base}-${index}`)) {
    index += 1
  }
  const name = `${base}-${index}`
  used.add(name)
  return name
}
