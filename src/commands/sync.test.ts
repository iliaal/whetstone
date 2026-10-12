import { mkdtemp, mkdir, readFile, readdir, rm, writeFile } from "fs/promises"
import os from "os"
import path from "path"
import { afterEach, expect, test } from "bun:test"

const roots: string[] = []
afterEach(async () => {
  await Promise.all(roots.splice(0).map((root) => rm(root, { recursive: true, force: true })))
})

for (const target of ["codex", "opencode"]) {
  for (const failure of ["invalid JSON", "settings directory"]) {
    test(`${target} sync preserves existing output when Claude has ${failure}`, async () => {
      const home = await mkdtemp(path.join(os.tmpdir(), "whetstone-sync-cli-"))
      roots.push(home)
      const claudeHome = path.join(home, ".claude")
      await mkdir(claudeHome)
      const settings = path.join(claudeHome, "settings.json")
      await writeFile(settings, JSON.stringify({ mcpServers: { demo: { command: "node", args: ["server.js"] } } }))
      const run = async () => {
        const proc = Bun.spawn([process.execPath, "run", path.resolve("src/index.ts"), "sync", "--target", target], {
          env: { ...process.env, HOME: home }, stdout: "pipe", stderr: "pipe",
        })
        const [stdout, stderr, exitCode] = await Promise.all([
          new Response(proc.stdout).text(), new Response(proc.stderr).text(), proc.exited,
        ])
        return { stdout, stderr, exitCode }
      }
      expect((await run()).exitCode).toBe(0)
      const output = target === "codex" ? path.join(home, ".codex") : path.join(home, ".config/opencode")
      const configPath = path.join(output, target === "codex" ? "config.toml" : "opencode.json")
      const original = await readFile(configPath, "utf8")
      expect(original).toContain("demo")
      const originalEntries = await readdir(output)
      const skill = path.join(claudeHome, "skills/new-skill")
      await mkdir(skill, { recursive: true })
      await writeFile(path.join(skill, "SKILL.md"), "# New skill\n")
      if (failure === "invalid JSON") {
        await writeFile(settings, '{"mcpServers":')
      } else {
        await rm(settings)
        await mkdir(settings)
      }

      const result = await run()
      expect(result.exitCode).not.toBe(0)
      expect(result.stderr).not.toBe("")
      expect(result.stdout).not.toContain("Done. Synced")
      expect(await readFile(configPath, "utf8")).toBe(original)
      expect(await readdir(output)).toEqual(originalEntries)
      expect(await readdir(path.join(output, "skills"))).toEqual([])
    })
  }
}
