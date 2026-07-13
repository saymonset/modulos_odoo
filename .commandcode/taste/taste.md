# Taste (Continuously Learned by [CommandCode][cmd])

[cmd]: https://commandcode.ai/

# git
- Never run `git commit` — the user does commits manually and tests first. Confidence: 0.85

# odoo
- Use declarative XML view inheritance (like sales views) over direct DB manipulation. Follow Odoo best practices. Confidence: 0.70
- In QWeb templates, format monetary amounts using t-options="{'widget': 'monetary', 'display_currency': currency_var}" — never use format_amount() which doesn't exist in QWeb context. Confidence: 0.70
- In Odoo 19 QWeb xpath expressions, use hasclass('class-name') instead of contains(@class, 'class-name') for class-based element selection — Odoo flags contains(@class) as error-prone. Confidence: 0.65
- When using Odoo 19's patch() on an OWL component, prefer super.method(...) over capturing BaseClass.prototype.method — patch() sets up the prototype chain via Object.setPrototypeOf, so super resolves correctly through all patches. Capturing the method before patching breaks when multiple modules patch the same method. Confidence: 0.80
- When overriding Odoo model methods that the core framework calls (like _prepare_account_move_line), always maintain the original method signature exactly — changing parameter names or removing parameters that the core passes positionally will cause TypeError on other servers. Match the parent class signature precisely. Confidence: 0.70

