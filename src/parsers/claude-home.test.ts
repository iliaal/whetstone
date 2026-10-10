import { mkdtemp, mkdir, readFile, realpath, rm, symlink, writeFile } from "fs/promises"
import path from "path"
import { afterEach, expect, test } from "bun:test"
import { loadClaudeHome } from "./claude-home"
import { syncToCodex } from "../sync/codex"
import { syncToOpenCode } from "../sync/opencode"

const tempRoots: string[] = []

afterEach(async () => {
  await Promise.all(tempRoots.splice(0).map((dir) => rm(dir, { recursive: true, force: true })))
})

for (const [target, sync] of [["codex", syncToCodex], ["opencode", syncToOpenCode]] as const) {
  for (const relative of [true, false]) {
    test(`${target} sync keeps skills readable with ${relative ? "a relative" : "an absolute"} Claude home`, async () => {
      const root = await mkdtemp(path.join(process.cwd(), ".whetstone-home-"))
      tempRoots.push(root)
      const home = path.join(root, "claude home")
      const source = path.join(home, "skills", "ia-demo")
      await mkdir(source, { recursive: true })
      await writeFile(path.join(source, "SKILL.md"), "# Demo skill\n")
      await symlink(source, path.join(home, "skills", "ia-linked"))
      await writeFile(path.join(home, "settings.json"), JSON.stringify({ mcpServers: {} }))

      const config = await loadClaudeHome(relative ? path.relative(process.cwd(), home) : home)
      const output = path.join(root, target)
      await sync(config, output)
      await sync(config, output)

      for (const name of ["ia-demo", "ia-linked"]) {
        const installed = path.join(output, "skills", name)
        expect(await readFile(path.join(installed, "SKILL.md"), "utf8")).toBe("# Demo skill\n")
        expect(await realpath(installed)).toBe(await realpath(source))
      }
    })
  }
}
