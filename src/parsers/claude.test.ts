import { mkdtemp, mkdir, rm, writeFile } from "fs/promises"
import os from "os"
import path from "path"
import { afterEach, expect, test } from "bun:test"
import { loadClaudePlugin } from "./claude"

const tempRoots: string[] = []

afterEach(async () => {
  await Promise.all(tempRoots.splice(0).map((dir) => rm(dir, { recursive: true, force: true })))
})

test("loadClaudePlugin ignores command support markdown", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "whetstone-parser-"))
  tempRoots.push(root)

  await mkdir(path.join(root, ".claude-plugin"), { recursive: true })
  await mkdir(path.join(root, "commands", "references"), { recursive: true })
  await mkdir(path.join(root, "agents"), { recursive: true })
  await mkdir(path.join(root, "skills", "ia-demo"), { recursive: true })

  await writeFile(
    path.join(root, ".claude-plugin", "plugin.json"),
    JSON.stringify({ name: "demo", version: "1.0.0" }),
  )
  await writeFile(
    path.join(root, "commands", "ia-demo.md"),
    "---\nname: ia-demo\ndescription: Demo command\n---\n\nRun the demo.\n",
  )
  await writeFile(
    path.join(root, "commands", "references", "template.md"),
    "# Template\n\nThis support document is not invocable.\n",
  )
  await writeFile(
    path.join(root, "agents", "ia-helper.md"),
    "---\nname: ia-helper\ndescription: Helper agent\n---\n\nHelp.\n",
  )
  await writeFile(
    path.join(root, "skills", "ia-demo", "SKILL.md"),
    "---\nname: ia-demo\ndescription: Use when testing parser behavior.\n---\n\n# Demo\n",
  )

  const plugin = await loadClaudePlugin(root)

  expect(plugin.commands.map((command) => command.name)).toEqual(["ia-demo"])
})
