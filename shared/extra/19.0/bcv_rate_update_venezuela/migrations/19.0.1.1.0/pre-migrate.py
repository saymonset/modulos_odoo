import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Safety net: asegurar que amount_total_ves_from_usd exista en purchase_order."""
    cr.execute(
        "ALTER TABLE purchase_order "
        "ADD COLUMN IF NOT EXISTS amount_total_ves_from_usd numeric DEFAULT 0.0"
    )
    _logger.info("Column amount_total_ves_from_usd ensured on purchase_order.")