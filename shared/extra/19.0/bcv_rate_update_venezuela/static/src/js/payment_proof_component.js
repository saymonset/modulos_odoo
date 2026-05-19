/** @odoo-module **/
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

let instanceCount = 0;

export class PaymentProofComponent extends Component {
    static template = "bcv_rate_update_venezuela.PaymentProofComponent";

    setup() {
        instanceCount++;
        if (instanceCount > 1) {
            console.warn("⚠️ PaymentProofComponent ya montado, ignorando instancia duplicada");
            this.state = useState({ showSection: false });
            return;
        }

        this.notification = useService("notification");
        this.state = useState({
            showSection: false,
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
        });

        onWillStart(async () => {
            this.state.loading = true;
            try {
                const providerId = await rpc("/payment_proof/get_transfer_provider_id");
                this.state.transferProviderId = providerId;
                const banks = await rpc("/payment_proof/get_bank_list");
                this.state.bankList = banks;
                const journalBanks = await rpc("/payment_proof/get_bank_journal_list");
                this.state.bankJournalList = journalBanks;
                const origVefSpan = document.getElementById('original_amount_vef');
                const origUsdSpan = document.getElementById('original_amount_usd');
                const rateSpan = document.getElementById('bcv_exchange_rate');
                const rateDateSpan = document.getElementById('bcv_rate_date');
                if (origVefSpan && origUsdSpan && rateSpan) {
                    this.state.original_amount_vef = this._normalizeNumber(origVefSpan.innerText);
                    this.state.original_amount_usd = this._normalizeNumber(origUsdSpan.innerText);
                    this.state.exchange_rate = this._normalizeNumber(rateSpan.innerText);
                    this.state.rate_date = rateDateSpan ? rateDateSpan.innerText : '';
                    this.state.amount_vef = this.state.original_amount_vef;
                    this.state.amount_usd = this.state.original_amount_usd;
                    this._validateAmounts();
                } else {
                    console.warn("No se encontraron los spans con los valores originales");
                    this.notification.add("No se pudieron cargar los montos de la orden.", { type: "warning" });
                }
            } catch (err) {
                console.error("Error inicial:", err);
                this.notification.add("Error al cargar datos de la orden", { type: "danger" });
            } finally {
                this.state.loading = false;
                this._updateSectionVisibility();
            }
        });

        onMounted(() => {
            console.log("✅ Componente montado");
            this._attachClickInterceptor();
            this._attachFieldEvents();
        });

        onWillUnmount(() => {
            // No es necesario limpiar eventos globales específicos
        });
    }

    _normalizeNumber(value) {
        if (value === undefined || value === null) return 0;
        if (typeof value !== 'string') value = String(value);
        let clean = value.trim();
        clean = clean.replace(/[^\d.,-]/g, '');
        const hasThousandsDot = /\.\d{3}/.test(clean);
        const hasCommaDecimal = /,\d{1,2}$/.test(clean);
        if (hasThousandsDot && hasCommaDecimal) {
            clean = clean.replace(/\./g, '');
            clean = clean.replace(',', '.');
        } else {
            clean = clean.replace(',', '.');
            const parts = clean.split('.');
            if (parts.length > 2) {
                clean = parts[0] + parts.slice(1).join('');
            }
        }
        const num = parseFloat(clean);
        return isNaN(num) ? 0 : num;
    }

    _round(value) {
        return Math.round(value * 100) / 100;
    }

    async _loadBankDetails(journalId) {
        if (!journalId || journalId === '') {
            this.state.bank_details = {
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
            };
            return;
        }
        this.state.bank_details.loading = true;
        this.state.bank_details.error = null;
        try {
            const details = await rpc("/payment_proof/get_bank_details", { journal_id: journalId });
            if (details.error) {
                this.state.bank_details.error = details.error;
            } else {
                this.state.bank_details = { ...this.state.bank_details, ...details, loading: false };
            }
        } catch (err) {
            console.error("Error cargando detalles del banco:", err);
            this.state.bank_details.error = "No se pudieron cargar los datos del banco";
            this.state.bank_details.loading = false;
        }
    }

    _updateField(event) {
        const field = event.currentTarget.dataset.field;
        let value = event.target.value;
        this.state[field] = value;
        if (field === 'bank_destination') {
            if (value) this._loadBankDetails(value);
            else {
                this.state.bank_details = { ...this.state.bank_details, bank_name: '', account_number: '', loading: false, error: null };
            }
        }
        this._updateSectionVisibility();
    }

    _onAmountVefInput(event) {
        let rawValue = event.target.value;
        let value = this._normalizeNumber(rawValue);
        this.state.amount_vef = value;
        if (this.state.exchange_rate > 0) {
            this.state.amount_usd = this._round(value / this.state.exchange_rate);
        } else {
            this.state.amount_usd = 0;
        }
        this._validateAmounts();
    }

    _onAmountUsdInput(event) {
        let rawValue = event.target.value;
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
        const amountVef = this._normalizeNumber(this.state.amount_vef);
        const originalAmountVef = this._normalizeNumber(this.state.original_amount_vef);
        const isValid = amountVef >= (originalAmountVef - 0.01);
        this.state.is_valid_amount = isValid;
        this._updateSectionVisibility();
    }

    _isTransferSelected() {
        const selectedRadio = document.querySelector('input[name="o_payment_radio"]:checked');
        if (!selectedRadio) return false;
        let providerId = selectedRadio.getAttribute("data-payment-option-id") ||
                         selectedRadio.getAttribute("data-provider-id") ||
                         selectedRadio.value;
        if (providerId && this.state.transferProviderId && String(providerId) === String(this.state.transferProviderId)) {
            return true;
        }
        const container = selectedRadio.closest('.o_payment_option, .payment_method');
        let text = "";
        if (container) text = container.innerText.toLowerCase();
        else if (selectedRadio.parentElement) text = selectedRadio.parentElement.innerText.toLowerCase();
        return text.includes("transferencia") || text.includes("bank transfer") || text.includes("wire transfer");
    }

    _updateSectionVisibility() {
        const isTransfer = this._isTransferSelected();
        if (this.state.showSection !== isTransfer) {
            this.state.showSection = isTransfer;
        }
    }

    _getFieldValue(fieldId) {
        const el = document.getElementById(fieldId);
        return el ? el.value : '';
    }

    _validateRequiredFields() {
        if (!this._isTransferSelected()) return { valid: true, missing: [] };

        const bankOrigin = this._getFieldValue('bank_origin');
        const bankDest = this._getFieldValue('bank_destination');
        const reference = this._getFieldValue('reference');
        const amountOk = this.state.is_valid_amount;
        const proofOk = this.state.proof_valid;

        const missing = [];
        if (!bankOrigin || bankOrigin === '') missing.push("Banco origen");
        if (!bankDest || bankDest === '') missing.push("Banco destino");
        if (!reference || reference.trim() === '') missing.push("Referencia");
        if (!proofOk) missing.push("Comprobante de pago");
        if (!amountOk) missing.push(`Monto válido (debe ser ≥ ${this.state.original_amount_vef} Bs.)`);

        return { valid: missing.length === 0, missing };
    }

    _attachClickInterceptor() {
        // Buscar el botón de pago (puede tardar en aparecer)
        const findButton = () => {
            const btn = document.querySelector('button[name="o_payment_submit_button"]');
            if (btn) {
                if (btn.getAttribute('data-validated')) return;
                btn.setAttribute('data-validated', 'true');
                // Usamos capture: true para interceptar antes que otros listeners
                btn.addEventListener('click', (event) => {
                    const { valid, missing } = this._validateRequiredFields();
                    if (!valid) {
                        event.preventDefault();
                        event.stopImmediatePropagation();
                        const msg = "❌ No se puede procesar el pago. Complete:\n\n- " + missing.join("\n- ");
                        alert(msg);
                        this.notification.add(msg, { type: "danger" });
                        return false;
                    }
                    return true;
                }, { capture: true });
            } else {
                setTimeout(findButton, 200);
            }
        };
        findButton();
    }

    _attachFieldEvents() {
        const refresh = () => this._updateSectionVisibility();

        // Radios de pago
        document.addEventListener('change', (e) => {
            if (e.target && e.target.getAttribute('name') === 'o_payment_radio') refresh();
        });
        document.addEventListener('click', (e) => {
            const radio = e.target.closest('input[name="o_payment_radio"]');
            if (radio) refresh();
        });

        // Campos del comprobante
        const fields = ['bank_origin', 'bank_destination', 'reference', 'payment_date', 'payment_method'];
        fields.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('change', refresh);
                if (el.tagName === 'INPUT' || el.tagName === 'SELECT') {
                    el.addEventListener('input', refresh);
                }
            }
        });

        const amountVef = document.getElementById('amount_vef');
        if (amountVef) amountVef.addEventListener('input', (e) => { this._onAmountVefInput(e); refresh(); });
        const amountUsd = document.getElementById('amount_usd');
        if (amountUsd) amountUsd.addEventListener('input', (e) => { this._onAmountUsdInput(e); refresh(); });

        refresh();
    }

    async uploadFile(file) {
        this.state.fileUploading = true;
        this.state.uploadError = null;
        this.state.uploadSuccess = false;
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
            formData.append("amount_usd", this.state.amount_usd);
            const response = await fetch("/shop/upload_payment_proof", {
                method: "POST",
                body: formData,
                credentials: "same-origin",
            });
            if (!response.ok) throw new Error("Error al subir el archivo");
            this.notification.add("Comprobante adjuntado correctamente.", { type: "success" });
            this.state.uploadSuccess = true;
            this.state.proof_valid = true;
        } catch (err) {
            this.state.uploadError = err.message;
            this.state.proof_valid = false;
            this.notification.add("Error al adjuntar el comprobante. Intente nuevamente.", { type: "danger" });
        } finally {
            this.state.fileUploading = false;
            this._updateSectionVisibility();
        }
    }

    _handleFileChange(event) {
        const file = event.target.files[0];
        if (file) {
            this.state.selectedFileName = file.name;
            this.state.proof_valid = false;
            this.state.uploadSuccess = false;
            this.state.uploadError = null;
            this.uploadFile(file);
        } else {
            this.state.selectedFileName = null;
            this.state.proof_valid = false;
            this.state.uploadSuccess = false;
            this._updateSectionVisibility();
        }
    }
}

registry.category("public_components").add("bcv_rate_update_venezuela.PaymentProofComponent", PaymentProofComponent);