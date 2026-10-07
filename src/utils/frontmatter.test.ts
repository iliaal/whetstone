import { expect, test } from "bun:test"
import { load } from "js-yaml"
import { formatFrontmatter, parseFrontmatter } from "./frontmatter"

function readFormattedData(data: Record<string, unknown>): unknown {
  const formatted = formatFrontmatter(data, "Body stays unchanged.\n")
  const end = formatted.indexOf("\n---\n", 4)
  expect(formatted.slice(end + 5)).toBe("\nBody stays unchanged.\n")
  const parsed = load(formatted.slice(4, end))
  expect(parsed).toEqual(parseFrontmatter(formatted).data)
  return parsed
}

test.each([
  "true", "false", "null", "~", "42", "0.5", "2026-10-06", "",
  "Review #123", "# heading", "*alias", "&anchor", "!tag", "@agent",
  "- item", "a: b", "[value]", "{value}", " leading", "trailing ",
  "---\nsecond", "first\nsecond", "first\nsecond\n", "first\nsecond\n\n",
])("frontmatter preserves string value %j", (value) => {
  expect(readFormattedData({ description: value })).toEqual({ description: value })
})

test("frontmatter preserves typed values and nested collections", () => {
  const data = {
    enabled: false,
    temperature: 0.5,
    missing: null,
    empty: [],
    tools: ["true", "Read #123", "line one\nline two", null, false, 42],
    metadata: { label: "null", tags: ["review", "fix"] },
    "key: with punctuation": "value",
  }
  expect(readFormattedData(data)).toEqual(data)
})

test("frontmatter omits undefined fields and leaves metadata-free bodies alone", () => {
  expect(readFormattedData({ name: "demo", description: undefined })).toEqual({ name: "demo" })
  expect(formatFrontmatter({}, "Body\n")).toBe("Body\n")
  expect(formatFrontmatter({ description: undefined }, "Body\n")).toBe("Body\n")
})
