import { mkdtemp, mkdir, readFile, rm, writeFile } from "fs/promises"
import os from "os"
import path from "path"
import { afterEach, expect, test } from "bun:test"

const roots: string[] = []
afterEach(async () => {
  await Promise.all(roots.splice(0).map((root) => rm(root, { recursive: true, force: true })))
})

for (const target of ["opencode", "codex"]) {
  for (const sourceKind of ["home", "home child", "absolute", "relative"]) {
    test(`convert accepts a ${sourceKind} source path for ${target}`, async () => {
      const root = await mkdtemp(path.join(os.tmpdir(), "whetstone-convert-"))
      roots.push(root)
      const home = path.join(root, "home")
      const plugin = sourceKind === "home" ? home : path.join(home, "plugin with spaces")
      await mkdir(path.join(plugin, ".claude-plugin"), { recursive: true })
      await writeFile(path.join(plugin, ".claude-plugin/plugin.json"), JSON.stringify({ name: "demo", version: "1.0.0" }))
      await mkdir(path.join(plugin, "skills/example"), { recursive: true })
      const skill = "---\nname: example\ndescription: Example skill\n---\n\nPreserve this skill body.\n"
      await writeFile(path.join(plugin, "skills/example/SKILL.md"), skill)
      const source = sourceKind === "home" ? "~"
        : sourceKind === "home child" ? "~/plugin with spaces"
        : sourceKind === "relative" ? path.relative(root, plugin) : plugin
      const output = path.join(root, "output")
      const codexHome = path.join(root, ".codex")
      const proc = Bun.spawn([
        process.execPath, "run", path.resolve("src/index.ts"), "convert", source,
        "--to", target, "--output", output, "--codex-home", codexHome,
      ], { cwd: root, env: { ...process.env, HOME: home }, stdout: "pipe", stderr: "pipe" })
      const [stdout, stderr, exitCode] = await Promise.all([
        new Response(proc.stdout).text(), new Response(proc.stderr).text(), proc.exited,
      ])
      expect(stderr).toBe("")
      expect(exitCode).toBe(0)
      const destination = target === "codex" ? codexHome : output
      expect(stdout).toBe(`Converted demo to ${target} at ${destination}\n`)
      const skillsRoot = target === "codex" ? codexHome : path.join(output, ".opencode")
      expect(await readFile(path.join(skillsRoot, "skills/example/SKILL.md"), "utf8")).toBe(skill)
      expect(await readFile(path.join(plugin, "skills/example/SKILL.md"), "utf8")).toBe(skill)
    })
  }
}
