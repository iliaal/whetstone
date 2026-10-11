import path from "path"
import { assertSafeDestination, copyDir, ensureDirWithin, writeText } from "../utils/files"
import {
  buildCodexMcpTables,
  LEGACY_CONVERT_MARKERS,
  renderMcpServerTables,
  prepareCodexMcpConfig,
} from "../utils/codex-config"
import { requireValidComponentName as requireName } from "../utils/symlink"
import type { CodexBundle } from "../types/codex"
import type { ClaudeMcpServer } from "../types/claude"

export async function writeCodexBundle(outputRoot: string, bundle: CodexBundle): Promise<void> {
  const codexRoot = resolveCodexRoot(outputRoot)
  // An explicit .codex home may be a dotfiles symlink; a .codex derived inside another directory
  // comes from that directory's contents (often a checkout) and must not redirect writes.
  if (codexRoot !== outputRoot) await assertSafeDestination(outputRoot, codexRoot, "directory")
  const blockId = `plugin:${requireName(bundle.pluginName)}`
  if (!/^[A-Za-z0-9:._-]+$/.test(blockId)) {
    throw new Error(`Plugin name ${JSON.stringify(bundle.pluginName)} cannot label a Codex config block`)
  }
  const applyConfig = await prepareCodexMcpConfig({
    root: codexRoot,
    configPath: path.join(codexRoot, "config.toml"),
    blockId,
    servers: bundle.mcpServers ?? {},
    legacyMarkers: LEGACY_CONVERT_MARKERS,
  })
  for (const prompt of bundle.prompts) {
    await assertSafeDestination(codexRoot, path.join(codexRoot, "prompts", `${requireName(prompt.name)}.md`))
  }
  for (const skill of [...bundle.skillDirs, ...bundle.generatedSkills]) {
    await assertSafeDestination(codexRoot, path.join(codexRoot, "skills", requireName(skill.name)), "directory")
  }
  for (const skill of bundle.generatedSkills) {
    await assertSafeDestination(codexRoot, path.join(codexRoot, "skills", skill.name, "SKILL.md"))
  }
  await ensureDirWithin(outputRoot, codexRoot)

  if (bundle.prompts.length > 0) {
    const promptsDir = path.join(codexRoot, "prompts")
    for (const prompt of bundle.prompts) {
      await writeText(path.join(promptsDir, `${requireName(prompt.name)}.md`), prompt.content + "\n", { root: codexRoot })
    }
  }

  if (bundle.skillDirs.length > 0) {
    const skillsRoot = path.join(codexRoot, "skills")
    for (const skill of bundle.skillDirs) {
      await copyDir(skill.sourceDir, path.join(skillsRoot, requireName(skill.name)), { root: codexRoot })
    }
  }

  if (bundle.generatedSkills.length > 0) {
    const skillsRoot = path.join(codexRoot, "skills")
    for (const skill of bundle.generatedSkills) {
      await writeText(
        path.join(skillsRoot, requireName(skill.name), "SKILL.md"),
        skill.content + "\n",
        { root: codexRoot },
      )
    }
  }

  await applyConfig()
}

function resolveCodexRoot(outputRoot: string): string {
  return path.basename(outputRoot) === ".codex" ? outputRoot : path.join(outputRoot, ".codex")
}

export function renderCodexConfig(mcpServers?: Record<string, ClaudeMcpServer>): string | null {
  if (!mcpServers) return null
  const tables = buildCodexMcpTables(mcpServers)
  if (Object.keys(tables).length === 0) return null
  return renderMcpServerTables(tables) + "\n"
}
