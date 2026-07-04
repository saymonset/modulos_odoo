# Taste (Continuously Learned by [CommandCode][cmd])

[cmd]: https://commandcode.ai/

# git
- Never run `git commit` — the user does commits manually and tests first. Confidence: 0.85

# odoo
- Use declarative XML view inheritance (like sales views) over direct DB manipulation. Follow Odoo best practices. Confidence: 0.70
- In QWeb templates, format monetary amounts using t-options="{'widget': 'monetary', 'display_currency': currency_var}" — never use format_amount() which doesn't exist in QWeb context. Confidence: 0.70

