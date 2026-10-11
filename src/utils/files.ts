import { constants, promises as fs } from "fs"
import { randomBytes } from "crypto"
import path from "path"

export type WriteOptions = {
  root?: string
  mode?: number
}

export async function backupFile(filePath: string): Promise<string | null> {
  const info = await lstatIfExists(filePath)
  if (!info) return null
  if (info.isSymbolicLink()) {
    throw new Error(`Refusing to back up symlink ${filePath}`)
  }
  if (!info.isFile()) {
    throw new Error(`Refusing to back up non-regular file ${filePath}`)
  }

  const timestamp = new Date().toISOString().replace(/[:.]/g, "-")
  const backupPath = `${filePath}.bak.${timestamp}`
  const source = await fs.open(filePath, constants.O_RDONLY | constants.O_NOFOLLOW)
  try {
    const content = await source.readFile()
    await fs.writeFile(backupPath, content, { flag: "wx", mode: 0o600 })
  } finally {
    await source.close()
  }
  return backupPath
}

export async function pathExists(filePath: string): Promise<boolean> {
  try {
    await fs.access(filePath)
    return true
  } catch {
    return false
  }
}

export async function lstatIfExists(filePath: string) {
  try {
    return await fs.lstat(filePath)
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") return null
    throw err
  }
}

export async function ensureDir(dirPath: string): Promise<void> {
  await fs.mkdir(dirPath, { recursive: true })
}

export async function readText(filePath: string): Promise<string> {
  return fs.readFile(filePath, "utf8")
}

export async function readJson<T>(filePath: string): Promise<T> {
  const raw = await readText(filePath)
  return JSON.parse(raw) as T
}

export function isWithin(root: string, target: string): boolean {
  const relative = path.relative(path.resolve(root), path.resolve(target))
  return relative === "" || (relative !== ".." && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative))
}

function relativeParts(root: string, target: string, allowRoot: boolean): string[] {
  const relative = path.relative(path.resolve(root), path.resolve(target))
  if (!isWithin(root, target) || (relative === "" && !allowRoot)) {
    throw new Error(`Refusing to write ${target}: path is outside the output root ${root}`)
  }
  return relative === "" ? [] : relative.split(path.sep)
}

// Components below the output root must be real directories, and the final entry absent or of the expected kind.
export async function assertSafeDestination(
  root: string,
  filePath: string,
  kind: "file" | "directory" = "file",
): Promise<void> {
  const parts = relativeParts(root, filePath, false)
  let current = path.resolve(root)
  for (let index = 0; index < parts.length; index += 1) {
    current = path.join(current, parts[index])
    const info = await lstatIfExists(current)
    if (!info) return
    if (info.isSymbolicLink()) {
      throw new Error(`Refusing to write through symlink ${current}`)
    }
    const isLast = index === parts.length - 1
    if (!isLast && !info.isDirectory()) {
      throw new Error(`Refusing to write ${filePath}: ${current} is not a directory`)
    }
    if (isLast && kind === "file" && !info.isFile()) {
      throw new Error(`Refusing to write ${filePath}: existing entry is not a regular file`)
    }
    if (isLast && kind === "directory" && !info.isDirectory()) {
      throw new Error(`Refusing to write into ${filePath}: existing entry is not a directory`)
    }
  }
}

export async function ensureDirWithin(root: string, dirPath: string): Promise<void> {
  const parts = relativeParts(root, dirPath, true)
  let current = path.resolve(root)
  await fs.mkdir(current, { recursive: true })
  for (const part of parts) {
    current = path.join(current, part)
    try {
      await fs.mkdir(current)
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code !== "EEXIST") throw err
    }
    const info = await fs.lstat(current)
    if (info.isSymbolicLink()) {
      throw new Error(`Refusing to write through symlink ${current}`)
    }
    if (!info.isDirectory()) {
      throw new Error(`Refusing to write into ${current}: not a directory`)
    }
  }
}

// Replacing via rename never dereferences whatever currently sits at the destination.
async function replaceFile(
  root: string,
  filePath: string,
  produce: (tempPath: string) => Promise<void>,
  mode?: number,
): Promise<void> {
  await assertSafeDestination(root, filePath)
  await ensureDirWithin(root, path.dirname(filePath))
  await replaceInVerifiedDir(filePath, produce, mode)
}

async function replaceInVerifiedDir(
  filePath: string,
  produce: (tempPath: string) => Promise<void>,
  mode?: number,
  keepProducedMode = false,
): Promise<void> {
  // Exclusive creation never follows a planted symlink, so a fresh path needs no temp file.
  try {
    await produce(filePath)
    return
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code !== "EEXIST") throw err
  }
  const existing = await lstatIfExists(filePath)
  if (existing?.isSymbolicLink()) {
    throw new Error(`Refusing to write through symlink ${filePath}`)
  }
  if (existing && !existing.isFile()) {
    throw new Error(`Refusing to write ${filePath}: existing entry is not a regular file`)
  }
  const tempPath = path.join(
    path.dirname(filePath),
    `.${path.basename(filePath)}.${randomBytes(6).toString("hex")}.tmp`,
  )
  try {
    await produce(tempPath)
    const finalMode = mode ?? (existing && !keepProducedMode ? existing.mode & 0o777 : undefined)
    if (finalMode !== undefined) await fs.chmod(tempPath, finalMode)
    await fs.rename(tempPath, filePath)
  } catch (err) {
    await fs.rm(tempPath, { force: true })
    throw err
  }
}

export async function writeText(filePath: string, content: string, options: WriteOptions = {}): Promise<void> {
  const root = options.root ?? path.dirname(filePath)
  await replaceFile(
    root,
    filePath,
    async (target) => {
      const handle = await fs.open(target, "wx", options.mode ?? 0o666)
      try {
        if (options.mode !== undefined) await handle.chmod(options.mode)
        await handle.writeFile(content, "utf8")
      } finally {
        await handle.close()
      }
    },
    options.mode,
  )
}

export async function writeJson(filePath: string, data: unknown, options: WriteOptions = {}): Promise<void> {
  const content = JSON.stringify(data, null, 2)
  await writeText(filePath, content + "\n", options)
}

export async function walkFiles(root: string): Promise<string[]> {
  const entries = await fs.readdir(root, { withFileTypes: true })
  const results: string[] = []
  for (const entry of entries) {
    const fullPath = path.join(root, entry.name)
    if (entry.isDirectory()) {
      const nested = await walkFiles(fullPath)
      results.push(...nested)
    } else if (entry.isFile()) {
      results.push(fullPath)
    }
  }
  return results
}

export async function copyDir(sourceDir: string, targetDir: string, options: { root?: string } = {}): Promise<void> {
  const root = options.root ?? targetDir
  await ensureDirWithin(root, targetDir)
  const entries = await fs.readdir(sourceDir, { withFileTypes: true })
  for (const entry of entries) {
    const sourcePath = path.join(sourceDir, entry.name)
    const targetPath = path.join(targetDir, entry.name)
    if (entry.isDirectory()) {
      await copyDir(sourcePath, targetPath, { root })
    } else if (entry.isFile()) {
      // copyFile carries the source mode, so executable bundled scripts stay executable.
      await replaceInVerifiedDir(targetPath, async (tempPath) => {
        await fs.copyFile(sourcePath, tempPath, constants.COPYFILE_EXCL)
      }, undefined, true)
    }
  }
}
