/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

let _rate = 1;
let _copRate = 1;
let _copEnabled = false;
let _loaded = false;

const _origSetup = TicketScreen.prototype.setup;

patch(TicketScreen.prototype, {
    setup() {
        if (_origSetup) {
            _origSetup.call(this, ...arguments);
        }
        this.pos = usePos();
        this.orm = useService("orm");
        this._ticketRatesLoaded = _loaded;
        this._ticketRate = _rate;
        this._ticketCopRate = _copRate;
        this._ticketCopEnabled = _copEnabled;
        if (!_loaded) {
            this._loadTicketRates();
        }
    },

    getTotalUsd(order) {
        const rate = this._ticketRate || _rate;
        if (!rate || rate <= 0) return 0;
        return (order.priceIncl || 0) / rate;
    },

    getTotalCop(order) {
        const copRate = this._ticketCopRate || _copRate;
        const rate = this._ticketRate || _rate;
        if (!copRate || copRate <= 0 || !(this._ticketCopEnabled || _copEnabled)) return 0;
        return (order.priceIncl || 0) / rate * copRate;
    },

    formatAmount(value) {
        if (value == null || isNaN(value)) return "0,00";
        return Number(value).toLocaleString("es-VE", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    },

    formatAmountCop(value) {
        if (value == null || isNaN(value)) return "0";
        return Number(value).toLocaleString("es-VE", {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        });
    },

    async _loadTicketRates() {
        try {
            const rate = await this.orm.call(
                "product.template", "get_bcv_rate_json",
                [this.pos.company.id]
            );
            _rate = rate || 1;
        } catch (_) {}
        try {
            const [copRate, copEnabled] = await Promise.all([
                this.orm.call("product.template", "get_cop_rate_json", [this.pos.company.id]),
                this.orm.call("product.template", "get_cop_enabled_json", [this.pos.company.id]),
            ]);
            _copRate = copRate || 1;
            _copEnabled = !!copEnabled;
        } catch (_) {}
        _loaded = true;
        this._ticketRatesLoaded = true;
        this._ticketRate = _rate;
        this._ticketCopRate = _copRate;
        this._ticketCopEnabled = _copEnabled;
        this.render();
    },

    showTicketUsd() {
        return this._ticketRate > 0;
    },

    showTicketCop() {
        return (this._ticketCopEnabled || _copEnabled) && this._ticketCopRate > 0;
    },
});
