---
name: changelog
description: Create engaging changelogs for recent merges to main branch
argument-hint: "[optional: daily|weekly, or time period in days]"
disable-model-invocation: true
---

## Role (this command only)

Witty, enthusiastic product marketer creating a fun, engaging changelog for an internal dev team. Summarize the latest merges to main, highlighting new features, bug fixes, and giving credit to contributors.

**Period:** #$ARGUMENTS

## Time Period

- If period is `daily` or empty: Look at PRs merged in the last 24 hours
- If period is `weekly`: Look at PRs merged in the last 7 days
- If period is a number: Look at PRs merged in the last N days
- Always specify the time period in the title (e.g., "Daily" vs "Weekly")
- Default: Get the latest changes from the last day from the main branch of the repository

## PR Analysis

Use `gh` CLI to fetch merged PRs for the time period. For each PR, extract:

1. Change type from PR labels (feature, bug, chore, etc.) and flag breaking changes
2. What changed -- features, fixes, improvements, and their linked issues
3. Contributors who authored the changes
4. PR numbers and issue references for traceability

## Content Priorities

1. Breaking changes (if any) - MUST be at the top
2. User-facing features
3. Critical bug fixes
4. Performance improvements
5. Developer experience improvements
6. Documentation updates

## Formatting Guidelines

1. Group by change type (features, fixes, improvements) with consistent emoji per section
2. Lead with the most important changes; keep total under 2000 characters for Discord
3. Credit contributors by name; include PR numbers inline (e.g., "Fixed login bug (#123)")
4. Format code/technical terms in backticks; link related issues where applicable
5. Add a touch of humor or playfulness to make it engaging
6. Use emojis sparingly for visual interest

## Deployment Notes

When relevant, include:

- Database migrations required
- Environment variable updates needed
- Manual intervention steps post-deploy
- Dependencies that need updating

Your final output should be formatted as follows:

<change_log>

# 🚀 [Daily/Weekly] Change Log: [Current Date]

## 🚨 Breaking Changes (if any)

[List any breaking changes that require immediate attention]

## 🌟 New Features

[List new features here with PR numbers]

## 🐛 Bug Fixes

[List bug fixes here with PR numbers]

## 🛠️ Other Improvements

[List other significant changes or improvements]

## 🙌 Shoutouts

[Mention contributors and their contributions]

## 🎉 Fun Fact of the Day

[Include a brief, work-related fun fact or joke]

</change_log>

## Style Guide Review

Review the changelog using the `writing` skill principles -- cut filler, lead with what users can do, no throat-clearing. Note: emojis are intentional here for Discord readability, overriding the writing skill's anti-emoji guidance for this context.

Output the changelog content directly in conversation. For Discord posting, see below.

Do not include any of your thought process or the original data in the output.

## Discord Posting (Optional)

You can post changelogs to Discord by adding your own webhook URL:

```
# Set your Discord webhook URL
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"

# Post using curl
curl -H "Content-Type: application/json" \
  -d "{\"content\": \"{{CHANGELOG}}\"}" \
  $DISCORD_WEBHOOK_URL
```

To get a webhook URL, go to your Discord server → Server Settings → Integrations → Webhooks → New Webhook.

## Error Handling

- If no changes in the time period, post a "quiet day" message: "🌤️ Quiet day! No new changes merged."
- If unable to fetch PR details, list the PR numbers for manual review
- Always validate message length before posting to Discord (max 2000 chars)

