import fs from "fs/promises"

/**
 * Create a symlink at target, replacing an existing symlink or file but never a real directory.
 */
export async function forceSymlink(source: string, target: string): Promise<void> {
  try {
    const stat = await fs.lstat(target)
    if (stat.isSymbolicLink()) {
      await fs.unlink(target)
    } else if (stat.isDirectory()) {
      throw new Error(
        `Cannot create symlink at ${target}: a real directory exists there. ` +
        `Remove it manually if you want to replace it with a symlink.`
      )
    } else {
      await fs.unlink(target)
    }
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code !== "ENOENT") {
      throw err
    }
  }
  await fs.symlink(source, target)
}

/**
 * Reject skill names that could escape the skills directory.
 */
export function isValidSkillName(name: unknown): name is string {
  if (typeof name !== "string" || name.trim().length === 0) return false
  if (name.includes("/") || name.includes("\\")) return false
  if (name.includes("..")) return false
  if (/[\u0000-\u001f\u007f]/.test(name)) return false
  if (name === "." || name === "..") return false
  return true
}

export function requireValidComponentName(name: unknown): string {
  if (!isValidSkillName(name)) throw new Error(`Invalid component name: ${JSON.stringify(name)}`)
  return name
}
