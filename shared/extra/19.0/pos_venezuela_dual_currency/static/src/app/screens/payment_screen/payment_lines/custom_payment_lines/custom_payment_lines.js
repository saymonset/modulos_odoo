/** @odoo-module **/

import { Component, useState, onRendered, onWillUpdateProps, useRef } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
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
        this.inputRef = useRef("bsInput");
        this.state = useState({
            result: 0,
            hasData: false,
            rate: 1,
        });

        this.loadRate().then(r => { this.state.rate = r || 1; });

        onRendered(() => {
            this.updateHasData();
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.paymentLines) {
                this.updateHasData(nextProps.paymentLines);
            }
        });
    }

    updateHasData(paymentLines) {
        const lines = paymentLines || this.props.paymentLines || [];
        this.state.hasData = lines.length > 0;
        if (!this.state.hasData) {
            this.state.result = 0;
        }
    }

    async onInputChange(event) {
        const val = parseFloat(event.target.value) || 0;
        if (this.state.rate > 0) {
            this.state.result = val / this.state.rate;
        } else {
            this.state.result = 0;
        }
        this.updateLastPaymentLine(this.state.result);
    }

    onBlur() {
        if (this.inputRef.el) {
            this.inputRef.el.value = 0;
        }
        this.state.result = 0;
        this.state.inputValue = 0;

        // Auto-agregar primera línea de pago si no hay
        const currentOrder = posState.getCurrentOrder();
        const paymentMethods = this.pos.config.payment_method_ids.slice().sort((a, b) => a.sequence - b.sequence);
        if (currentOrder && paymentMethods.length > 0 && (!this.props.paymentLines || this.props.paymentLines.length === 0)) {
            currentOrder.add_paymentline(paymentMethods[0]);
        }
    }

    updateLastPaymentLine(newValue) {
        const lines = this.props.paymentLines || [];
        if (lines.length > 0) {
            const lastLine = lines[lines.length - 1];
            if (posState.is_igtf) {
                // El IGTF se maneja desde la lógica en payment_screen.js
            } else {
                lastLine.amount = newValue;
            }
        }
    }

    async loadRate() {
        try {
            const rate = await this.orm.call(
                'product.template', 'get_bcv_rate_json',
                [this.pos.company.id]
            );
            return rate;
        } catch (e) {
            console.error("Error al obtener tasa BCV:", e);
            return 1;
        }
    }

    formatCurrency(value) {
        // Usa el formateador del entorno POS si está disponible, o toFixed
        if (this.env && this.env.utils && this.env.utils.formatCurrency) {
            return this.env.utils.formatCurrency(value);
        }
        return Number(value).toFixed(2);
    }
}
