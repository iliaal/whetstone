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
export function isValidSkillName(name: string): boolean {
  if (!name || name.length === 0) return false
  if (name.includes("/") || name.includes("\\")) return false
  if (name.includes("..")) return false
  if (name.includes("\0")) return false
  if (name === "." || name === "..") return false
  return true
}
