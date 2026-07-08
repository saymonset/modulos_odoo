/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { posState } from "../../../../shared_state";

export class CustomPaymentLines extends Component {
    static template = "pos_venezuela_dual_currency.CustomPaymentLines";
    static props = {
        paymentLines: { type: Array, optional: true },
    };

    setup() {
        super.setup();
        this.pos = usePos();
        this.orm = useService("orm");

        this.state = useState({
            rate: 1,
            rateLoaded: false,
            selectedCurrency: "usd",
            inputAmount: "",
            inputFocused: false,
        });

        onMounted(() => {
            this.loadRate();
            this._rateInterval = setInterval(() => this.loadRate(), 60000);
        });

        onWillUnmount(() => {
            if (this._rateInterval) clearInterval(this._rateInterval);
        });
    }

    // ── Available currencies (extensible) ──
    get currencies() {
        return [
            { id: "bs", symbol: "Bs.", label: "Bolívares", rate: 1 },
            { id: "usd", symbol: "US$", label: "Dólares", rate: this.state.rate || 1 },
        ];
    }

    get activeCurrency() {
        return this.currencies.find((c) => c.id === this.state.selectedCurrency)
            || this.currencies[0];
    }

    get convertedBs() {
        const val = parseFloat(this.state.inputAmount) || 0;
        if (this.state.selectedCurrency === "bs") return val;
        return val * (this.state.rate || 1);
    }

    get displayConversion() {
        const val = parseFloat(this.state.inputAmount) || 0;
        if (val === 0) return null;
        if (this.state.selectedCurrency === "usd") {
            return { label: "Bs.", value: this.convertedBs };
        }
        return { label: "US$", value: this.state.rate > 0 ? val / this.state.rate : 0 };
    }

    get canApply() {
        return parseFloat(this.state.inputAmount) > 0
            && this.props.paymentLines
            && this.props.paymentLines.length > 0;
    }

    // ── Actions ──

    selectCurrency(currencyId) {
        if (currencyId === this.state.selectedCurrency) return;
        this.state.selectedCurrency = currencyId;
        this.state.inputAmount = "";
    }

    onInputChange(ev) {
        const raw = ev.target.value;
        if (raw === "") {
            this.state.inputAmount = "";
            return;
        }
        let sanitized = raw.replace(/,/g, "").replace(/^0+(\d)/, "$1");
        if (sanitized === ".") sanitized = "0.";
        if (sanitized.startsWith(".")) sanitized = "0" + sanitized;
        if (/^-?\d*\.?\d*$/.test(sanitized)) {
            this.state.inputAmount = sanitized;
        }
    }

    applyToPaymentLine() {
        if (!this.canApply) return;
        const bsAmount = Math.round(this.convertedBs * 100) / 100;
        const lines = this.props.paymentLines;

        if (lines.length === 0) return;

        const selectedLine = lines.find((l) => l.isSelected());
        const target = selectedLine || lines[lines.length - 1];

        if (!posState.is_igtf) {
            try {
                target.setAmount(bsAmount);
            } catch (_) {
                console.warn("pos_venezuela_dual_currency: setAmount failed", _);
            }
            target.currency_type = this.state.selectedCurrency;
            target.amount_foreign = parseFloat(this.state.inputAmount) || 0;
            target.rate_applied = this.state.rate;
        }

        this.state.inputAmount = "";
    }

    onKeydown(ev) {
        if (ev.key === "Enter") {
            this.applyToPaymentLine();
        }
    }

    // ── Rate ──

    async loadRate() {
        try {
            const rate = await this.orm.call(
                "product.template",
                "get_bcv_rate_json",
                [this.pos.company.id]
            );
            this.state.rate = rate || 1;
            this.state.rateLoaded = true;
        } catch (e) {
            console.error("Error al obtener tasa BCV:", e);
            this.state.rateLoaded = true;
        }
    }

    // ── Formatting ──

    formatDecimal(value) {
        if (value == null || isNaN(value)) return "0.00";
        return Number(value).toFixed(2);
    }
}
