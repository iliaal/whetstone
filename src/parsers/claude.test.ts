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

test("loadClaudePlugin loads overlapping component paths only once", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "whetstone-parser-"))
  tempRoots.push(root)
  await mkdir(path.join(root, ".claude-plugin"), { recursive: true })
  await writeFile(path.join(root, ".claude-plugin", "plugin.json"), JSON.stringify({
    name: "demo",
    agents: ["./agents", "agents/nested", "extra-agents", "./extra-agents"],
    commands: ["./commands", "commands/nested", "extra-commands"],
    skills: ["./skills", "skills/ia-demo", "extra-skills"],
  }))
  const files = [
    "agents/nested/ia-demo.md", "extra-agents/ia-demo.md",
    "commands/nested/ia-demo.md", "extra-commands/ia-demo.md",
    "skills/ia-demo/SKILL.md", "extra-skills/ia-demo/SKILL.md",
  ]
  for (const file of files) {
    await mkdir(path.dirname(path.join(root, file)), { recursive: true })
    await writeFile(path.join(root, file), "---\nname: ia-demo\n---\nInstructions.\n")
  }

  const plugin = await loadClaudePlugin(root)

  // Distinct files with the same declared name must remain available to converters.
  expect(plugin.agents.map((agent) => path.relative(root, agent.sourcePath))).toEqual(files.slice(0, 2))
  expect(plugin.commands.map((command) => path.relative(root, command.sourcePath))).toEqual(files.slice(2, 4))
  expect(plugin.skills.map((skill) => path.relative(root, skill.skillPath))).toEqual(files.slice(4, 6))
})
