import { defineCommand } from "citty"
import { promises as fs } from "fs"
import os from "os"
import path from "path"
import { fileURLToPath } from "url"
import { loadClaudePlugin } from "../parsers/claude"
import { convertClaudeToOpenCode } from "../converters/claude-to-opencode"
import { convertClaudeToCodex } from "../converters/claude-to-codex"
import { resolveOpenCodePaths } from "../targets/opencode"
import { expandHome } from "../utils/resolve-home"

const targets = ["codex", "opencode", "kilocode", "agents"]
const pluginRoot = fileURLToPath(new URL("../../plugins/whetstone/", import.meta.url))

async function sameTree(installed: string, source: string): Promise<boolean> {
  const actual = await fs.lstat(installed).catch((error: NodeJS.ErrnoException) => {
    if (error.code === "ENOENT") return null
    throw error
  })
  if (!actual) return false
  if (actual.isSymbolicLink()) {
    return path.resolve(path.dirname(installed), await fs.readlink(installed)) === path.resolve(source)
  }
  const expected = await fs.lstat(source)
  if (actual.isFile() && expected.isFile()) {
    return (await fs.readFile(installed)).equals(await fs.readFile(source))
  }
  if (!actual.isDirectory() || !expected.isDirectory()) return false
  const names = (await fs.readdir(installed)).sort()
  const expectedNames = (await fs.readdir(source)).sort()
  if (JSON.stringify(names) !== JSON.stringify(expectedNames)) return false
  for (const name of names) {
    if (!await sameTree(path.join(installed, name), path.join(source, name))) return false
  }
  return true
}

async function matchesText(installed: string, expected: string): Promise<boolean> {
  try {
    if (!(await fs.lstat(installed)).isFile()) return false
    return await fs.readFile(installed, "utf8") === expected
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return false
    throw error
  }
}

export async function findOwnedInstalls(target: string, home: string, output?: string): Promise<string[]> {
  const owned = new Set<string>()
  const skillSource = path.join(pluginRoot, "skills")
  const skillRoots = target === "opencode"
    ? (output ? [output] : [process.cwd(), path.join(home, ".config/opencode"), path.join(home, ".opencode")])
        .map((root) => resolveOpenCodePaths(root).skillsDir)
    : [path.join(target === "codex" ? process.env.CODEX_HOME ?? path.join(home, ".codex") : path.join(home, `.${target}`), "skills")]
  for (const root of skillRoots) {
    for (const name of await fs.readdir(skillSource)) {
      const installed = path.join(root, name)
      if (await sameTree(installed, path.join(skillSource, name))) owned.add(installed)
    }
  }
  if (target !== "opencode" && target !== "codex") return [...owned]
  const plugin = await loadClaudePlugin(pluginRoot)
  const options = { agentMode: "subagent" as const, inferTemperature: true, permissions: "none" as const }
  if (target === "codex") {
    const root = process.env.CODEX_HOME ?? path.join(home, ".codex")
    const bundle = convertClaudeToCodex(plugin, options)
    for (const prompt of bundle.prompts) {
      const installed = path.join(root, "prompts", `${prompt.name}.md`)
      if (await matchesText(installed, prompt.content + "\n")) owned.add(installed)
    }
    for (const skill of bundle.generatedSkills) {
      const installed = path.join(root, "skills", skill.name)
      if (await matchesText(path.join(installed, "SKILL.md"), skill.content + "\n") &&
          JSON.stringify(await fs.readdir(installed)) === '["SKILL.md"]') owned.add(installed)
    }
  } else {
    const bundle = convertClaudeToOpenCode(plugin, options)
    const roots = output ? [output] : [process.cwd(), path.join(home, ".config/opencode"), path.join(home, ".opencode")]
    for (const root of roots) {
      const paths = resolveOpenCodePaths(root)
      for (const [directory, files] of [
        [paths.agentsDir, bundle.agents.map((entry) => ({ name: `${entry.name}.md`, content: entry.content }))],
        [paths.commandDir, bundle.commandFiles.map((entry) => ({ name: `${entry.name}.md`, content: entry.content }))],
        [paths.pluginsDir, bundle.plugins],
      ] as const) {
        for (const file of files) {
          const installed = path.join(directory, file.name)
          if (await matchesText(installed, file.content + "\n")) owned.add(installed)
        }
      }
      const support = path.join(paths.supportDir, plugin.manifest.name)
      const runtimePath = fileURLToPath(new URL("../runtime/opencode-hooks.ts", import.meta.url))
      const installedPlugins = await fs.readdir(paths.pluginsDir).catch((error: NodeJS.ErrnoException) => {
        if (error.code === "ENOENT") return []
        throw error
      })
      // Surviving local plugins can import support through arbitrary JavaScript paths.
      const hasSurvivingPlugin = installedPlugins.some((name) => !owned.has(path.join(paths.pluginsDir, name)))
      if (!hasSurvivingPlugin && await sameTree(path.join(support, "plugin"), pluginRoot) &&
          await sameTree(path.join(support, "opencode-hooks.ts"), runtimePath) &&
          JSON.stringify((await fs.readdir(support)).sort()) === '["opencode-hooks.ts","plugin"]') owned.add(support)
    }
  }
  return [...owned]
}

export default defineCommand({
  meta: {
    name: "cleanup",
    description: "Back up identifiable Whetstone installs, preserving unrelated or modified files",
  },
  args: {
    target: { type: "string", required: true, description: `Target: ${targets.join(" | ")}` },
    output: { type: "string", alias: "o", description: "OpenCode project or config root (default: current project and legacy global roots)" },
    dryRun: { type: "boolean", alias: "dry-run", default: false, description: "Print actions without moving files" },
  },
  async run({ args }) {
    if (!targets.includes(args.target)) throw new Error(`Unknown target: ${args.target}`)
    if (args.output && args.target !== "opencode") throw new Error("--output is only supported for OpenCode cleanup")
    const home = os.homedir()
    const output = args.output ? path.resolve(expandHome(args.output)) : undefined
    const candidates = await findOwnedInstalls(args.target, home, output)
    const stamp = new Date().toISOString().replace(/[:.]/g, "-")
    const backupRoot = path.join(home, ".cache/whetstone/legacy-backup", `${args.target}-${stamp}`)
    for (const installed of candidates) {
      const destination = path.join(backupRoot, encodeURIComponent(installed))
      if (args.dryRun) console.log(`[dry-run] would move ${installed} -> ${destination}`)
      else {
        await fs.mkdir(backupRoot, { recursive: true })
        await fs.rename(installed, destination)
        console.log(`moved ${installed} -> ${destination}`)
      }
    }
    console.log(`${args.target} cleanup: ${candidates.length} owned artifact(s)${args.dryRun ? " (dry run)" : ` backed up to ${backupRoot}`}. Unidentified or modified entries and configs are preserved.`)
  },
})
