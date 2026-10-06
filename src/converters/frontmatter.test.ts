import { expect, test } from "bun:test"
import { convertClaudeToCodex } from "./claude-to-codex"
import { convertClaudeToOpenCode } from "./claude-to-opencode"
import type { ClaudePlugin } from "../types/claude"
import { parseFrontmatter } from "../utils/frontmatter"

const options = {
  agentMode: "subagent" as const,
  inferTemperature: false,
  permissions: "none" as const,
}

test("converters preserve descriptions containing YAML comments and scalar syntax", () => {
  const plugin: ClaudePlugin = {
    root: "/unused",
    manifest: { name: "demo", version: "1.0.0" },
    skills: [],
    agents: [{ name: "helper", description: "true", body: "Help.", sourcePath: "/unused/helper.md" }],
    commands: [{
      name: "review", description: "Review #123", argumentHint: "@owner",
      body: "Review the change.", sourcePath: "/unused/review.md",
    }],
  }

  const opencode = convertClaudeToOpenCode(plugin, options)
  expect(parseFrontmatter(opencode.agents[0].content).data.description).toBe("true")
  expect(parseFrontmatter(opencode.commandFiles[0].content).data.description).toBe("Review #123")

  const codex = convertClaudeToCodex(plugin, options)
  expect(parseFrontmatter(codex.prompts[0].content).data).toEqual({
    description: "Review #123", "argument-hint": "@owner",
  })
  expect(codex.generatedSkills.map((skill) => parseFrontmatter(skill.content).data.description))
    .toEqual(["Review #123", "true"])
})
