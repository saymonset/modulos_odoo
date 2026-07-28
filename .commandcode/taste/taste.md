# Taste (Continuously Learned by [CommandCode][cmd])

[cmd]: https://commandcode.ai/

# git
- Never run `git commit` — the user does commits manually and tests first. Confidence: 0.85

# communication
- Spanish is the preferred communication language for all interactions. Confidence: 0.95
- When debugging regressions, always investigate the most recent commits first via `git show` to identify the root cause — git-based root-cause analysis is the expected approach. Confidence: 0.75
- When a bug or inconsistency is found in one area, immediately perform a systematic cross-cutting search across ALL relevant files (views, reports, templates) for similar issues — the user expects a complete inventory of affected locations, not just a fix for the one reported instance. Confidence: 0.85

# odoo
See [odoo/taste.md](odoo/taste.md)
