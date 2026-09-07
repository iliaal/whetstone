import { mkdtemp, mkdir, readFile, rm, symlink, writeFile, lstat, appendFile } from "fs/promises"
import os from "os"
import path from "path"
import { pathToFileURL } from "url"
import { afterEach, expect, test } from "bun:test"

const roots: string[] = []
afterEach(async () => {
  await Promise.all(roots.splice(0).map((root) => rm(root, { recursive: true, force: true })))
})

test("cleanup backs up owned links while preserving unrelated and modified skills", async () => {
  const home = await mkdtemp(path.join(os.tmpdir(), "whetstone-cleanup-"))
  roots.push(home)
  const skills = path.join(home, ".agents/skills")
  await mkdir(path.join(skills, "ia-debugging"), { recursive: true })
  await writeFile(path.join(skills, "ia-debugging/SKILL.md"), "My customized debugging skill")
  await mkdir(path.join(skills, "unrelated"))
  await writeFile(path.join(skills, "unrelated/SKILL.md"), "Unrelated skill")
  await symlink(path.resolve("plugins/whetstone/skills/ia-writing"), path.join(skills, "ia-writing"))
  const proc = Bun.spawn([process.execPath, "run", path.resolve("src/index.ts"), "cleanup", "--target", "agents"], {
    env: { ...process.env, HOME: home }, stdout: "pipe", stderr: "pipe",
  })
  const stdout = await new Response(proc.stdout).text()
  const stderr = await new Response(proc.stderr).text()
  expect(await proc.exited).toBe(0)
  expect(stderr).toBe("")
  expect(await readFile(path.join(skills, "unrelated/SKILL.md"), "utf8")).toBe("Unrelated skill")
  expect(await readFile(path.join(skills, "ia-debugging/SKILL.md"), "utf8")).toBe("My customized debugging skill")
  expect(stdout).toContain("ia-writing")
  expect(await lstat(path.join(skills, "ia-writing")).catch(() => null)).toBeNull()
})

test.each([false, true])("project cleanup preserves user artifacts (customized plugin: %s)", async (customized) => {
  const home = await mkdtemp(path.join(os.tmpdir(), "whetstone-project-"))
  roots.push(home)
  const project = path.join(home, "opencode")
  await mkdir(project)
  const cli = path.resolve("src/index.ts")
  const install = Bun.spawn([process.execPath, "run", cli, "install", path.resolve("plugins/whetstone"), "--to", "opencode"], {
    cwd: project, env: { ...process.env, HOME: home }, stdout: "pipe", stderr: "pipe",
  })
  await Promise.all([new Response(install.stdout).text(), new Response(install.stderr).text()])
  expect(await install.exited).toBe(0)
  const ownedSkill = path.join(project, ".opencode/skills/ia-debugging/SKILL.md")
  expect(await readFile(ownedSkill, "utf8")).toContain("name: ia-debugging")
  const config = await readFile(path.join(project, "opencode.json"), "utf8")
  const pluginFile = path.join(project, ".opencode/plugins/converted-hooks.ts")
  if (customized) await appendFile(pluginFile, "\n// Local customization\n")
  const unrelated = path.join(project, ".opencode/agents/personal.md")
  await writeFile(unrelated, "My own agent")
  const cleanup = Bun.spawn([process.execPath, "run", cli, "cleanup", "--target", "opencode"], {
    cwd: project, env: { ...process.env, HOME: home }, stdout: "pipe", stderr: "pipe",
  })
  await Promise.all([new Response(cleanup.stdout).text(), new Response(cleanup.stderr).text()])
  expect(await cleanup.exited).toBe(0)
  expect(await readFile(unrelated, "utf8")).toBe("My own agent")
  expect(await readFile(path.join(project, "opencode.json"), "utf8")).toBe(config)
  expect(await lstat(ownedSkill).catch(() => null)).toBeNull()
  if (customized) {
    const installed = await import(pathToFileURL(pluginFile).href)
    const hooks = await installed.default({ directory: project })
    const args = { prompt: "Debug the failing Python test and find its root cause", subagent_type: "general" }
    await hooks["tool.execute.before"]({ tool: "task", sessionID: "cleanup-session", callID: "call-1" }, { args })
    expect(args.prompt).toContain("BEFORE STARTING:")
    for (const match of args.prompt.matchAll(/^- (.+\/SKILL\.md)$/gm)) {
      expect(await readFile(match[1], "utf8")).toContain("name:")
    }
  } else {
    expect(await lstat(pluginFile).catch(() => null)).toBeNull()
    expect(await lstat(path.join(project, ".opencode/.whetstone/whetstone")).catch(() => null)).toBeNull()
  }
})
