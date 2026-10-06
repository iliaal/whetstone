import { dump, load } from "js-yaml"

export type FrontmatterResult = {
  data: Record<string, unknown>
  body: string
}

export function parseFrontmatter(raw: string): FrontmatterResult {
  const lines = raw.split(/\r?\n/)
  if (lines.length === 0 || lines[0].trim() !== "---") {
    return { data: {}, body: raw }
  }

  let endIndex = -1
  for (let i = 1; i < lines.length; i += 1) {
    if (lines[i].trim() === "---") {
      endIndex = i
      break
    }
  }

  if (endIndex === -1) {
    return { data: {}, body: raw }
  }

  const yamlText = lines.slice(1, endIndex).join("\n")
  const body = lines.slice(endIndex + 1).join("\n")
  const parsed = load(yamlText)
  const data = (parsed && typeof parsed === "object") ? (parsed as Record<string, unknown>) : {}
  return { data, body }
}

export function formatFrontmatter(data: Record<string, unknown>, body: string): string {
  const entries = Object.entries(data).filter(([, value]) => value !== undefined)
  if (entries.length === 0) {
    return body
  }

  // Quote strings so YAML syntax, implicit types, and trailing newlines survive conversion.
  const yaml = dump(Object.fromEntries(entries), { lineWidth: -1, forceQuotes: true }).trimEnd()
  return [`---`, yaml, `---`, "", body].join("\n")
}
