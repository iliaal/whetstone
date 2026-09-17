---
# Regression tripwire only. It passed in every recorded run of both the plugin
# and no-plugin arms, so a green result is not evidence of trigger discipline;
# skill-not-fired.md carries that check.
type: regex
target: last_message
match: not_contains
---
Ready to merge|Ready with fixes|Not ready|CR-\d{3}
