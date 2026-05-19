/** @odoo-module **/
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

export class PaymentProofComponent extends Component {
    static template = "bcv_rate_update_venezuela.PaymentProofComponent";

    setup() {
        this.notification = useService("notification");
        this.state = useState({
            showSection: true,   // Siempre visible
            transferProviderId: null,
            fileUploading: false,
            uploadError: null,
            uploadSuccess: false,
            loading: true,
            selectedFileName: null,
            proof_valid: false,
            payment_date: new Date().toISOString().slice(0, 10),
            payment_method: 'movil',
            bank_origin: '',
            bank_destination: '',
            reference: '',
            amount_vef: 0,
            exchange_rate: 0,
            amount_usd: 0,
            original_amount_vef: 0,
            original_amount_usd: 0,
            is_valid_amount: false,
            rate_date: '',
            bankList: [],
            bankJournalList: [],
            bank_details: {
                bank_name: '',
                account_number: '',
                account_holder: '',
                phone: '',
                email: '',
                routing_number: '',
                instructions: '',
                company_name: '',
                company_rif: '',
                loading: false,
                error: null,
            },
            sale_order_id: null,
        });

        onWillStart(async () => {
            this.state.loading = true;
            try {
                const orderIdElem = document.querySelector('input[name="sale_order_id"]');
                this.state.sale_order_id = orderIdElem ? orderIdElem.value : null;

                const providerId = await rpc("/payment_proof/get_transfer_provider_id");
                this.state.transferProviderId = String(providerId);

                const banks = await rpc("/payment_proof/get_bank_list");
                this.state.bankList = banks;
                const journalBanks = await rpc("/payment_proof/get_bank_journal_list");
                this.state.bankJournalList = journalBanks;

                const origVefSpan = document.getElementById('original_amount_vef');
                const rateSpan = document.getElementById('bcv_exchange_rate');
                if (origVefSpan && rateSpan) {
                    this.state.original_amount_vef = this._normalizeNumber(origVefSpan.innerText);
                    this.state.exchange_rate = this._normalizeNumber(rateSpan.innerText);
                    this.state.amount_vef = this.state.original_amount_vef;
                    this._validateAmounts();
                }
            } catch (err) {
                console.error(err);
            } finally {
                this.state.loading = false;
                this._interceptPayment();
            }
        });

        onMounted(() => {
            this.state.showSection = true;
        });
    }

    _normalizeNumber(v) {
        let n = parseFloat(String(v).replace(/[^\d.,-]/g, '').replace(',', '.'));
        return isNaN(n) ? 0 : n;
    }

    _round(v) { return Math.round(v * 100) / 100; }

    async _loadBankDetails(journalId) {
        if (!journalId) {
            this.state.bank_details = { loading: false, error: null, bank_name: '', account_number: '' };
            return;
        }
        this.state.bank_details.loading = true;
        try {
            const details = await rpc("/payment_proof/get_bank_details", { journal_id: journalId });
            this.state.bank_details = { ...this.state.bank_details, ...details, loading: false, error: null };
        } catch (err) {
            this.state.bank_details = { ...this.state.bank_details, error: "Error", loading: false };
        }
    }

    _updateField(e) {
        this.state[e.currentTarget.dataset.field] = e.target.value;
        if (e.currentTarget.dataset.field === 'bank_destination') this._loadBankDetails(e.target.value);
    }

    _onAmountVefInput(e) {
        this.state.amount_vef = this._normalizeNumber(e.target.value);
        if (this.state.exchange_rate) this.state.amount_usd = this._round(this.state.amount_vef / this.state.exchange_rate);
        this._validateAmounts();
    }

    _validateAmounts() {
        this.state.is_valid_amount = this.state.amount_vef >= (this.state.original_amount_vef - 0.01);
    }

    // Detección infalible: por texto "Transferencia bancaria"
    _isTransferSelected() {
        const radio = document.querySelector('input[name="o_payment_radio"]:checked');
        if (!radio) return false;
        const parent = radio.closest('.o_payment_option, .payment_method, li');
        const text = parent ? parent.innerText.toLowerCase() : '';
        return text.includes('transferencia') || text.includes('bank transfer');
    }

    _getFieldValue(id) {
        const el = document.getElementById(id);
        return el ? el.value : '';
    }

    async _validateAndSave() {
        if (!this._isTransferSelected()) return true;  // No validar otros métodos

        const missing = [];
        if (!this._getFieldValue('bank_origin')) missing.push("Banco origen");
        if (!this._getFieldValue('bank_destination')) missing.push("Banco destino");
        if (!this._getFieldValue('reference')) missing.push("Referencia");
        if (!this.state.proof_valid) missing.push("Comprobante de pago");
        if (!this.state.is_valid_amount) missing.push("Monto válido (debe ser ≥ " + this.state.original_amount_vef + " Bs.)");

        if (missing.length) {
            alert("❌ Complete los siguientes campos:\n- " + missing.join("\n- "));
            return false;
        }

        try {
            const data = {
                sale_order_id: this.state.sale_order_id,
                payment_date: this.state.payment_date,
                payment_method: this.state.payment_method,
                bank_origin: this.state.bank_origin,
                bank_destination: this.state.bank_destination,
                reference: this.state.reference,
                amount_vef: this.state.amount_vef,
                exchange_rate: this.state.exchange_rate,
                amount_usd: this.state.amount_usd,
            };
            const res = await rpc("/payment/validate_and_save", data);
            if (res.error) {
                alert("Error: " + res.error);
                return false;
            }
            return true;
        } catch (err) {
            alert("Error de validación. Intente de nuevo.");
            return false;
        }
    }

    _interceptPayment() {
        // Método 1: interceptar clic en el botón (más directo)
        const btn = document.querySelector('button[name="o_payment_submit_button"]');
        if (btn) {
            btn.addEventListener('click', async (event) => {
                const ok = await this._validateAndSave();
                if (!ok) {
                    event.preventDefault();
                    event.stopImmediatePropagation();
                }
            }, { capture: true });
        } else {
            setTimeout(() => this._interceptPayment(), 200);
        }

        // Método 2: interceptar submit del formulario (por si acaso)
        const form = document.getElementById('o_payment_form');
        if (form && !form.hasAttribute('data-submit-check')) {
            form.setAttribute('data-submit-check', 'true');
            form.addEventListener('submit', async (event) => {
                const ok = await this._validateAndSave();
                if (!ok) {
                    event.preventDefault();
                    event.stopPropagation();
                }
            });
        }
    }

    async uploadFile(file) {
        this.state.fileUploading = true;
        this.state.proof_valid = false;
        try {
            const fd = new FormData();
            fd.append("payment_proof_file", file);
            fd.append("payment_date", this.state.payment_date);
            fd.append("payment_method", this.state.payment_method);
            fd.append("bank_origin", this.state.bank_origin);
            fd.append("bank_destination", this.state.bank_destination);
            fd.append("reference", this.state.reference);
            fd.append("amount_vef", this.state.amount_vef);
            fd.append("exchange_rate", this.state.exchange_rate);
            fd.append("amount_usd", this.state.amount_usd);
            const resp = await fetch("/shop/upload_payment_proof", {
                method: "POST",
                body: fd,
                credentials: "same-origin",
            });
            if (!resp.ok) throw new Error();
            this.notification.add("Comprobante subido correctamente", { type: "success" });
            this.state.uploadSuccess = true;
            this.state.proof_valid = true;
        } catch (err) {
            this.state.uploadError = "Error al subir";
            this.notification.add("Error al subir el comprobante", { type: "danger" });
        } finally {
            this.state.fileUploading = false;
        }
    }

    _handleFileChange(e) {
        const file = e.target.files[0];
        if (file) {
            this.state.selectedFileName = file.name;
            this.state.proof_valid = false;
            this.uploadFile(file);
        } else {
            this.state.selectedFileName = null;
            this.state.proof_valid = false;
        }
    }
}

registry.category("public_components").add("bcv_rate_update_venezuela.PaymentProofComponent", PaymentProofComponent);