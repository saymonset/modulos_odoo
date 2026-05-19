/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

let alreadyMounted = false;

export class PaymentProofComponent extends Component {
    static template = "bcv_rate_update_venezuela.PaymentProofComponent";

    setup() {
        if (alreadyMounted || document.getElementById('payment_proof_form_container')) {
            console.warn("⚠️ PaymentProofComponent ya está montado, ignorando duplicado");
            this.state = useState({ loading: false });
            return;
        }
        alreadyMounted = true;

        this.notification = useService("notification");
        this.state = useState({
            loading: false,
            bankList: [],
            bankJournalList: [],
            original_amount_vef: 0,
            exchange_rate: 0,
            amount_vef: 0,
            amount_usd: 0,
            is_valid_amount: false,
            rate_date: '',
            payment_date: new Date().toISOString().slice(0, 10),
            payment_method: 'movil',
            bank_origin: '',
            bank_destination: '',
            reference: '',
            proof_valid: false,
            selectedFileName: null,
            uploadSuccess: false,
            fileUploading: false,
            uploadError: null,
            bank_details: { bank_name: '', account_number: '', loading: false, error: null },
        });

        onWillStart(async () => {
            try {
                const banks = await rpc("/payment_proof/get_bank_list");
                this.state.bankList = banks;
                const journalBanks = await rpc("/payment_proof/get_bank_journal_list");
                this.state.bankJournalList = journalBanks;
                const origVefSpan = document.getElementById('original_amount_vef');
                const rateSpan = document.getElementById('bcv_exchange_rate');
                const rateDateSpan = document.getElementById('bcv_rate_date');
                if (origVefSpan && rateSpan) {
                    this.state.original_amount_vef = this._normalizeNumber(origVefSpan.innerText);
                    this.state.exchange_rate = this._normalizeNumber(rateSpan.innerText);
                    this.state.rate_date = rateDateSpan ? rateDateSpan.innerText : '';
                    this.state.amount_vef = this.state.original_amount_vef;
                    // Calcular USD inicial
                    this.state.amount_usd = this._round(this.state.amount_vef / this.state.exchange_rate);
                    this._validateAmounts();
                }
            } catch (err) {
                console.error(err);
                this.notification.add("Error al cargar datos de pago", { type: "danger" });
            }
        });
    }

    _normalizeNumber(v) {
        let n = parseFloat(String(v).replace(/[^\d.,-]/g, '').replace(',', '.'));
        return isNaN(n) ? 0 : n;
    }

    _round(v) {
        return Math.round(v * 100) / 100;
    }

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
            this.state.bank_details = { ...this.state.bank_details, error: "Error cargando banco", loading: false };
        }
    }

    _updateField(e) {
        this.state[e.currentTarget.dataset.field] = e.target.value;
        if (e.currentTarget.dataset.field === 'bank_destination') this._loadBankDetails(e.target.value);
    }

    _onAmountVefInput(e) {
        let rawValue = e.target.value;
        let value = this._normalizeNumber(rawValue);
        this.state.amount_vef = value;
        if (this.state.exchange_rate > 0) {
            this.state.amount_usd = this._round(value / this.state.exchange_rate);
        } else {
            this.state.amount_usd = 0;
        }
        this._validateAmounts();
    }

    _onAmountUsdInput(e) {
        let rawValue = e.target.value;
        let value = this._normalizeNumber(rawValue);
        this.state.amount_usd = value;
        if (this.state.exchange_rate > 0) {
            this.state.amount_vef = this._round(value * this.state.exchange_rate);
        } else {
            this.state.amount_vef = 0;
        }
        this._validateAmounts();
    }

    _validateAmounts() {
        this.state.is_valid_amount = this.state.amount_vef >= (this.state.original_amount_vef - 0.01);
    }

    async uploadFile(file) {
        this.state.fileUploading = true;
        this.state.proof_valid = false;
        try {
            const formData = new FormData();
            formData.append("payment_proof_file", file);
            formData.append("payment_date", this.state.payment_date);
            formData.append("payment_method", this.state.payment_method);
            formData.append("bank_origin", this.state.bank_origin);
            formData.append("bank_destination", this.state.bank_destination);
            formData.append("reference", this.state.reference);
            formData.append("amount_vef", this.state.amount_vef);
            formData.append("exchange_rate", this.state.exchange_rate);
            formData.append("amount_usd", this.state.amount_usd || 0);
            const response = await fetch("/shop/upload_payment_proof", {
                method: "POST",
                body: formData,
                credentials: "same-origin",
            });
            if (!response.ok) throw new Error();
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