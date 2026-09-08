/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount, onWillUpdateProps } from "@odoo/owl";
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
            copRate: 1,
            copEnabled: false,
            rateLoaded: false,
            selectedCurrency: "bs",
            inputAmount: "",
            inputFocused: false,
            _rawDigits: "0",
            _trailingComma: false,
            remainingAtSelection: 0,
        });

        onMounted(() => {
            if ((this.props.paymentLines || []).length > 0) {
                this.prefillFromRemaining();
            }
            this.loadRate();
            this._rateInterval = setInterval(() => this.loadRate(), 60000);
        });

        onWillUnmount(() => {
            if (this._rateInterval) clearInterval(this._rateInterval);
        });

        onWillUpdateProps((nextProps) => {
            const prevLen = (this.props.paymentLines || []).length;
            const nextLen = (nextProps.paymentLines || []).length;
            if (nextLen !== prevLen) {
                if (nextLen > 0) {
                    this.prefillFromRemaining();
                } else {
                    this.state.inputAmount = "0";
                    this.state._rawDigits = "0";
                }
            }
        });
    }

    // ── Available currencies (extensible) ──
    get currencies() {
        const list = [
            { id: "bs", symbol: "Bs.", label: "Bolívares", rate: 1 },
            { id: "usd", symbol: "US$", label: "Dólares", rate: this.state.rate || 1 },
        ];
        if (this.state.copEnabled) {
            list.push({ id: "cop", symbol: "COP$", label: "Pesos", rate: this.state.copRate || 1 });
        }
        return list;
    }

    get activeCurrency() {
        return this.currencies.find((c) => c.id === this.state.selectedCurrency)
            || this.currencies[0];
    }

    get convertedBs() {
        const val = this._parseEsVE(this.state.inputAmount);
        if (this.state.selectedCurrency === "bs") return val;
        if (this.state.selectedCurrency === "cop") {
            const usdVal = this.state.copRate > 0 ? val / this.state.copRate : 0;
            return usdVal * (this.state.rate || 1);
        }
        return val * (this.state.rate || 1);
    }

    get displayConversion() {
        const val = this._parseEsVE(this.state.inputAmount);
        if (val === 0) return null;
        const rate = this.state.rate || 1;
        const copRate = this.state.copRate || 1;
        if (this.state.selectedCurrency === "usd") {
            const copVal = copRate > 0 ? val * copRate : 0;
            if (this.state.copEnabled) {
                return [
                    { label: "Bs.", value: val * rate },
                    { label: "COP$", value: copVal },
                ];
            }
            return [{ label: "Bs.", value: val * rate }];
        }
        if (this.state.selectedCurrency === "cop") {
            const usdVal = copRate > 0 ? val / copRate : 0;
            return [
                { label: "US$", value: usdVal },
                { label: "Bs.", value: usdVal * rate },
            ];
        }
        // bs selected
        const usdVal = rate > 0 ? val / rate : 0;
        const copVal = copRate > 0 ? usdVal * copRate : 0;
        if (this.state.copEnabled) {
            return [
                { label: "US$", value: usdVal },
                { label: "COP$", value: copVal },
            ];
        }
        return [{ label: "US$", value: usdVal }];
    }

    get canApply() {
        return this._parseEsVE(this.state.inputAmount) > 0
            && this.props.paymentLines
            && this.props.paymentLines.length > 0;
    }

    // Nombre del método de pago al que se aplicará el monto (si hay línea seleccionada)
    get selectedPaymentName() {
        const lines = this.props.paymentLines || [];
        const selected = lines.find((l) => l.isSelected && l.isSelected());
        try {
            return (selected && selected.payment_method_id && selected.payment_method_id.name) || "";
        } catch (_) {
            return "";
        }
    }

    // Restante por pagar en Bs (moneda base). Piso en 0 para evitar
    // pre-llenados negativos (IGTF/cambio) y para que la deuda cubierta
    // pre-llene vacío en lugar de reinyectar montos de líneas previas.
    get remainingInBs() {
        const order = this.pos.getOrder();
        return order ? Math.max(order.remainingDue, 0) : 0;
    }

    // Pre-llenar el input con el restante, siempre en Bs.
    // Si pendingPrefillDue tiene un valor (capturado antes de agregar la línea),
    // usarlo; si no, caer a remainingInBs (remainingDue actual).
    // Guarda remainingAtSelection para reutilizar al cambiar de moneda.
    prefillFromRemaining() {
        this.state.selectedCurrency = "bs";
        const due = posState.pendingPrefillDue != null
            ? Math.max(posState.pendingPrefillDue, 0)
            : this.remainingInBs;
        posState.pendingPrefillDue = null;
        this.state.remainingAtSelection = due;
        this.state._rawDigits = String(due);
        this.state._trailingComma = false;
        this.state.inputAmount = this._formatDisplay(due, false);
    }

    // ── Actions ──

    selectCurrency(currencyId) {
        if (currencyId === this.state.selectedCurrency) return;
        this.state.selectedCurrency = currencyId;
        this._prefillForCurrency();
    }

    // Pre-llenar con el deudor en la moneda seleccionada
    _prefillForCurrency() {
        const bsAmount = this.state.remainingAtSelection || this.remainingInBs;
        const rate = this.state.rate || 1;
        const copRate = this.state.copRate || 1;
        let value;
        if (this.state.selectedCurrency === "usd") {
            value = rate > 0 ? bsAmount / rate : 0;
        } else if (this.state.selectedCurrency === "cop") {
            value = rate > 0 && copRate > 0 ? (bsAmount / rate) * copRate : 0;
        } else {
            value = bsAmount;
        }
        const formatted = this._formatDisplay(value, false);
        this.state._rawDigits = String(Math.round(value * 100) / 100);
        this.state._trailingComma = false;
        this.state.inputAmount = formatted;
    }

    onInputChange(ev) {
        const raw = ev.target.value;
        if (raw === "") {
            this.state.inputAmount = "";
            this.state._rawDigits = "0";
            return;
        }
        // Parse es-VE: quitar puntos de miles, coma→punto
        const stripped = raw.replace(/\./g, "").replace(",", ".");
        this.state._trailingComma = raw.endsWith(",");
        const digitsOnly = stripped.replace(/[^0-9.]/g, "");
        let value = parseFloat(digitsOnly);
        if (!isFinite(value) || value < 0) return;
        value = Math.round(value * 100) / 100;
        this.state._rawDigits = String(value);
        const showDecimals = raw.includes(",");
        this.state.inputAmount = this._formatDisplay(value, showDecimals);
    }

    applyToPaymentLine() {
        if (!this.canApply) return;
        const bsAmount = Math.round(this.convertedBs * 100) / 100;
        const lines = this.props.paymentLines;

        if (lines.length === 0) return;

        const target = lines.find((l) => l.isSelected())
            || lines
                .slice()
                .reverse()
                .find((l) => {
                    const status = l.get_payment_status ? l.get_payment_status() : "";
                    return status !== "waiting" && status !== "waitingCard";
                })
            || lines[lines.length - 1];

        if (!target) return;

        if (!posState.is_igtf) {
            try {
                target.setAmount(bsAmount);
            } catch (_) {
                console.warn("pos_venezuela_dual_currency: setAmount failed", _);
            }
            target.currency_type = this.state.selectedCurrency;
            target.rate_applied = this.state.selectedCurrency === "cop" ? this.state.copRate : this.state.rate;
            if (this.state.selectedCurrency === "usd") {
                target.amount_foreign = this._parseEsVE(this.state.inputAmount);
            } else if (this.state.selectedCurrency === "cop") {
                const usdVal = this.state.copRate > 0 ? this._parseEsVE(this.state.inputAmount) / this.state.copRate : 0;
                target.amount_foreign = Math.round(usdVal * 100) / 100;
            } else {
                target.amount_foreign = this.state.rate > 0
                    ? Math.round((bsAmount / this.state.rate) * 100) / 100
                    : 0;
            }
        }

        this.state.inputAmount = "0";
        this.state._rawDigits = "0";
        this.state._trailingComma = false;
        this.state.remainingAtSelection = 0;
    }

    onKeydown(ev) {
        if (ev.key === "Enter") {
            this.applyToPaymentLine();
        }
    }

    // Pagar exactamente el monto restante en la moneda activa
    applyExactRemaining() {
        if (!this.props.paymentLines || this.props.paymentLines.length === 0) return;
        const order = this.pos.getOrder();
        const remainingBs = order ? order.remainingDue : 0;
        if (remainingBs <= 0) return;

        const rate = this.state.rate || 1;
        const copRate = this.state.copRate || 1;
        let value;
        if (this.state.selectedCurrency === "usd") {
            value = rate > 0 ? remainingBs / rate : 0;
        } else if (this.state.selectedCurrency === "cop") {
            value = rate > 0 && copRate > 0 ? (remainingBs / rate) * copRate : 0;
        } else {
            value = remainingBs;
        }
        this.state.inputAmount = this._formatDisplay(value, false);
        this.state._rawDigits = String(Math.round(value * 100) / 100);
        this.state._trailingComma = false;
        this.applyToPaymentLine();
    }

    clearInput() {
        this.state.inputAmount = "0";
        this.state._rawDigits = "0";
        this.state._trailingComma = false;
    }

    // ── Formatting helpers (es-VE) ──

    // Parsear formato es-VE: quitar puntos de miles, coma→punto decimal
    _parseEsVE(raw) {
        if (raw == null || raw === "" || raw === "0") return 0;
        const stripped = raw.replace(/\./g, "").replace(",", ".");
        const val = parseFloat(stripped);
        return isFinite(val) ? val : 0;
    }

    // Formatear número con estilo es-VE: puntos de miles, coma decimal.
    // decimals=true siempre muestra 2 decimales; decimals=false solo si los tiene.
    _formatDisplay(value, { decimals = false } = {}) {
        if (!isFinite(value) || value < 0) return "0";
        const rounded = Math.round(value * 100) / 100;
        const hasDecimals = !Number.isInteger(rounded) || decimals;
        const formatted = rounded.toLocaleString("es-VE", {
            minimumFractionDigits: hasDecimals ? 2 : 0,
            maximumFractionDigits: 2,
        });
        return formatted;
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
        try {
            const [copRate, copEnabled] = await Promise.all([
                this.orm.call('product.template', 'get_cop_rate_json', [this.pos.company.id]),
                this.orm.call('product.template', 'get_cop_enabled_json', [this.pos.company.id]),
            ]);
            this.state.copRate = copRate || 1;
            this.state.copEnabled = !!copEnabled;
        } catch (_) {}
    }

    // ── Formatting ──

    formatDecimal(value) {
        if (value == null || isNaN(value)) return "0,00";
        return Number(value).toLocaleString("es-VE", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }
}
