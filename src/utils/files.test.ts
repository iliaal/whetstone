import { afterEach, expect, spyOn, test } from "bun:test"
import { mkdtemp, readFile, rm, stat, writeFile } from "fs/promises"
import os from "os"
import path from "path"
import { backupFile } from "./files"

const roots: string[] = []
const timestamp = "2026-10-12T14:00:00.000Z"

afterEach(async () => {
  await Promise.all(roots.splice(0).map((root) => rm(root, { recursive: true, force: true })))
})

async function sourceFile(): Promise<string> {
  const root = await mkdtemp(path.join(os.tmpdir(), "whetstone-backup-"))
  roots.push(root)
  const source = path.join(root, "config.json")
  await writeFile(source, "current contents")
  return source
}

test("backupFile preserves successive snapshots taken in the same millisecond", async () => {
  const source = await sourceFile()
  const clock = spyOn(Date.prototype, "toISOString").mockReturnValue(timestamp)
  try {
    const first = await backupFile(source)
    await writeFile(source, "updated contents")
    const second = await backupFile(source)
    expect(first).toBe(`${source}.bak.2026-10-12T14-00-00-000Z`)
    expect(second).not.toBe(first)
    expect(await readFile(first!, "utf8")).toBe("current contents")
    expect(await readFile(second!, "utf8")).toBe("updated contents")
    expect((await stat(first!)).mode & 0o777).toBe(0o600)
    expect((await stat(second!)).mode & 0o777).toBe(0o600)
  } finally {
    clock.mockRestore()
  }
})

test("backupFile exclusively creates distinct concurrent backups at a fixed timestamp", async () => {
  const source = await sourceFile()
  const clock = spyOn(Date.prototype, "toISOString").mockReturnValue(timestamp)
  try {
    const results = await Promise.allSettled(Array.from({ length: 20 }, () => backupFile(source)))
    expect(results.every((result) => result.status === "fulfilled")).toBe(true)
    const backups = results.map((result) => (result as PromiseFulfilledResult<string>).value)
    expect(new Set(backups).size).toBe(20)
    for (const backup of backups) {
      expect(await readFile(backup, "utf8")).toBe("current contents")
      expect((await stat(backup)).mode & 0o777).toBe(0o600)
    }
  } finally {
    clock.mockRestore()
  }
})
