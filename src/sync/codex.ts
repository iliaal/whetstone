import fs from "fs/promises"
import path from "path"
import type { ClaudeHomeConfig } from "../parsers/claude-home"
import { LEGACY_SYNC_MARKERS, prepareCodexMcpConfig } from "../utils/codex-config"
import { forceSymlink, isValidSkillName } from "../utils/symlink"

export async function syncToCodex(
  config: ClaudeHomeConfig,
  outputRoot: string,
): Promise<void> {
  const servers: unknown = config.mcpServers
  if (typeof servers !== "object" || servers === null || Array.isArray(servers)) {
    throw new Error("Invalid Claude mcpServers config: expected an object")
  }
  const commandServers = Object.fromEntries(
    Object.entries(config.mcpServers).filter(([, server]) => server?.command !== undefined),
  )
  const applyConfig = await prepareCodexMcpConfig({
    root: outputRoot,
    configPath: path.join(outputRoot, "config.toml"),
    blockId: "claude-sync",
    servers: commandServers,
    legacyMarkers: LEGACY_SYNC_MARKERS,
  })

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

  await applyConfig()
}
