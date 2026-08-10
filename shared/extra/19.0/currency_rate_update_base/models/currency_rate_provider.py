import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class CurrencyRateProvider(models.Model):
    _name = 'currency.rate.provider'
    _description = 'Currency Rate Provider'

    name = fields.Char(string='Name', required=True)
    provider_type = fields.Selection([
        ('manual', 'Manual')
    ], string='Provider Type', required=True, default='manual')
    
    currency_id = fields.Many2one('res.currency', string='Target Currency', required=True)
    rate_currency_id = fields.Many2one('res.currency', string='Rate Currency', 
                                      compute='_compute_rate_currency_id', store=True, readonly=False,
                                      help="Currency of the rate value (e.g. COP for Colombia)")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency', readonly=True, store=True)

    @api.depends('provider_type', 'name', 'company_id')
    def _compute_rate_currency_id(self):
        for reg in self:
            name = (reg.name or '').lower()
            res_currency = self.env['res.currency']
            
            # Auto-detect based on name or type
            if 'venezuela' in name or 'bcv' in name or reg.provider_type == 'bcv':
                reg.rate_currency_id = self.env.ref('base.VES', raise_if_not_found=False)
            elif 'colombia' in name or 'bogota' in name:
                reg.rate_currency_id = self.env.ref('base.COP', raise_if_not_found=False)
            elif 'costa rica' in name or 'bccr' in name:
                reg.rate_currency_id = self.env.ref('base.CRC', raise_if_not_found=False)
            else:
                reg.rate_currency_id = reg.company_id.currency_id
    
    active = fields.Boolean(default=True)
    last_update = fields.Datetime(string='Last Successful Update', readonly=True)
    last_rate = fields.Float(string='Last Rate Obtained', digits=(12, 6), readonly=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('error', 'Error')
    ], default='draft')

    is_main_rate = fields.Boolean(
        string='Main Rate',
        help="Use this provider as the primary source for website and reports.",
        default=False
    )

    @api.onchange('is_main_rate')
    def _onchange_is_main_rate(self):
        if self.is_main_rate:
            # Uncheck others for the same company
            others = self.search([
                ('id', '!=', self._origin.id if self._origin else self.id),
                ('company_id', '=', self.company_id.id),
                ('is_main_rate', '=', True)
            ])
            others.write({'is_main_rate': False})

    def action_update_rate(self):
        """Main entry point to update rates"""
        for record in self:
            try:
                rate = record._dispatch_fetch()
                if rate:
                    record._update_odoo_rate(rate)
                    record.write({
                        'last_update': fields.Datetime.now(),
                        'last_rate': rate,
                        'state': 'active'
                    })
            except Exception as e:
                record.state = 'error'
                _logger.error(f"Error updating rate for {record.name}: {str(e)}")
                raise UserError(_("Error updating rate: %s") % str(e))

    def _dispatch_fetch(self):
        """Override this or add methods like _fetch_rate_XYZ"""
        self.ensure_one()
        method_name = f'_fetch_rate_{self.provider_type}'
        if hasattr(self, method_name):
            return getattr(self, method_name)()
        return False

    def _update_odoo_rate(self, rate_value):
        """
        Updates res.currency.rate.
        Most scrapers return 'Price of 1 USD in local currency'.
        Odoo expects 'rate' to be '1 unit of Company Currency = X units of Target Currency'.
        """
        self.ensure_one()
        company = self.company_id
        base_currency = company.currency_id
        target_currency = self.currency_id
        usd = self.env.ref('base.USD')

        if target_currency == base_currency:
            _logger.info("Target currency is same as company base currency. Skipping rate update.")
            return

        # Case 1: Company base currency is USD
        # If scraper returns 1 USD = 36 VES, and target is VES, rate = 36.
        if base_currency == usd:
            final_rate = rate_value
        
        # Case 2: Target currency is USD, base is local (e.g. VES)
        # If scraper returns 1 USD = 36 VES, and target is USD, rate = 1 / 36.
        elif target_currency == usd:
            final_rate = 1.0 / rate_value if rate_value != 0 else 0
            
        # Case 3: Both are different from USD (Cross rate)
        # We use USD as a bridge. 
        # We assume rate_value is 'Price of 1 USD in Target Currency'.
        # We need 'Price of 1 USD in Base Currency' to calculate.
        else:
            # Try to get the latest USD rate in this company
            usd_rate_record = self.env['res.currency.rate'].search([
                ('currency_id', '=', usd.id),
                ('company_id', '=', company.id),
            ], order='name desc', limit=1)
            
            if usd_rate_record and usd_rate_record.rate:
                # 1 Base = usd_rate_record.rate USD
                # 1 USD = rate_value Target
                # 1 Base = (usd_rate_record.rate * rate_value) Target
                final_rate = usd_rate_record.rate * rate_value
            else:
                # Fallback: assume 1:1 if no USD rate found? Or just use rate_value?
                # This case is rare if the user sets up providers correctly.
                final_rate = rate_value

        _logger.info(f"Updating rate for {target_currency.name} (Base: {base_currency.name}): {final_rate}")
        
        # Create or update today's rate
        rate_record = self.env['res.currency.rate'].search([
            ('currency_id', '=', target_currency.id),
            ('name', '=', fields.Date.today()),
            ('company_id', '=', company.id),
        ], limit=1)
        
        vals = {
            'currency_id': target_currency.id,
            'name': fields.Date.today(),
            'rate': final_rate,
            'company_id': company.id,
            'original_value': rate_value,
            'provider_id': self.id,
        }
        
        if rate_record:
            rate_record.write(vals)
        else:
            self.env['res.currency.rate'].create(vals)

    def run_cron_update(self):
        providers = self.search([('active', '=', True), ('state', '!=', 'draft')])
        providers.action_update_rate()
