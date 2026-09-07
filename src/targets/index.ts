import type { ClaudePlugin } from "../types/claude"
import type { OpenCodeBundle } from "../types/opencode"
import type { CodexBundle } from "../types/codex"
import { convertClaudeToOpenCode, type ClaudeToOpenCodeOptions } from "../converters/claude-to-opencode"
import { convertClaudeToCodex } from "../converters/claude-to-codex"
import { writeOpenCodeBundle } from "./opencode"
import { writeCodexBundle } from "./codex"

export type TargetHandler<TBundle = OpenCodeBundle | CodexBundle> = {
  name: string
  implemented: boolean
  convert: (plugin: ClaudePlugin, options: ClaudeToOpenCodeOptions) => TBundle | null
  write: (outputRoot: string, bundle: TBundle) => Promise<void>
}

export const targets: Record<string, TargetHandler> = {
  opencode: {
    name: "opencode",
    implemented: true,
    convert: convertClaudeToOpenCode,
    write: (root, bundle) => {
      if (!("agents" in bundle)) throw new Error("Expected an OpenCode bundle")
      return writeOpenCodeBundle(root, bundle)
    },
  },
  codex: {
    name: "codex",
    implemented: true,
    convert: convertClaudeToCodex,
    write: (root, bundle) => {
      if (!("prompts" in bundle)) throw new Error("Expected a Codex bundle")
      return writeCodexBundle(root, bundle)
    },
  },
}
