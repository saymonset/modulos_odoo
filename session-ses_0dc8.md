# New session - 2026-07-02T15:41:12.686Z

**Session ID:** ses_0dc823b98ffec4Lpl7plt735fH
**Created:** 7/2/2026, 5:41:12 PM
**Updated:** 7/2/2026, 5:41:56 PM

---

## User

puedes analizar este modulo y dime que hereda, que hace: /home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela

---

## Assistant (Plan · DeepSeek V4 Flash Free · 5.8s)

_Thinking:_

The user wants me to analyze a module and explain what it inherits and what it does. I should explore the module structure first.

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela</path>
<type>directory</type>
<entries>
__init__.py
__manifest__.py
__pycache__/
controllers/
data/
hooks.py
migrations/
models/
README.md
security/
services/
static/
tests/
uses_cases/
views/

(15 entries)
</entries>
```

---

## Assistant (Plan · DeepSeek V4 Flash Free · 6.4s)

_Thinking:_

Let me explore the module structure more deeply - read the manifest, models, controllers, etc.

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/__manifest__.py"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/__manifest__.py</path>
<type>file</type>
<content>
1: {
2:     'name': 'BCV Rate Update for Venezuela',
3:     'summary': 'Actualización automática de tasa BCV para Venezuela',
4:     'description': """
5:         Obtiene diariamente la tasa de cambio oficial del BCV y actualiza
6:         la moneda VES en Odoo.
7:     """,
8:     'version': '19.0.1.0.1',
9:     'category': 'Sales/Point of Sale',
10:     'author': 'Simon Alberto Rodriguez Pacheco',
11:     'website': 'https://github.com/simonrodriguezpacheco',
12:     'maintainer': 'Simon Alberto Rodriguez Pacheco',
13:     'license': 'LGPL-3',
14:     #'website_sale', 'base_address_city', 'contacts'
15:     'depends': [
16:         'base',
17:         'web',
18:         'sale_management',
19:         'account',          # Contabilidad base
20:         'stock',            # Inventario
21:         'point_of_sale',
22:         'website_sale', 
23:         'contacts',
24:         'payment',
25:         'whatsapp_cloud_integration',
26:         'currency_rate_update_base',
27:         'currency_rate_update_venezuela',
28:     ],
29: 
30:     'external_dependencies': {
31:         'python': ['requests', 'beautifulsoup4'],
32:     },
33:     
34:     'data': [
35:         'security/ir.model.access.csv',
36:         'data/res_bank_data.xml',
37:         'views/res_currency_views.xml',
38:         'views/sale_order_tree_debug.xml',
39:         'views/sale_order_views.xml',
40:         'views/website_cart_usd.xml',
41:         'views/payment_attachment_templates.xml',
42:         'views/payment_provider_views.xml',
43:         'views/res_company_views.xml',
44:         # 'views/website_sale_templates.xml',
45:         # 'views/invoice_report_templates.xml',
46:         'views/payment_templates_inherit.xml',
47:         'views/product_views.xml',
48:         'data/ir_cron_data.xml',
49:     ],
50:     
51:     'assets': {
52:         'point_of_sale.assets': [
53:             'bcv_rate_update_venezuela/static/src/css/payment_proof_component.css',
54:             'bcv_rate_update_venezuela/static/src/js/payment_proof_component.js',
55:             'bcv_rate_update_venezuela/static/src/xml/payment_proof_component.xml',
56:             'bcv_rate_update_venezuela/static/src/css/address_autofill.css',
57:             'bcv_rate_update_venezuela/static/src/js/address_autofill.js',
58:             'bcv_rate_update_venezuela/static/src/xml/address_autofill.xml',
59:         ],
60:         'web.assets_backend': [
61:             'bcv_rate_update_venezuela/static/src/css/payment_proof_component.css',
62:             'bcv_rate_update_venezuela/static/src/js/address_autofill.js',
63:         ],
64:          "web.assets_frontend": [
65:             'bcv_rate_update_venezuela/static/src/css/payment_proof_component.css',
66:             'bcv_rate_update_venezuela/static/src/js/payment_proof_component.js',
67:             'bcv_rate_update_venezuela/static/src/xml/payment_proof_component.xml',
68:             'bcv_rate_update_venezuela/static/src/css/address_autofill.css',
69:             'bcv_rate_update_venezuela/static/src/js/address_autofill.js',
70:             'bcv_rate_update_venezuela/static/src/xml/address_autofill.xml',
71:         ],
72:     },
73:     
74:     'application': False,
75:     'installable': True,
76:     'auto_install': False,
77:     'post_init_hook': '_post_init_hook',
78:     'uninstall_hook': '_uninstall_cleanup',
79:     'images': [
80:         'bcv_rate_update_venezuela/static/description/icon.png'
81:     ],
82: }

(End of file - total 82 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models</path>
<type>directory</type>
<entries>
__init__.py
__pycache__/
account_move_line.py
payment_provider.py
product_template.py
res_company.py
res_currency_rate.py
sale_order_line.py
sale_order.py
website_cart_usd.py
whatsapp_history_extension.py

(11 entries)
</entries>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/controllers"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/controllers</path>
<type>directory</type>
<entries>
__init__.py
__pycache__/
address_autofill.py
payment_custom_override.py
payment_validation.py
website_sale_attachment.py

(6 entries)
</entries>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/views"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/views</path>
<type>directory</type>
<entries>
invoice_report_templates.xml
payment_attachment_templates.xml
payment_provider_views.xml
payment_templates_inherit.xml
product_views.xml
res_company_views.xml
res_currency_views.xml
sale_order_tree_debug.xml
sale_order_views.xml
website_cart_usd.xml
website_sale_templates.xml

(11 entries)
</entries>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/services"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/services</path>
<type>directory</type>
<entries>
__init__.py
__pycache__/
whatsapp_service.py

(3 entries)
</entries>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/data"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/data</path>
<type>directory</type>
<entries>
ir_cron_data.xml
res_bank_data.xml

(2 entries)
</entries>
```

---

## Assistant (Plan · DeepSeek V4 Flash Free · 7.7s)

_Thinking:_

Let me read the models to understand what the module does.

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/__init__.py"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/__init__.py</path>
<type>file</type>
<content>
1: # -*- coding: utf-8 -*-
2: from . import res_currency_rate
3: from . import sale_order
4: from . import sale_order_line
5: from . import account_move_line
6: from . import website_cart_usd
7: from . import payment_provider
8: from . import whatsapp_history_extension
9: from . import res_company
10: from . import product_template

(End of file - total 10 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/res_currency_rate.py"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/res_currency_rate.py</path>
<type>file</type>
<content>
1: import logging
2: from odoo import models, fields, api, _
3: 
4: _logger = logging.getLogger(__name__)
5: 
6: class ResCurrencyRate(models.Model):
7:     _inherit = 'res.currency.rate'
8: 
9:     # Keep these fields for backward compatibility with views
10:     is_bcv_rate = fields.Boolean('Tasa BCV', default=False)
11:     source = fields.Selection([
12:         ('bcv', 'BCV Oficial'),
13:         ('parallel', 'Paralelo'),
14:         ('other', 'Otra Fuente'),
15:     ], string='Fuente', default='other')
16: 
17:     bcv_rate_value = fields.Float(
18:         'Tasa BCV (1 USD = X VES)',
19:         digits=(12, 2),
20:         help="Valor original publicado por BCV (1 USD = este valor en VES)"
21:     )
22: 
23:     is_bcv_editable = fields.Boolean(
24:         compute='_compute_is_bcv_editable',
25:         store=False,
26:     )
27: 
28:     @api.depends('currency_id')
29:     def _compute_is_bcv_editable(self):
30:         for rec in self:
31:             rec.is_bcv_editable = (rec.currency_id.name == 'VES')
32: 
33:     @api.model
34:     def create(self, vals):
35:         rate = super().create(vals)
36:         if rate.currency_id.name == 'VES':
37:             _logger.info("Nueva tasa VES creada. Recalculando precios desde USD...")
38:             self.env['product.template']._recalculate_ves_prices_from_usd()
39:         return rate
40: 
41:     def write(self, vals):
42:         before_rates = {r.id: r.rate for r in self}
43:         res = super().write(vals)
44:         for rate in self:
45:             if rate.currency_id.name == 'VES' and before_rates.get(rate.id) != rate.rate:
46:                 if 'rate' in vals or 'original_value' in vals:
47:                     _logger.info("Tasa VES modificada. Recalculando precios desde USD...")
48:                     self.env['product.template']._recalculate_ves_prices_from_usd()
49:                     break
50:         return res

(End of file - total 50 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/res_company.py"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/res_company.py</path>
<type>file</type>
<content>
1: from odoo import fields, models
2: 
3: class ResCompany(models.Model):
4:     _inherit = 'res.company'
5: 
6:     schedule_info = fields.Char(string="Horario de Atención", default="Abierto - Cierra a las 7:00 p.m.")

(End of file - total 6 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/sale_order.py"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/sale_order.py</path>
<type>file</type>
<content>
1: from odoo import models, fields, api, _
2: from odoo.exceptions import UserError
3: from odoo.http import request
4: import logging
5: 
6: _logger = logging.getLogger(__name__)
7: 
8: 
9: class SaleOrder(models.Model):
10:     _inherit = 'sale.order'
11: 
12:     payment_proof = fields.Binary('Comprobante de pago', attachment=True)
13:     payment_proof_filename = fields.Char('Nombre del archivo')
14:     payment_date = fields.Date('Fecha de pago')
15:     payment_method = fields.Selection([
16:         ('transfer', 'Transferencia'),
17:         ('movil', 'Pago móvil'),
18:         ('other', 'Otro'),
19:     ], string='Forma de pago', default='movil')
20:     bank_origin = fields.Char('Banco origen')
21:     bank_destination = fields.Char('Banco destino', default='N/A')
22:     reference = fields.Char('Referencia')
23:     amount_vef = fields.Float('Monto en bolívares', digits=(12, 2))
24:     exchange_rate = fields.Float('Tasa de cambio', digits=(12, 2))
25:     amount_usd = fields.Float('Monto USD', digits=(12, 2))
26: 
27:     currency_aux = fields.Many2one('res.currency', string='Moneda Auxiliar USD', compute='_compute_currency_aux', store=True)
28:     amount_total_usd = fields.Monetary(string='Total USD (BCV)', currency_field='currency_aux', compute='_compute_amount_total_usd', store=True)
29:     whatsapp_sent = fields.Boolean(string="WhatsApp enviado", default=False)
30: 
31:     @api.depends('order_line.price_subtotal_usd_bcv')
32:     def _compute_amount_total_usd(self):
33:         for order in self:
34:             order.amount_total_usd = sum(line.price_subtotal_usd_bcv for line in order.order_line)
35: 
36:     @api.depends('currency_id')
37:     def _compute_currency_aux(self):
38:         usd = self.env.ref('base.USD', raise_if_not_found=False)
39:         for order in self:
40:             order.currency_aux = usd
41: 
42:     # ------------------------------------------------------------
43:     # GUARDAR DATOS DEL COMPROBANTE (desde frontend)
44:     # ------------------------------------------------------------
45:     def action_save_payment_data(self, payment_data):
46:         _logger.info(f"*** SALVANDO: Datos de pago para orden {self.name}")
47:         self.sudo().write({
48:             'payment_date': payment_data.get('payment_date'),
49:             'payment_method': payment_data.get('payment_method'),
50:             'bank_origin': payment_data.get('bank_origin'),
51:             'bank_destination': payment_data.get('bank_destination', 'N/A'),
52:             'reference': payment_data.get('reference'),
53:             'amount_vef': float(payment_data.get('amount_vef', 0)),
54:             'exchange_rate': float(payment_data.get('exchange_rate', 0)),
55:             'amount_usd': float(payment_data.get('amount_usd', 0)),
56:         })
57:         return True
58: 
59:     # ------------------------------------------------------------
60:     # VALIDACIÓN DE CAMPOS OBLIGATORIOS
61:     # ------------------------------------------------------------
62:     def validate_payment_required_fields(self):
63:         _logger.info(f"*** VALIDANDO: {len(self)} orden(es)")
64:         for order in self:
65:             if order.payment_method in ['transfer', 'movil']:
66:                 if not order.reference:
67:                     raise UserError(_('✏️ Falta la referencia del pago. Por favor, indique el número de referencia de su transferencia.'))
68:                 if not order.bank_origin:
69:                     raise UserError(_('🏦 Falta el banco origen. Seleccione desde qué banco realiza la transferencia.'))
70:                 if not order.bank_destination or order.bank_destination == 'N/A':
71:                     raise UserError(_('🏦 Falta el banco destino. Seleccione el banco al que depositará.'))
72:                 attachment = self.env['ir.attachment'].sudo().search([
73:                     ('res_model', '=', 'sale.order'),
74:                     ('res_id', '=', order.id),
75:                     ('description', '=', 'Comprobante de pago - Transferencia / Pago Móvil'),
76:                 ], limit=1)
77:                 if not attachment:
78:                     raise UserError(_('📎 Falta adjuntar el comprobante de pago. Por favor, suba la imagen o PDF del comprobante.'))
79:                 if order.amount_vef < (order.amount_total - 0.01):
80:                     raise UserError(_('💰 El monto pagado (%.2f Bs.) es menor al total de la orden (%.2f Bs.). Por favor, verifique el monto.'))
81:                 _logger.info(f"*** VALIDACIÓN EXITOSA para orden {order.name}")
82: 
83:     # ------------------------------------------------------------
84:     # CONFIRMACIÓN DE LA ORDEN (con procesamiento posterior)
85:     # ------------------------------------------------------------
86:     def action_confirm(self):
87:         _logger.info(f"*** CONFIRMANDO: action_confirm llamado con órdenes {self.ids}")
88:         if not self:
89:             tx = self.env['payment.transaction'].sudo().search([
90:                 ('reference', 'like', 'S%'),
91:                 ('state', 'in', ['pending', 'authorized']),
92:             ], order='id desc', limit=1)
93:             if tx and tx.sale_order_ids:
94:                 order = tx.sale_order_ids[0]
95:                 _logger.info(f"*** CONFIRMANDO: Orden recuperada desde transacción: {order.name}")
96:                 if request and hasattr(request, 'session') and 'payment_data' in request.session:
97:                     payment_data = request.session.pop('payment_data')
98:                     if payment_data.get('sale_order_id') == order.id:
99:                         order.action_save_payment_data(payment_data)
100:                 res = super(SaleOrder, order).action_confirm()
101:                 self._process_order_post_confirm(order)
102:                 return res
103:             else:
104:                 return self.env['sale.order']
105:         else:
106:             for order in self:
107:                 if request and hasattr(request, 'session') and 'payment_data' in request.session:
108:                     payment_data = request.session.pop('payment_data')
109:                     order.action_save_payment_data(payment_data)
110:             res = super().action_confirm()
111:             for order in self:
112:                 self._process_order_post_confirm(order)
113:             return res
114: 
115:     # ------------------------------------------------------------
116:     # PROCESAMIENTO POST-CONFIRMACIÓN (WhatsApp y otros)
117:     # ------------------------------------------------------------
118:     @staticmethod
119:     def _process_order_post_confirm(order):
120:         """Procesa una orden ya confirmada: guarda datos de pago (si no se hicieron antes) y envía WhatsApp."""
121:         _logger.info(f"*** POST-CONFIRMACIÓN: Procesando orden {order.name}")
122: 
123:         # Si aún no se guardaron los datos de pago (por ejemplo, porque no vinieron en la sesión),
124:         # intentamos recuperarlos nuevamente (esto es un respaldo).
125:         if not order.payment_date and request and hasattr(request, 'session') and 'payment_data' in request.session:
126:             payment_data = request.session.pop('payment_data')
127:             if payment_data.get('sale_order_id') == order.id:
128:                 order.action_save_payment_data(payment_data)
129:                 _logger.info(f"*** POST-CONFIRMACIÓN: Datos de pago guardados desde sesión para {order.name}")
130: 
131:         # Enviar WhatsApp solo si no se ha enviado antes y la orden está confirmada y el cliente tiene teléfono
132:         if not order.whatsapp_sent and order.state == 'sale' and order.partner_id.phone:
133:             _logger.info(f"*** POST-CONFIRMACIÓN: Intentando enviar WhatsApp para orden {order.name}")
134:             # Buscar el comprobante adjunto (para enviarlo como imagen si existe)
135:             attachment = order.env['ir.attachment'].sudo().search([
136:                 ('res_model', '=', 'sale.order'),
137:                 ('res_id', '=', order.id),
138:                 ('description', '=', 'Comprobante de pago - Transferencia / Pago Móvil'),
139:             ], limit=1)
140:             if attachment:
141:                 if 'whatsapp.service' in order.env.registry:
142:                     service = order.env['whatsapp.service']
143:                     result = service.sendWhatsappConfirmation(order)
144:                     if not result.get('success'):
145:                         _logger.error(f"*** POST-CONFIRMACIÓN: Fallo en WhatsApp para {order.name}: {result.get('message')}")
146:                     else:
147:                         order.write({'whatsapp_sent': True})
148:                         _logger.info(f"*** POST-CONFIRMACIÓN: WhatsApp enviado correctamente para {order.name}")
149:                 else:
150:                     _logger.info(f"*** POST-CONFIRMACIÓN: Módulo WhatsApp no instalado, saltando notificación para {order.name}")
151:             else:
152:                 _logger.warning(f"*** POST-CONFIRMACIÓN: No se encontró comprobante para orden {order.name}. WhatsApp NO enviado.")
153:         else:
154:             _logger.info(f"*** POST-CONFIRMACIÓN: No se cumplen condiciones para enviar WhatsApp a {order.name} (whatsapp_sent={order.whatsapp_sent}, state={order.state}, phone={order.partner_id.phone})")
155: 
156: 
157: # ------------------------------------------------------------
158: # HERENCIA DEL PROVEEDOR DE PAGO (validación extra)
159: # ------------------------------------------------------------
160: class PaymentProvider(models.Model):
161:     _inherit = 'payment.provider'
162: 
163:     def _get_processing_values(self, values):
164:         _logger.info(f"*** PAYMENT: _get_processing_values llamado para proveedor {self.code}")
165:         sale_order_id = values.get('sale_order_id')
166:         if sale_order_id:
167:             sale_order = self.env['sale.order'].browse(sale_order_id)
168:             if sale_order and sale_order.payment_method in ['transfer', 'movil']:
169:                 if not sale_order.reference and request and hasattr(request, 'session') and 'payment_data' in request.session:
170:                     payment_data = request.session.get('payment_data')
171:                     if payment_data and payment_data.get('sale_order_id') == sale_order_id:
172:                         sale_order.action_save_payment_data(payment_data)
173:         return super()._get_processing_values(values)

(End of file - total 173 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/sale_order_line.py"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/sale_order_line.py</path>
<type>file</type>
<content>
1: from odoo import models, fields, api
2: from odoo.tools.float_utils import float_round
3: 
4: class SaleOrderLine(models.Model):
5:     _inherit = 'sale.order.line'
6: 
7:     price_usd_bcv = fields.Float(
8:         string='Precio USD (BCV)',
9:         digits=(12, 2),
10:         compute='_compute_usd_bcv',
11:         store=True
12:     )
13:     
14:     price_subtotal_usd_bcv = fields.Float(
15:         string='Subtotal USD (BCV)',
16:         digits=(12, 2),
17:         compute='_compute_usd_bcv',
18:         store=True
19:     )
20: 
21:     rate_value = fields.Float(
22:         string='Tasa de Cambio (BCV)',
23:         digits=(12, 2),
24:         compute='_compute_usd_bcv',
25:         store=True
26:     )
27: 
28:     @api.depends('price_unit', 'product_uom_qty')
29:     def _compute_usd_bcv(self):
30:         for line in self:
31:             main_provider = self.env['currency.rate.provider'].sudo().search([
32:                 ('company_id', '=', line.order_id.company_id.id),
33:                 ('provider_type', '=', 'bcv'),
34:                 ('active', '=', True),
35:             ], limit=1)
36: 
37:             rate_val = 0.0
38:             if main_provider:
39:                 rate_val = main_provider.last_rate
40: 
41:             if not rate_val:
42:                 rate = self.env['res.currency.rate'].search([
43:                     ('currency_id.name', '=', 'USD'),
44:                     ('company_id', '=', line.order_id.company_id.id),
45:                 ], order='name desc', limit=1)
46:                 if rate:
47:                     rate_val = rate.original_value
48: 
49:             if not rate_val:
50:                 line.price_usd_bcv = 0.0
51:                 line.price_subtotal_usd_bcv = 0.0
52:                 line.rate_value = 0.0
53:                 continue
54: 
55:             line.rate_value = rate_val
56:             line.price_usd_bcv = float_round(line.price_unit / rate_val, precision_digits=2)
57:             line.price_subtotal_usd_bcv = float_round(line.price_usd_bcv * line.product_uom_qty, precision_digits=2)

(End of file - total 57 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/product_template.py"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/product_template.py</path>
<type>file</type>
<content>
1: from odoo import models, fields, api
2: from odoo.tools.float_utils import float_round
3: import logging
4: 
5: _logger = logging.getLogger(__name__)
6: 
7: 
8: class ProductTemplate(models.Model):
9:     _inherit = 'product.template'
10: 
11:     currency_usd_id = fields.Many2one(
12:         'res.currency',
13:         string='USD Currency',
14:         compute='_compute_currency_usd_id'
15:     )
16: 
17:     list_price_usd = fields.Float(
18:         string='Precio de Venta USD',
19:         digits=(12, 2)
20:     )
21: 
22:     def _compute_currency_usd_id(self):
23:         usd = self.env.ref('base.USD', raise_if_not_found=False)
24:         for template in self:
25:             template.currency_usd_id = usd
26: 
27:     @api.onchange('list_price')
28:     def _onchange_list_price(self):
29:         for template in self:
30:             rate = self._get_bcv_rate(template.company_id)
31:             if rate:
32:                 template.list_price_usd = float_round(template.list_price / rate, precision_digits=2)
33: 
34:     @api.onchange('list_price_usd')
35:     def _onchange_list_price_usd(self):
36:         for template in self:
37:             rate = self._get_bcv_rate(template.company_id)
38:             if rate:
39:                 template.list_price = float_round(template.list_price_usd * rate, precision_digits=2)
40: 
41:     @api.model_create_multi
42:     def create(self, vals_list):
43:         records = super().create(vals_list)
44:         if self.env.context.get('_skip_bcv_sync'):
45:             return records
46:         for record, vals in zip(records, vals_list):
47:             record._sync_usd_ves_values(vals)
48:         return records
49: 
50:     def write(self, vals):
51:         res = super().write(vals)
52:         if not self.env.context.get('_skip_bcv_sync'):
53:             self._sync_usd_ves_values(vals)
54:         return res
55: 
56:     def _sync_usd_ves_values(self, vals):
57:         if 'list_price_usd' in vals:
58:             for template in self:
59:                 rate = self._get_bcv_rate(template.company_id)
60:                 if rate:
61:                     template.with_context(_skip_bcv_sync=True).write({
62:                         'list_price': float_round(template.list_price_usd * rate, precision_digits=2),
63:                     })
64:         elif 'list_price' in vals:
65:             for template in self:
66:                 rate = self._get_bcv_rate(template.company_id)
67:                 if rate:
68:                     template.with_context(_skip_bcv_sync=True).write({
69:                         'list_price_usd': float_round(template.list_price / rate, precision_digits=2),
70:                     })
71: 
72:     @api.model
73:     def _get_bcv_rate(self, company):
74:         if not company:
75:             company = self.env.company
76:         main_provider = self.env['currency.rate.provider'].sudo().search([
77:             ('company_id', '=', company.id),
78:             ('provider_type', '=', 'bcv'),
79:             ('active', '=', True),
80:         ], limit=1)
81:         rate_val = 0.0
82:         if main_provider:
83:             rate_val = main_provider.last_rate
84:         if not rate_val:
85:             rate = self.env['res.currency.rate'].search([
86:                 ('currency_id.name', '=', 'USD'),
87:                 ('company_id', '=', company.id),
88:             ], order='name desc', limit=1)
89:             if rate:
90:                 rate_val = rate.original_value
91:         return rate_val or 1.0
92: 
93:     @api.model
94:     def _recalculate_ves_prices_from_usd(self):
95:         companies = self.env['res.company'].search([])
96:         for company in companies:
97:             rate = self._get_bcv_rate(company)
98:             if not rate or rate == 1.0:
99:                 continue
100:             templates = self.env['product.template'].search([
101:                 ('list_price_usd', '>', 0),
102:                 ('company_id', '=', company.id),
103:             ])
104:             for t in templates:
105:                 t.with_context(_skip_bcv_sync=True).write({
106:                     'list_price': float_round(t.list_price_usd * rate, precision_digits=2),
107:                 })
108:             attr_values = self.env['product.template.attribute.value'].search([
109:                 ('price_extra_usd', '!=', 0),
110:                 ('product_tmpl_id.company_id', '=', company.id),
111:             ])
112:             for a in attr_values:
113:                 a.with_context(_skip_bcv_sync=True).write({
114:                     'price_extra': a.price_extra_usd * rate,
115:                 })
116:         _logger.info("Precios VES recalculados desde USD para todas las compañías.")
117: 
118: 
119: class ProductProduct(models.Model):
120:     _inherit = 'product.product'
121: 
122:     currency_usd_id = fields.Many2one(
123:         'res.currency',
124:         string='USD Currency',
125:         compute='_compute_currency_usd_id'
126:     )
127: 
128:     lst_price_usd = fields.Float(
129:         string='Precio de Venta USD',
130:         digits=(12, 2)
131:     )
132: 
133:     def _compute_currency_usd_id(self):
134:         usd = self.env.ref('base.USD', raise_if_not_found=False)
135:         for rec in self:
136:             rec.currency_usd_id = usd
137: 
138:     @api.onchange('lst_price')
139:     def _onchange_lst_price(self):
140:         for rec in self:
141:             rate = self.env['product.template']._get_bcv_rate(rec.company_id)
142:             if rate:
143:                 rec.lst_price_usd = float_round(rec.lst_price / rate, precision_digits=2)
144: 
145:     @api.onchange('lst_price_usd')
146:     def _onchange_lst_price_usd(self):
147:         for rec in self:
148:             rate = self.env['product.template']._get_bcv_rate(rec.company_id)
149:             if rate:
150:                 rec.lst_price = float_round(rec.lst_price_usd * rate, precision_digits=2)
151: 
152:     @api.model_create_multi
153:     def create(self, vals_list):
154:         records = super().create(vals_list)
155:         if self.env.context.get('_skip_bcv_sync'):
156:             return records
157:         for record, vals in zip(records, vals_list):
158:             record._sync_usd_ves_values(vals)
159:         return records
160: 
161:     def write(self, vals):
162:         res = super().write(vals)
163:         if not self.env.context.get('_skip_bcv_sync'):
164:             self._sync_usd_ves_values(vals)
165:         return res
166: 
167:     def _sync_usd_ves_values(self, vals):
168:         if 'lst_price_usd' in vals:
169:             for rec in self:
170:                 rate = self.env['product.template']._get_bcv_rate(rec.company_id)
171:                 if rate:
172:                     rec.with_context(_skip_bcv_sync=True).write({
173:                         'lst_price': float_round(rec.lst_price_usd * rate, precision_digits=2),
174:                     })
175:         elif 'lst_price' in vals or 'list_price' in vals or 'price_extra' in vals:
176:             for rec in self:
177:                 rate = self.env['product.template']._get_bcv_rate(rec.company_id)
178:                 if rate:
179:                     rec.with_context(_skip_bcv_sync=True).write({
180:                         'lst_price_usd': float_round(rec.lst_price / rate, precision_digits=2),
181:                     })
182: 
183: 
184: class ProductTemplateAttributeValue(models.Model):
185:     _inherit = 'product.template.attribute.value'
186: 
187:     currency_usd_id = fields.Many2one(
188:         'res.currency',
189:         string='USD Currency',
190:         compute='_compute_currency_usd_id'
191:     )
192: 
193:     price_extra_usd = fields.Float(
194:         string='Precio Extra USD',
195:         digits=(12, 2)
196:     )
197: 
198:     def _compute_currency_usd_id(self):
199:         usd = self.env.ref('base.USD', raise_if_not_found=False)
200:         for rec in self:
201:             rec.currency_usd_id = usd
202: 
203:     @api.onchange('price_extra')
204:     def _onchange_price_extra(self):
205:         for rec in self:
206:             rate = self.env['product.template']._get_bcv_rate(rec.product_tmpl_id.company_id)
207:             if rate:
208:                 rec.price_extra_usd = float_round(rec.price_extra / rate, precision_digits=2)
209: 
210:     @api.onchange('price_extra_usd')
211:     def _onchange_price_extra_usd(self):
212:         for rec in self:
213:             rate = self.env['product.template']._get_bcv_rate(rec.product_tmpl_id.company_id)
214:             if rate:
215:                 rec.price_extra = float_round(rec.price_extra_usd * rate, precision_digits=2)
216: 
217:     @api.model_create_multi
218:     def create(self, vals_list):
219:         records = super().create(vals_list)
220:         if self.env.context.get('_skip_bcv_sync'):
221:             return records
222:         for record, vals in zip(records, vals_list):
223:             record._sync_usd_ves_values(vals)
224:         return records
225: 
226:     def write(self, vals):
227:         res = super().write(vals)
228:         if not self.env.context.get('_skip_bcv_sync'):
229:             self._sync_usd_ves_values(vals)
230:         return res
231: 
232:     def _sync_usd_ves_values(self, vals):
233:         if 'price_extra_usd' in vals:
234:             for rec in self:
235:                 rate = self.env['product.template']._get_bcv_rate(rec.product_tmpl_id.company_id)
236:                 if rate:
237:                     rec.with_context(_skip_bcv_sync=True).write({
238:                         'price_extra': float_round(rec.price_extra_usd * rate, precision_digits=2),
239:                     })
240:         elif 'price_extra' in vals:
241:             for rec in self:
242:                 rate = self.env['product.template']._get_bcv_rate(rec.product_tmpl_id.company_id)
243:                 if rate:
244:                     rec.with_context(_skip_bcv_sync=True).write({
245:                         'price_extra_usd': float_round(rec.price_extra / rate, precision_digits=2),
246:                     })

(End of file - total 246 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/account_move_line.py"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/account_move_line.py</path>
<type>file</type>
<content>
1: from odoo import models, fields, api
2: 
3: class AccountMoveLine(models.Model):
4:     _inherit = 'account.move.line'
5: 
6:     price_usd_bcv = fields.Float(
7:         string='Precio USD (BCV)',
8:         digits=(12, 2),
9:         readonly=True
10:     )
11: 
12:     bcv_rate_value = fields.Float(
13:         string='Tasa BCV',
14:         digits=(12, 2),
15:         readonly=True
16:     )
17: 
18:     @api.model
19:     def create(self, vals):
20:         line = super(AccountMoveLine, self).create(vals)
21:         # Copiar precio USD(BCV) si viene de la línea de venta
22:         if 'sale_line_ids' in vals and vals['sale_line_ids']:
23:             sale_line = self.env['sale.order.line'].browse(vals['sale_line_ids'][0][2][0])
24:             line.price_usd_bcv = sale_line.price_usd_bcv
25:             line.bcv_rate_value = sale_line.bcv_rate_value
26:         return line

(End of file - total 26 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/payment_provider.py"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/payment_provider.py</path>
<type>file</type>
<content>
1: from odoo import fields, models
2: 
3: class PaymentProvider(models.Model):
4:     _inherit = 'payment.provider'
5: 
6:     is_wire_transfer = fields.Boolean(string="Es transferencia bancaria")

(End of file - total 6 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/website_cart_usd.py"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/website_cart_usd.py</path>
<type>file</type>
<content>
1: from odoo import models, fields, api
2: 
3: class Website(models.Model):
4:     _inherit = 'website'
5: 
6:     def get_bcv_rate(self):
7:         """Retorna la tasa USD/VES actual (cuántos bolívares por 1 USD)"""
8:         # get_rate_info returns the 'rate' as display_val (original_value or rate)
9:         rate_info = self.get_rate_info(currency_name='USD')
10:         return rate_info.get('rate', 1.0)
11: 
12:     def get_conversion_factor_ves_to_usd(self):
13:         """
14:         Retorna el factor para convertir VES a USD (precio_VES * factor = precio_USD).
15:         """
16:         # Si la moneda base ya es USD, no hay factor de conversión (es 1.0)
17:         if self.company_id.currency_id.name == 'USD':
18:             return 1.0
19:             
20:         rate = self.get_bcv_rate()
21:         # Si la tasa es 1.0 o 0.0 y la moneda base no es USD, la tasa no es válida
22:         if rate and rate > 1.0:
23:             return 1.0 / rate
24:         return 0.0
25:     
26:     def get_bcv_rate_info(self):
27:         """
28:         Retorna un dict con la tasa BCV (1 USD = X VES).
29:         Mantenido por compatibilidad con plantillas existentes.
30:         """
31:         # Priorizar el proveedor marcado como "Main" o buscar USD
32:         info = self.get_rate_info(currency_name='USD')
33:         
34:         # Si no hay tasa de USD específica, intentamos obtener cualquier tasa activa (para otros países)
35:         if info.get('rate') == 1.0 and info.get('date') is None:
36:              info = self.get_rate_info()
37: 
38:         return info

(End of file - total 38 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/whatsapp_history_extension.py"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/whatsapp_history_extension.py</path>
<type>file</type>
<content>
1: from odoo import fields, models
2: 
3: class WhatsappHistoryExtended(models.Model):
4:     _inherit = 'whatsapp.history'
5: 
6:     sale_order_id = fields.Many2one('sale.order', string='Orden de venta', index=True) 

(End of file - total 6 lines)
</content>
```

---

## Assistant (Plan · DeepSeek V4 Flash Free · 6.2s)

_Thinking:_

Now let me also read the controllers, hooks, and services to understand the full picture.

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/hooks.py"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/hooks.py</path>
<type>file</type>
<content>
1: # -*- coding: utf-8 -*-
2: from odoo.tools.float_utils import float_round
3: import logging
4: 
5: _logger = logging.getLogger(__name__)
6: 
7: def _clean_orphan_views(env):
8:     views = env['ir.ui.view'].sudo().search([
9:         ('name', 'in', ['sale.order.form.usd.total', 'sale.order.form.payment.proof']),
10:     ])
11:     orphan_ids = []
12:     for view in views:
13:         ext_id = view.get_external_id()
14:         if not ext_id.get(view.id):
15:             orphan_ids.append(view.id)
16:     if orphan_ids:
17:         env['ir.ui.view'].sudo().browse(orphan_ids).unlink()
18:     _logger.info("Vistas huérfanas eliminadas correctamente (post-install).")
19: 
20: def _uninstall_cleanup(env):
21:     data = env['ir.model.data'].sudo().search([
22:         ('model', '=', 'ir.ui.view'),
23:         ('module', '=', 'bcv_rate_update_venezuela'),
24:         ('name', 'in', ['sale.order.form.usd.total', 'sale.order.form.payment.proof']),
25:     ])
26:     view_ids = data.mapped('res_id')
27:     if view_ids:
28:         env['ir.ui.view'].sudo().browse(view_ids).unlink()
29:     _logger.info("Vistas del módulo eliminadas durante la desinstalación.")
30: 
31: def _populate_initial_usd_prices(env):
32:     rate = env['product.template']._get_bcv_rate(env.company)
33:     if not rate or rate == 1.0:
34:         _logger.warning("No se pudo obtener tasa BCV para poblar precios USD iniciales.")
35:         return
36:     templates = env['product.template'].search([
37:         ('list_price', '>', 0),
38:         ('list_price_usd', '=', 0),
39:     ])
40:     count = 0
41:     for t in templates:
42:         t.with_context(_skip_bcv_sync=True).write({'list_price_usd': float_round(t.list_price / rate, precision_digits=2)})
43:         count += 1
44:     _logger.info("Precios USD poblados para %s plantillas.", count)
45:     variants = env['product.product'].search([
46:         ('product_tmpl_id.list_price', '>', 0),
47:         ('lst_price_usd', '=', 0),
48:     ])
49:     count_var = 0
50:     for v in variants:
51:         v.with_context(_skip_bcv_sync=True).write({'lst_price_usd': float_round(v.lst_price / rate, precision_digits=2)})
52:         count_var += 1
53:     _logger.info("Precios USD poblados para %s variantes.", count_var)
54:     attr_values = env['product.template.attribute.value'].search([
55:         ('price_extra', '!=', 0),
56:         ('price_extra_usd', '=', 0),
57:     ])
58:     count_attr = 0
59:     for a in attr_values:
60:         a.with_context(_skip_bcv_sync=True).write({'price_extra_usd': float_round(a.price_extra / rate, precision_digits=2)})
61:         count_attr += 1
62:     _logger.info("Precios extra USD poblados para %s atributos.", count_attr)
63: 
64: def _post_init_hook(env):
65:     _clean_orphan_views(env)
66:     _populate_initial_usd_prices(env)

(End of file - total 66 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/controllers/__init__.py"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/controllers/__init__.py</path>
<type>file</type>
<content>
1: # -*- coding: utf-8 -*-
2: from . import website_sale_attachment
3: from . import address_autofill
4: from . import payment_validation
5: from . import payment_custom_override

(End of file - total 5 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/controllers/address_autofill.py"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/controllers/address_autofill.py</path>
<type>file</type>
<content>
1: from odoo import http
2: from odoo.http import request
3: 
4: 
5: class AddressAutofill(http.Controller):
6: 
7:     @http.route('/shop/get_company_address_data', type='json', auth='public', methods=['POST'], website=True, csrf=False)
8:     def get_company_address_data(self):
9:         """Retorna datos por defecto de la compañía (Venezuela fallback)"""
10:         company = request.env.company
11:         venezuela = request.env['res.country'].search([('code', '=', 'VE')], limit=1)
12:         default_country_id = venezuela.id if venezuela else False
13: 
14:         return {
15:             'country_id': company.country_id.id if company.country_id else default_country_id,
16:             'city': company.city or '',
17:             'zip': company.zip or '',
18:         }
19: 
20:     @http.route('/shop/search_partner_by_email_or_phone', type='json', auth='public', methods=['POST'], website=True, csrf=False)
21:     def search_partner_by_email_or_phone(self, email='', phone='', **kwargs):
22:         """
23:         Busca contacto por email o teléfono.
24:         """
25:         Partner = request.env['res.partner'].sudo()
26:         domain = []
27: 
28:         email = (email or '').strip()
29:         phone = (phone or '').strip()
30: 
31:         if email and '@' in email and len(email) >= 5:
32:             domain.append(('email', 'ilike', email))
33: 
34:         if phone and len(phone) >= 5:
35:             phone_clean = ''.join(filter(str.isdigit, phone))
36:             if phone_clean:
37:                 domain.append(('phone', 'ilike', phone_clean))
38: 
39:         if not domain:
40:             return {}
41: 
42:         # Buscar primero por email (más preciso), luego por teléfono
43:         partner = Partner.search(domain, limit=1, order='email desc')  
44:         
45:         if not partner:
46:             return {}
47: 
48:         return {
49:             'name': partner.name or '',
50:             'phone': partner.phone or '',
51:             'email': partner.email or '',
52:             'street': partner.street or '',
53:             'street2': partner.street2 or '',
54:             'city': partner.city or '',
55:             'zip': partner.zip or '',
56:             'country_id': partner.country_id.id if partner.country_id else False,
57:             'state_id': partner.state_id.id if partner.state_id else False,
58:             'vat': partner.vat or '',
59:         }

(End of file - total 59 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/controllers/payment_custom_override.py"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/controllers/payment_custom_override.py</path>
<type>file</type>
<content>
1: from odoo import http
2: from odoo.http import request
3: import logging
4: import re
5: 
6: _logger = logging.getLogger(__name__)
7: 
8: 
9: class PaymentCustomOverride(http.Controller):
10: 
11:     @http.route('/payment/custom/process', type='http', auth='public', methods=['POST'], csrf=False)
12:     def custom_process(self, **post):
13:         _logger.info("=" * 80)
14:         _logger.info("*** PAYMENT: INICIO - Interceptando /payment/custom/process")
15:         reference = post.get('reference')
16:         if not reference:
17:             _logger.warning("*** PAYMENT: No se recibió referencia")
18:             return request.redirect('/shop/payment?error=Falta+la+referencia+del+pago')
19: 
20:         # Limpiar sufijo numérico (ej: "S00118-3" -> "S00118")
21:         clean_reference = re.sub(r'-\d+$', '', reference)
22:         _logger.info(f"*** PAYMENT: Referencia original: {reference}, limpia: {clean_reference}")
23: 
24:         # Buscar la orden de venta
25:         sale_order = request.env['sale.order'].sudo().search([('name', '=', clean_reference)], limit=1)
26:         if not sale_order:
27:             _logger.warning(f"No se encontró orden con referencia {clean_reference}")
28:             return request.redirect('/shop/payment?error=No+se+encontró+la+orden+de+pago')
29: 
30:         _logger.info(f"*** PAYMENT: Orden encontrada: {sale_order.name} (ID {sale_order.id})")
31: 
32:         # Recuperar datos de sesión (guardados durante la subida del comprobante)
33:         if 'payment_data' in request.session:
34:             payment_data = request.session.pop('payment_data')
35:             _logger.info(f"*** PAYMENT: Datos de sesión recuperados: {payment_data}")
36:             if payment_data.get('sale_order_id') == sale_order.id:
37:                 sale_order.action_save_payment_data(payment_data)
38:                 _logger.info(f"*** PAYMENT: Datos guardados en la orden")
39:             else:
40:                 _logger.warning(f"El sale_order_id de la sesión no coincide")
41:         else:
42:             _logger.warning("*** PAYMENT: No hay datos de pago en la sesión")
43: 
44:         # ================================================================
45:         # 1. VERIFICAR Y LIMPIAR TRANSACCIONES EXISTENTES
46:         # ================================================================
47:         existing_tx = request.env['payment.transaction'].sudo().search([
48:             ('reference', '=', reference)
49:         ], limit=1)
50:         if existing_tx:
51:             _logger.info(f"*** PAYMENT: Ya existe una transacción con referencia {reference}. Estado actual: {existing_tx.state}")
52:             if existing_tx.state in ['pending', 'authorized', 'done']:
53:                 # Estado válido, redirigir a la página de estado de pago
54:                 return request.redirect('/payment/status')
55:             else:
56:                 # Estado 'draft' o 'cancel' - eliminar para crear una nueva
57:                 _logger.info(f"*** PAYMENT: Eliminando transacción en estado {existing_tx.state} para crear una nueva")
58:                 existing_tx.sudo().unlink()
59:                 _logger.info("*** PAYMENT: Transacción eliminada correctamente")
60: 
61:         # ================================================================
62:         # 2. OBTENER PROVEEDOR Y MÉTODO DE PAGO
63:         # ================================================================
64:         provider = request.env['payment.provider'].sudo().search([
65:             ('code', '=', 'custom')
66:         ], limit=1)
67:         if not provider:
68:             provider = request.env['payment.provider'].sudo().search([
69:                 ('is_wire_transfer', '=', True)
70:             ], limit=1)
71:         if not provider:
72:             _logger.error("No se encontró proveedor de pago")
73:             return request.redirect('/shop/payment?error=Error+en+la+configuración+de+pago')
74:         _logger.info(f"*** PAYMENT: Proveedor encontrado: ID={provider.id}, code={provider.code}")
75: 
76:         # Obtener método de pago asociado al proveedor (campo many2many 'provider_ids')
77:         payment_method = request.env['payment.method'].sudo().search([
78:             ('provider_ids', 'in', provider.id)
79:         ], limit=1)
80:         if not payment_method:
81:             # Fallback: tomar cualquier método de pago activo
82:             payment_method = request.env['payment.method'].sudo().search([], limit=1)
83:         if not payment_method:
84:             _logger.error("No se encontró método de pago")
85:             return request.redirect('/shop/payment?error=Error+en+el+método+de+pago')
86:         _logger.info(f"*** PAYMENT: Método de pago: ID={payment_method.id}, name={payment_method.name}")
87: 
88:         # ================================================================
89:         # 2b. GARANTIZAR payment_method_line_id PARA EVITAR ERROR DE POST-PROCESO
90:         # ================================================================
91:         if not provider.journal_id:
92:             journal = request.env['account.journal'].sudo().search([
93:                 ('company_id', '=', provider.company_id.id),
94:                 ('type', '=', 'bank'),
95:             ], limit=1)
96:             if journal:
97:                 provider.sudo().write({'journal_id': journal.id})
98:             else:
99:                 _logger.error("*** PAYMENT: No se encontró diario bancario para el proveedor")
100:                 return request.redirect('/shop/payment?error=Error+en+la+configuración+del+diario+de+pago')
101: 
102:         journal = provider.journal_id
103:         payment_method_line = journal.inbound_payment_method_line_ids\
104:             .filtered(lambda l: l.payment_provider_id == provider.id)
105:         if not payment_method_line:
106:             payment_method_line = journal.inbound_payment_method_line_ids\
107:                 .filtered(lambda l: not l.payment_provider_id)[:1]
108:         if not payment_method_line:
109:             manual_method = request.env['account.payment.method'].sudo().search([
110:                 ('payment_type', '=', 'inbound'),
111:                 ('code', '=', 'manual'),
112:             ], limit=1)
113:             if manual_method:
114:                 payment_method_line = request.env['account.payment.method.line'].sudo().create({
115:                     'payment_method_id': manual_method.id,
116:                     'journal_id': journal.id,
117:                     'payment_provider_id': provider.id,
118:                 })
119:         if not payment_method_line:
120:             _logger.error("*** PAYMENT: No se pudo crear payment_method_line para el proveedor")
121:             return request.redirect('/shop/payment?error=Error+en+la+configuración+de+línea+de+pago')
122: 
123:         # ================================================================
124:         # 3. CREAR NUEVA TRANSACCIÓN
125:         # ================================================================
126:         tx_values = {
127:             'reference': reference,
128:             'amount': sale_order.amount_total,
129:             'currency_id': sale_order.currency_id.id,
130:             'partner_id': sale_order.partner_id.id,
131:             'provider_id': provider.id,
132:             'payment_method_id': payment_method.id,
133:             'state': 'pending',
134:             'is_live': True,
135:         }
136:         _logger.info(f"*** PAYMENT: Creando transacción con valores: {tx_values}")
137:         try:
138:             tx = request.env['payment.transaction'].sudo().create(tx_values)
139:             _logger.info(f"*** PAYMENT: Transacción creada con ID {tx.id}")
140:             sale_order.action_confirm()
141:             _logger.info(f"*** PAYMENT: Orden confirmada correctamente: {sale_order.name} (state={sale_order.state})")
142:             tx.sudo().write({'state': 'done'})
143:             _logger.info(f"*** PAYMENT: Transacción {tx.id} marcada como done")
144:             return request.redirect('/payment/status')
145:         except Exception as e:
146:             _logger.exception("*** PAYMENT: Error al procesar el pago")
147:             return request.redirect(f'/shop/payment?error=Error+al+procesar+el+pago:+{str(e)}')

(End of file - total 147 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/controllers/payment_validation.py"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/controllers/payment_validation.py</path>
<type>file</type>
<content>
1: from odoo import http
2: from odoo.http import request
3: from odoo.exceptions import UserError
4: import json
5: import logging
6: 
7: _logger = logging.getLogger(__name__)
8: 
9: 
10: class PaymentDataController(http.Controller):
11: 
12:     @http.route('/payment/validate_and_save', type='json', auth='public', methods=['POST'])
13:     def validate_and_save_payment_data(self, **post):
14:         _logger.info(">>> PAYMENT: /payment/validate_and_save called")
15:         data = json.loads(request.httprequest.data) if request.httprequest.data else post
16:         sale_order_id = data.get('sale_order_id')
17:         if not sale_order_id:
18:             return {'error': 'No se encontró la orden'}
19:         sale_order = request.env['sale.order'].sudo().browse(sale_order_id)
20:         if not sale_order:
21:             return {'error': 'Orden no válida'}
22:         _logger.info(f">>> PAYMENT: Saving data for order {sale_order.name}")
23:         sale_order.action_save_payment_data(data)
24:         try:
25:             sale_order.validate_payment_required_fields()
26:             _logger.info(">>> PAYMENT: Validation passed")
27:         except UserError as e:
28:             _logger.info(f">>> PAYMENT: Validation failed: {str(e)}")
29:             return {'error': str(e)}
30:         return {'success': True}

(End of file - total 30 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/controllers/website_sale_attachment.py"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/controllers/website_sale_attachment.py</path>
<type>file</type>
<content>
1: from odoo import http
2: from odoo.http import request
3: from odoo.addons.website_sale.controllers.main import WebsiteSale
4: from markupsafe import Markup
5: import base64
6: import logging
7: 
8: _logger = logging.getLogger(__name__)
9: 
10: 
11: class WebsiteSaleAttachment(WebsiteSale):
12: 
13:     @http.route('/shop/get_partner_data', type='json', auth='public', website=True)
14:     def get_partner_data(self, email=None, phone=None):
15:         if not email and not phone:
16:             return {}
17:         domain = []
18:         if email:
19:             domain.append(('email', '=', email))
20:         if phone:
21:             domain.append(('phone', '=', phone))
22:         if not domain:
23:             return {}
24:         search_domain = ['|'] * (len(domain) - 1) + domain if len(domain) > 1 else domain
25:         partner = request.env['res.partner'].sudo().search(search_domain, limit=1)
26:         if partner:
27:             if partner.user_ids or partner.id == request.website.partner_id.id:
28:                 _logger.info("Partner found but has users or is public. Skipping auto-fill.")
29:                 return {'has_user': True}
30:             return {
31:                 'name': partner.name,
32:                 'street': partner.street,
33:                 'street2': partner.street2,
34:                 'city': partner.city,
35:                 'zip': partner.zip,
36:                 'country_id': partner.country_id.id,
37:                 'state_id': partner.state_id.id,
38:                 'phone': partner.phone,
39:                 'email': partner.email,
40:                 'vat': partner.vat,
41:             }
42:         return {}
43: 
44:     @http.route(['/shop/address/submit'], type='http', methods=['POST'], auth='public', website=True, sitemap=False)
45:     def shop_address_submit(self, partner_id=None, **form_data):
46:         _logger.info(f"=== shop_address_submit override (partner_id: {partner_id}) ===")
47:         if not partner_id and request.cart and request.cart._is_anonymous_cart():
48:             email = form_data.get('email')
49:             phone = form_data.get('phone')
50:             domain = []
51:             if email:
52:                 domain.append(('email', '=', email))
53:             if phone:
54:                 domain.append(('phone', '=', phone))
55:             if domain:
56:                 search_domain = ['|'] * (len(domain) - 1) + domain if len(domain) > 1 else domain
57:                 existing_partner = request.env['res.partner'].sudo().search(search_domain + [('user_ids', '=', False)], limit=1)
58:                 if existing_partner:
59:                     _logger.info(f"Vínculando orden a partner existente ID {existing_partner.id}")
60:                     partner_id = existing_partner.id
61:         return super().shop_address_submit(partner_id=partner_id, **form_data)
62: 
63:     @http.route('/payment_proof/get_order_total_and_rate', type='json', auth='public', csrf=False)
64:     def get_order_total_and_rate(self):
65:         _logger.info("=== get_order_total_and_rate called ===")
66:         try:
67:             sale_order_id = request.session.get('sale_order_id') or request.session.get('sale_last_order_id')
68:             if not sale_order_id:
69:                 return {'error': 'No hay orden activa'}
70:             order = request.env['sale.order'].sudo().browse(int(sale_order_id)).exists()
71:             if not order:
72:                 return {'error': 'No se encontró la orden'}
73:             amount_vef = order.amount_total
74:             rate_info = request.website.get_rate_info()
75:             exchange_rate = rate_info.get('rate', 0.0)
76:             if exchange_rate and exchange_rate > 1.0:
77:                 amount_usd = amount_vef / exchange_rate
78:                 return {
79:                     'amount_vef': amount_vef,
80:                     'exchange_rate': exchange_rate,
81:                     'rate_date': rate_info.get('date_formatted', ''),
82:                     'amount_usd': amount_usd,
83:                 }
84:             else:
85:                 return {
86:                     'amount_vef': amount_vef,
87:                     'exchange_rate': 0.0,
88:                     'rate_date': '',
89:                     'amount_usd': 0.0,
90:                     'error': 'Tasa de cambio no disponible temporalmente'
91:                 }
92:         except Exception as e:
93:             _logger.error(f"Error en get_order_total_and_rate: {str(e)}", exc_info=True)
94:             return {'error': f'Error interno: {str(e)}'}
95: 
96:     # -------------------------------------------------------------------------
97:     # Ruta para subir comprobante (POST) - CORREGIDA con sale_order_id en payment_data
98:     # -------------------------------------------------------------------------
99:     @http.route(['/shop/upload_payment_proof'], type='http', methods=['POST'], auth='public', website=True, csrf=False)
100:     def upload_payment_proof(self, **post):
101:         file = request.httprequest.files.get('payment_proof_file')
102:         if not file or not file.filename:
103:             return request.make_response('ERROR', status=400)
104: 
105:         sale_order_id = request.session.get('sale_order_id') or request.session.get('sale_last_order_id')
106:         order = None
107:         if sale_order_id:
108:             order = request.env['sale.order'].sudo().browse(int(sale_order_id)).exists()
109: 
110:         file_data = file.read()
111:         file_base64 = base64.b64encode(file_data).decode('utf-8')
112:         filename = file.filename
113: 
114:         mimetype = file.content_type
115:         if not mimetype or mimetype == 'application/octet-stream':
116:             ext = filename.split('.')[-1].lower()
117:             if ext in ('jpg', 'jpeg'):
118:                 mimetype = 'image/jpeg'
119:             elif ext == 'png':
120:                 mimetype = 'image/png'
121:             elif ext == 'pdf':
122:                 mimetype = 'application/pdf'
123:             else:
124:                 mimetype = 'application/octet-stream'
125: 
126:         # IMPORTANTE: incluir sale_order_id
127:         payment_data = {
128:             'sale_order_id': sale_order_id,
129:             'payment_date': post.get('payment_date'),
130:             'payment_method': post.get('payment_method'),
131:             'bank_origin': post.get('bank_origin'),
132:             'bank_destination': post.get('bank_destination', 'N/A'),
133:             'reference': post.get('reference'),
134:             'amount_vef': float(post.get('amount_vef', 0)),
135:             'exchange_rate': float(post.get('exchange_rate', 0)),
136:             'amount_usd': float(post.get('amount_usd', 0)) if post.get('amount_usd') and post.get('amount_usd') != 'undefined' else 0.0,
137:         }
138:         _logger.info(f"📝 Datos de pago recibidos: {payment_data}")
139: 
140:         request.session['payment_data'] = payment_data
141: 
142:         if order:
143:             if payment_data['amount_vef'] < (order.amount_total - 0.01):
144:                 _logger.warning(f"❌ Monto insuficiente: {payment_data['amount_vef']} < {order.amount_total}")
145:                 return request.make_response('MONTO_INSUFICIENTE', status=400)
146:             try:
147:                 attachment = request.env['ir.attachment'].sudo().create({
148:                     'name': filename,
149:                     'type': 'binary',
150:                     'datas': file_base64,
151:                     'res_model': 'sale.order',
152:                     'res_id': order.id,
153:                     'mimetype': mimetype,
154:                     'description': 'Comprobante de pago - Transferencia / Pago Móvil',
155:                 })
156:                 order.sudo().write({
157:                     'payment_proof': file_base64,
158:                     'payment_proof_filename': filename,
159:                     'payment_date': payment_data['payment_date'],
160:                     'payment_method': payment_data['payment_method'],
161:                     'bank_origin': payment_data['bank_origin'],
162:                     'bank_destination': payment_data['bank_destination'],
163:                     'reference': payment_data['reference'],
164:                     'amount_vef': payment_data['amount_vef'],
165:                     'exchange_rate': payment_data['exchange_rate'],
166:                     'amount_usd': payment_data['amount_usd'],
167:                 })
168:                 timestamp = int(attachment.write_date.timestamp()) if attachment.write_date else ''
169:                 attachment_url = f"/web/image/{attachment.id}" + (f"?unique={timestamp}" if timestamp else "")
170:                 if mimetype.startswith('image/'):
171:                     img_tag = f'<div><img src="{attachment_url}" style="max-width:100%; max-height:300px;"/></div>'
172:                 else:
173:                     img_tag = f'<div><a href="{attachment_url}" target="_blank">📄 Ver archivo adjunto</a></div>'
174:                 body_html = f"""
175:                 <p>🧾 <strong>Comprobante de pago adjunto</strong></p>
176:                 <ul>
177:                     <li>📅 Fecha: {payment_data.get('payment_date', 'No especificada')}</li>
178:                     <li>💳 Método: {payment_data.get('payment_method', 'No especificado')}</li>
179:                     <li>🔢 Referencia: {payment_data.get('reference', 'No especificada')}</li>
180:                     <li>₿ Monto Bs: {payment_data.get('amount_vef', 0):,.2f}</li>
181:                     <li>💱 Tasa BCV: {payment_data.get('exchange_rate', 0):,.2f}</li>
182:                     <li>💵 Monto USD: {payment_data.get('amount_usd', 0):,.2f}</li>
183:                 </ul>
184:                 {img_tag}
185:                 <p><em>Adjunto: {filename}</em></p>
186:                 """
187:                 order.sudo().message_post(
188:                     body=Markup(body_html),
189:                     attachment_ids=[attachment.id],
190:                     message_type='comment',
191:                     subtype_id=request.env.ref('mail.mt_comment').id
192:                 )
193:                 _logger.info(f"✅ Comprobante guardado en orden {order.name}")
194:                 return request.make_response('OK')
195:             except Exception as e:
196:                 _logger.error(f"Error guardando comprobante: {e}", exc_info=True)
197:                 return request.make_response('ERROR', status=500)
198: 
199:         # Fallback en sesión
200:         request.session['payment_proof'] = {
201:             'data': file_base64,
202:             'filename': filename,
203:             'mimetype': mimetype,
204:         }
205:         return request.make_response('OK')
206: 
207:     @http.route('/payment_proof/get_transfer_provider_id', type='json', auth='public', csrf=False)
208:     def get_transfer_provider_id(self):
209:         provider = request.env['payment.provider'].sudo().search([('is_wire_transfer', '=', True)], limit=1)
210:         _logger.info(f"Transfer provider ID: {provider.id if provider else 0}")
211:         return provider.id if provider else 0
212: 
213:     # -------------------------------------------------------------------------
214:     # LISTA DE BANCOS ORIGEN (corregida para eliminar duplicados por BIC)
215:     # -------------------------------------------------------------------------
216:     @http.route('/payment_proof/get_bank_list', type='json', auth='public', csrf=False)
217:     def get_bank_list(self):
218:         try:
219:             banks = request.env['res.bank'].sudo().search([('active', '=', True)], order='name ASC')
220:             unique = {}
221:             for bank in banks:
222:                 bic = bank.bic
223:                 if bic and bic not in unique:
224:                     unique[bic] = {
225:                         'id': bic,
226:                         'name': bank.name,
227:                         'bic': bic,
228:                     }
229:             bank_list = list(unique.values())
230:             _logger.info(f"Devolviendo {len(bank_list)} bancos únicos desde res.bank")
231:             return bank_list
232:         except Exception as e:
233:             _logger.error(f"Error al obtener lista de bancos: {str(e)}")
234:             return [
235:                 {'id': '0102', 'name': 'Banco de Venezuela', 'bic': '0102'},
236:                 {'id': '0134', 'name': 'Banesco Banco Universal', 'bic': '0134'},
237:                 {'id': '0105', 'name': 'Banco Mercantil', 'bic': '0105'},
238:             ]
239: 
240:     @http.route('/payment_proof/get_bank_journal_list', type='json', auth='public', csrf=False)
241:     def get_bank_journal_list(self):
242:         try:
243:             bank_journals = request.env['account.journal'].sudo().search([
244:                 ('type', '=', 'bank'),
245:                 ('active', '=', True),
246:             ], order='name ASC')
247:             bank_list = []
248:             for journal in bank_journals:
249:                 bank_name = journal.bank_id.name if journal.bank_id else journal.name
250:                 bank_list.append({
251:                     'id': journal.id,
252:                     'name': bank_name,
253:                     'journal_id': journal.id,
254:                     'bic': journal.bank_id.bic if journal.bank_id else '',
255:                 })
256:             _logger.info(f"Devolviendo {len(bank_list)} bancos desde los diarios contables")
257:             return bank_list
258:         except Exception as e:
259:             _logger.error(f"Error al obtener lista de bancos: {str(e)}")
260:             return []
261: 
262:     @http.route('/payment_proof/get_bank_details', type='json', auth='public', csrf=False)
263:     def get_bank_details(self, journal_id):
264:         try:
265:             if not journal_id:
266:                 return {'error': 'No se especificó banco destino'}
267:             try:
268:                 journal_id = int(journal_id)
269:             except (ValueError, TypeError):
270:                 return {'error': f'ID de banco inválido: {journal_id}'}
271:             journal = request.env['account.journal'].sudo().browse(journal_id).exists()
272:             if not journal:
273:                 return {'error': f'Banco destino no encontrado con ID: {journal_id}'}
274:             bank_details = {
275:                 'bank_name': journal.bank_id.name if journal.bank_id else journal.name,
276:                 'account_number': journal.bank_acc_number or 'No especificado',
277:                 'account_holder': journal.bank_id and journal.bank_id.name or request.env.company.name,
278:                 'phone': journal.bank_id and journal.bank_id.phone or '',
279:                 'email': journal.bank_id and journal.bank_id.email or '',
280:                 'routing_number': journal.bank_id and journal.bank_id.bic or '',
281:                 'instructions': 'Transferencia bancaria - Por favor use su número de orden como referencia',
282:             }
283:             company = request.env.company
284:             bank_details['company_name'] = company.name
285:             bank_details['company_rif'] = company.vat or ''
286:             _logger.info(f"Detalles del banco destino para journal {journal_id}: {bank_details}")
287:             return bank_details
288:         except Exception as e:
289:             _logger.error(f"Error al obtener detalles del banco: {str(e)}", exc_info=True)
290:             return {'error': str(e)}
291: 
292:     def _process_payment(self, **kwargs):
293:         _logger.info("🔄 Entrando en _process_payment (Payment Custom)")
294:         sale_order_id = request.session.get('sale_order_id') or request.session.get('sale_last_order_id')
295:         order = None
296:         if sale_order_id:
297:             order = request.env['sale.order'].sudo().browse(int(sale_order_id)).exists()
298:         if order and 'payment_proof' in request.session:
299:             proof = request.session.pop('payment_proof')
300:             try:
301:                 attachment = request.env['ir.attachment'].sudo().create({
302:                     'name': proof['filename'],
303:                     'type': 'binary',
304:                     'datas': proof['data'],
305:                     'res_model': 'sale.order',
306:                     'res_id': order.id,
307:                     'mimetype': proof.get('mimetype', 'application/octet-stream'),
308:                     'description': 'Comprobante de pago - Transferencia / Pago Móvil',
309:                 })
310:                 order.sudo().write({
311:                     'payment_proof': proof['data'],
312:                     'payment_proof_filename': proof['filename'],
313:                 })
314:                 timestamp = int(attachment.write_date.timestamp()) if attachment.write_date else ''
315:                 attachment_url = f"/web/image/{attachment.id}" + (f"?unique={timestamp}" if timestamp else "")
316:                 mimetype = proof.get('mimetype', '')
317:                 if mimetype.startswith('image/'):
318:                     img_tag = f'<div><img src="{attachment_url}" style="max-width:100%; max-height:300px;"/></div>'
319:                 else:
320:                     img_tag = f'<div><a href="{attachment_url}" target="_blank">📄 Ver archivo adjunto</a></div>'
321:                 body_html = f"<p>🧾 <strong>Comprobante de pago adjunto</strong> (recuperado desde sesión)</p>{img_tag}<p><em>Adjunto: {proof['filename']}</em></p>"
322:                 order.sudo().message_post(
323:                     body=Markup(body_html),
324:                     attachment_ids=[attachment.id],
325:                     message_type='comment',
326:                     subtype_id=request.env.ref('mail.mt_comment').id
327:                 )
328:             except Exception as e:
329:                 _logger.error(f"Error creando attachment desde sesión: {e}", exc_info=True)
330:         if order and 'payment_data' in request.session:
331:             payment_data = request.session.pop('payment_data')
332:             try:
333:                 order.sudo().write({
334:                     'payment_date': payment_data.get('payment_date'),
335:                     'payment_method': payment_data.get('payment_method'),
336:                     'bank_origin': payment_data.get('bank_origin'),
337:                     'bank_destination': payment_data.get('bank_destination', 'N/A'),
338:                     'reference': payment_data.get('reference'),
339:                     'amount_vef': payment_data.get('amount_vef', 0),
340:                     'exchange_rate': payment_data.get('exchange_rate', 0),
341:                     'amount_usd': payment_data.get('amount_usd', 0),
342:                 })
343:                 _logger.info(f"✅ Datos de pago adicionales guardados en orden {order.name}")
344:             except Exception as e:
345:                 _logger.error(f"Error guardando datos de pago adicionales: {e}", exc_info=True)
346:         return super()._process_payment(**kwargs)

(End of file - total 346 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/services/whatsapp_service.py"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/services/whatsapp_service.py</path>
<type>file</type>
<content>
1: # -*- coding: utf-8 -*-
2: import os
3: from pathlib import Path
4: import logging
5: import json
6: from odoo import api, models, fields, _
7: from odoo.exceptions import ValidationError
8: 
9: # 👇 Importa el caso de uso
10: from ..uses_cases.send_whatsapp_confirmation_use_case import SendWhatsappConfirmationUseCase
11: 
12: _logger = logging.getLogger(__name__)
13: 
14: class WhatsappService(models.AbstractModel):
15:     _name = 'whatsapp.service'
16:     _description = 'Whatsapp Service Layer'
17: 
18:     @api.model
19:     def sendWhatsappConfirmation(self, order):
20:         use_case = SendWhatsappConfirmationUseCase(self.env)
21:         return use_case.execute({'order': order})
22:     

(End of file - total 22 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/data/ir_cron_data.xml"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/data/ir_cron_data.xml</path>
<type>file</type>
<content>
1: <?xml version="1.0" encoding="utf-8"?>
2: <odoo>
3:     <record id="cron_fetch_bcv_rate" model="ir.cron">
4:         <field name="name">Obtener tasa BCV</field>
5:         <field name="model_id" ref="currency_rate_update_base.model_currency_rate_provider"/>
6:         <field name="state">code</field>
7:         <field name="code">model.run_cron_update()</field>
8:         <field name="interval_number">1</field>
9:         <field name="interval_type">days</field>
10:         <field name="active">True</field>
11:         <field name="user_id" ref="base.user_root"/>
12:         <field name="priority">10</field>
13:     </record>
14: 
15:     <record id="cron_update_ves_prices_from_usd" model="ir.cron">
16:         <field name="name">Actualizar precios VES desde USD (tasa BCV)</field>
17:         <field name="model_id" ref="product.model_product_template"/>
18:         <field name="state">code</field>
19:         <field name="code">model._recalculate_ves_prices_from_usd()</field>
20:         <field name="interval_number">1</field>
21:         <field name="interval_type">days</field>
22:         <field name="active">True</field>
23:         <field name="user_id" ref="base.user_root"/>
24:         <field name="priority">5</field>
25:     </record>
26: </odoo>

(End of file - total 26 lines)
</content>
```

---

## Assistant (Plan · DeepSeek V4 Flash Free · 4.1s)

_Thinking:_

Now I have a comprehensive picture of the module. Let me also check what modules it depends on to understand the inheritance chain, and look at the uses_cases and migrations directories briefly.

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/uses_cases"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/uses_cases</path>
<type>directory</type>
<entries>
__init__.py
__pycache__/
send_whatsapp_confirmation_use_case.py

(3 entries)
</entries>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/migrations"
}
```

**Output:**
```
<path>/home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/migrations</path>
<type>directory</type>
<entries>
19.0.1.0.1/

(1 entries)
</entries>
```

---

## Assistant (Plan · DeepSeek V4 Flash Free · 13.3s)

_Thinking:_

Now I have a complete understanding of the module. Let me summarize it clearly.

Aquí tienes el análisis del módulo `bcv_rate_update_venezuela`:

---

## ¿Qué hace?

Es un módulo completo de comercio electrónico y gestión financiera adaptado a Venezuela. Sus funcionalidades principales:

### 1. **Tasa BCV automática**
- Hereda de `currency_rate_update_base` y `currency_rate_update_venezuela`
- Un cron diario obtiene la tasa oficial del BCV (USD → VES) vía scraping (`requests` + `beautifulsoup4`)
- Cuando se crea/modifica una tasa VES, **recalcula automáticamente todos los precios** de productos desde USD

### 2. **Precios duales USD/VES en productos**
- `product.template` — campo `list_price_usd` para precio de venta en USD
- `product.product` — campo `lst_price_usd` para variantes
- `product.template.attribute.value` — campo `price_extra_usd` para atributos
- Sincronización bidireccional: cambiar precio VES → actualiza USD, y viceversa
- En `hooks.py`: `_populate_initial_usd_prices()` pobla precios USD iniciales al instalar

### 3. **Órdenes de venta con pago por transferencia**
- `sale.order` — campos: comprobante de pago (`payment_proof`), fecha, método, banco origen/destino, referencia, monto VES/USD, tasa de cambio
- `sale.order.line` — `price_usd_bcv`, `price_subtotal_usd_bcv`, `rate_value` (cálculo automático Bs→USD)
- `account.move.line` — copia el precio USD y tasa BCV desde la línea de venta
- Validación de campos obligatorios antes de confirmar

### 4. **Portal de pago frontend (e-commerce)**
- Subida de comprobante de pago (imagen/PDF) con ruta `/shop/upload_payment_proof`
- Autocompletado de dirección del partner por email/teléfono (`/shop/get_partner_data`, `/shop/search_partner_by_email_or_phone`)
- Endpoint `/payment/custom/process` que procesa el pago completo: crea transacción, confirma orden, la marca como `done`
- Endpoint `/payment/validate_and_save` para validar datos de pago vía JSON
- Lista de bancos origen desde `res.bank` y bancos destino desde `account.journal`

### 5. **Notificación WhatsApp post-compra**
- Servicio `whatsapp.service` que usa `SendWhatsappConfirmationUseCase`
- Envía confirmación al cliente cuando se sube un comprobante y la orden se confirma
- Previene envíos duplicados con campo `whatsapp_sent`

### 6. **Extras**
- `res.company` — campo `schedule_info` (horario de atención)
- `payment.provider` — campo `is_wire_transfer` (marca proveedor como transferencia bancaria)
- `whatsapp.history` — campo `sale_order_id` para relacionar historial con órdenes
- `website` — métodos `get_bcv_rate()`, `get_bcv_rate_info()`, `get_conversion_factor_ves_to_usd()`

---

## ¿Qué hereda?

| Modelo Odoo | Archivo | Nuevos campos/métodos |
|---|---|---|
| `res.currency.rate` | `models/res_currency_rate.py` | `is_bcv_rate`, `source`, `bcv_rate_value`, recálculo de precios VES |
| `sale.order` | `models/sale_order.py` | Campos de pago, `action_confirm()` override, `action_save_payment_data()`, `validate_payment_required_fields()`, `_process_order_post_confirm()` |
| `sale.order.line` | `models/sale_order_line.py` | `price_usd_bcv`, `price_subtotal_usd_bcv`, `rate_value` |
| `account.move.line` | `models/account_move_line.py` | `price_usd_bcv`, `bcv_rate_value` |
| `product.template` | `models/product_template.py` | `list_price_usd`, sincronización USD↔VES, `_recalculate_ves_prices_from_usd()` |
| `product.product` | `models/product_template.py` | `lst_price_usd`, sincronización USD↔VES |
| `product.template.attribute.value` | `models/product_template.py` | `price_extra_usd`, sincronización USD↔VES |
| `payment.provider` | `models/payment_provider.py` | `is_wire_transfer` |
| `res.company` | `models/res_company.py` | `schedule_info` |
| `website` | `models/website_cart_usd.py` | `get_bcv_rate()`, `get_bcv_rate_info()`, `get_conversion_factor_ves_to_usd()` |
| `whatsapp.history` | `models/whatsapp_history_extension.py` | `sale_order_id` |
| `WebsiteSale` (controller) | `controllers/website_sale_attachment.py` | Rutas de comprobante, autocompletado, bancos |

**Dependencias**: `base`, `web`, `sale_management`, `account`, `stock`, `point_of_sale`, `website_sale`, `contacts`, `payment`, `whatsapp_cloud_integration`, `currency_rate_update_base`, `currency_rate_update_venezuela`.

---

