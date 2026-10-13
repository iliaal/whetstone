import { expect, test } from "bun:test"
import { convertClaudeToCodex } from "./claude-to-codex"
import type { ClaudePlugin } from "../types/claude"
import { parseFrontmatter } from "../utils/frontmatter"

const options = { agentMode: "subagent" as const, inferTemperature: false, permissions: "none" as const }

function convertedBodies(body: string): string[] {
  const plugin: ClaudePlugin = {
    root: "/unused", manifest: { name: "demo", version: "1.0.0" }, skills: [],
    agents: [{ name: "helper", body, sourcePath: "/unused/helper.md" }],
    commands: [{ name: "review", body, sourcePath: "/unused/review.md" }],
  }
  const bundle = convertClaudeToCodex(plugin, options)
  return [...bundle.generatedSkills, ...bundle.prompts].map((item) => parseFrontmatter(item.content).body)
}

test("Codex preserves email addresses containing agent role names", () => {
  const addresses = [
    "ops@release-agent.example.com", "first.last@code-reviewer.example.com",
    "build+ci@repo-researcher.example.com", "on-call@risk-analyst.example.com",
    "a_b@db-specialist.example.com", "user!tag@data-oracle.example.com",
    "user%tag@code-sentinel.example.com", "user/tag@repo-guardian.example.com",
    "user=tag@plan-strategist.example.com",
    "star*@release-agent.example.com", '"quoted user"@release-agent.example.com',
    "ops@release-agent", "name@code-reviewer", "x@code-reviewer", "a@code-reviewer.example",
    "<ops@release-agent.example.com>", "[email](mailto:ops@release-agent.example.com)",
    "`ops@release-agent.example.com`",
  ]
  for (const address of addresses) {
    for (const body of convertedBodies(`Contact ${address} for details.`)) {
      expect(body).toContain(`Contact ${address} for details.`)
    }
  }
})

test("Codex still converts standalone agent references in prose and Markdown", () => {
  for (const [source, expected] of [
    ["@code-reviewer", "$code-reviewer skill"],
    ["Ask @code-reviewer.", "Ask $code-reviewer skill."],
    ["(@code-reviewer)", "($code-reviewer skill)"],
    ["`@code-reviewer`", "`$code-reviewer skill`"],
    ["**@code-reviewer**", "**$code-reviewer skill**"],
    ["_@code-reviewer_", "_$code-reviewer skill_"],
    ["__@code-reviewer__", "__$code-reviewer skill__"],
  ]) {
    for (const body of convertedBodies(source)) expect(body).toContain(expected)
  }
})


test("Codex preserves long uninterrupted text beside agent references", () => {
  const text = "x".repeat(100_000)
  for (const body of convertedBodies(`${text} @code-reviewer`)) {
    expect(body).toContain(`${text} $code-reviewer skill`)
  }
}, 1000)
