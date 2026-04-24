import { defineCommand } from "citty"
import { promises as fs } from "fs"
import os from "os"
import path from "path"
import { pathExists } from "../utils/files"

type TargetSpec = {
  name: string
  label: string
  paths: (home: string) => string[]
}

const TARGET_SPECS: Record<string, TargetSpec> = {
  codex: {
    name: "codex",
    label: "Codex",
    paths: (home) => [
      path.join(home, ".codex", "skills"),
      path.join(home, ".codex", "prompts"),
    ],
  },
  opencode: {
    name: "opencode",
    label: "OpenCode",
    paths: (home) => [path.join(home, ".opencode")],
  },
  kilocode: {
    name: "kilocode",
    label: "Kilocode",
    paths: (home) => [path.join(home, ".kilocode", "skills")],
  },
  agents: {
    name: "agents",
    label: ".agents (generic)",
    paths: (home) => [path.join(home, ".agents", "skills")],
  },
}

type CleanupResult = {
  backupDir: string
  moved: number
  skipped: number
}

export default defineCommand({
  meta: {
    name: "cleanup",
    description: "Back up stale plugin installs from a target before a fresh install",
  },
  args: {
    target: {
      type: "string",
      required: true,
      description: `Target to clean: ${Object.keys(TARGET_SPECS).join(" | ")}`,
    },
    dryRun: {
      type: "boolean",
      alias: "dry-run",
      default: false,
      description: "Print actions without moving files",
    },
  },
  async run({ args }) {
    const target = args.target
    const spec = TARGET_SPECS[target]
    if (!spec) {
      const known = Object.keys(TARGET_SPECS).join(" | ")
      throw new Error(`Unknown target: ${target}. Supported: ${known}`)
    }

    const home = os.homedir()
    const paths = spec.paths(home)
    const stamp = new Date().toISOString().replace(/[:.]/g, "-")
    const backupRoot = path.join(home, ".cache", "compound-engineering", "legacy-backup", `${spec.name}-${stamp}`)

    const result: CleanupResult = { backupDir: backupRoot, moved: 0, skipped: 0 }

    for (const p of paths) {
      if (!(await pathExists(p))) {
        result.skipped++
        continue
      }
      const relName = path.relative(home, p).replace(/[/\\]/g, "_")
      const dest = path.join(backupRoot, relName)
      if (args.dryRun) {
        console.log(`[dry-run] would move ${p} -> ${dest}`)
        result.moved++
        continue
      }
      await fs.mkdir(path.dirname(dest), { recursive: true })
      await fs.rename(p, dest)
      console.log(`moved ${p} -> ${dest}`)
      result.moved++
    }

    if (result.moved === 0) {
      console.log(`Nothing to clean under ${spec.label}. (${result.skipped} paths not present)`)
      return
    }

    console.log(
      `\n${spec.label} cleanup: moved ${result.moved} artifact(s) to ${backupRoot}` +
        (args.dryRun ? " (dry run — no files touched)" : ""),
    )
  },
})
