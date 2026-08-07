from odoo import models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def get_statistics_for_session(self, session):
        statistics = super().get_statistics_for_session(session)
        company = self.company_id or session.company_id
        rate = self.env['product.template']._get_bcv_rate(company)
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        total_usd = 0.0
        paid = (statistics.get('orders') or {}).get('paid')
        if paid and paid.get('amount'):
            total_usd = paid['amount'] / rate if rate else 0.0
        statistics['total_usd'] = {
            'amount': total_usd,
            'display': usd.format(total_usd) if usd else f"${total_usd:,.2f}",
        }
        statistics['rate'] = {'amount': rate, 'display': f"{rate:,.4f}"}
        return statistics