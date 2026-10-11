import fs from "fs/promises"
import path from "path"
import type { ClaudeHomeConfig } from "../parsers/claude-home"
import type { ClaudeMcpServer } from "../types/claude"
import type { OpenCodeMcpServer } from "../types/opencode"
import { assertSafeDestination, writeText } from "../utils/files"
import { setOwn } from "../utils/own-property"
import { forceSymlink, isValidSkillName } from "../utils/symlink"

export async function syncToOpenCode(
  config: ClaudeHomeConfig,
  outputRoot: string,
): Promise<void> {
  const skillsDir = path.join(outputRoot, "skills")
  await fs.mkdir(skillsDir, { recursive: true })

  for (const skill of config.skills) {
    if (!isValidSkillName(skill.name)) {
      console.warn(`Skipping skill with invalid name: ${skill.name}`)
      continue
    }
    const target = path.join(skillsDir, skill.name)
    await forceSymlink(skill.sourceDir, target)
  }

  if (Object.keys(config.mcpServers).length > 0) {
    const configPath = path.join(outputRoot, "opencode.json")
    await assertSafeDestination(outputRoot, configPath)
    const existing = await readJsonSafe(configPath)
    const mcpConfig = convertMcpForOpenCode(config.mcpServers)
    existing.mcp = { ...(existing.mcp ?? {}), ...mcpConfig }
    await writeText(configPath, JSON.stringify(existing, null, 2), { root: outputRoot, mode: 0o600 })
  }
}

async function readJsonSafe(filePath: string): Promise<Record<string, unknown>> {
  try {
    const content = await fs.readFile(filePath, "utf-8")
    return JSON.parse(content) as Record<string, unknown>
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") {
      return {}
    }
    throw err
  }
}

function convertMcpForOpenCode(
  servers: Record<string, ClaudeMcpServer>,
): Record<string, OpenCodeMcpServer> {
  const result: Record<string, OpenCodeMcpServer> = {}

  for (const [name, server] of Object.entries(servers)) {
    if (server.command) {
      setOwn(result, name, {
        type: "local",
        command: [server.command, ...(server.args ?? [])],
        environment: server.env,
        enabled: true,
      })
      continue
    }

    if (server.url) {
      setOwn(result, name, {
        type: "remote",
        url: server.url,
        headers: server.headers,
        enabled: true,
      })
    }
  }

  return result
}
