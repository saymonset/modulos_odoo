# Taste (Continuously Learned by [CommandCode][cmd])

[cmd]: https://commandcode.ai/

# git
- Never run `git commit` — the user does commits manually and tests first. Confidence: 0.85

# odoo
- Use declarative XML view inheritance (like sales views) over direct DB manipulation. Follow Odoo best practices. Confidence: 0.70
- In QWeb templates, format monetary amounts using t-options="{'widget': 'monetary', 'display_currency': currency_var}" — never use format_amount() which doesn't exist in QWeb context. Confidence: 0.70
- In Odoo 19 QWeb xpath expressions, use hasclass('class-name') instead of contains(@class, 'class-name') for class-based element selection — Odoo flags contains(@class) as error-prone. Confidence: 0.65
- When using Odoo 19's patch() on an OWL component, capture BaseClass.prototype.method before the patch and manually call it via .call(this, ...args) — patch() won't expose this._super for methods that don't exist on the base class, and other modules' patches can also break the super chain. Confidence: 0.75

