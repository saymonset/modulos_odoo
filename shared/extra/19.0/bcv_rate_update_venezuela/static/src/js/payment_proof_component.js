/** @odoo-module **/
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

export class PaymentProofComponent extends Component {
    static template = "bcv_rate_update_venezuela.PaymentProofComponent";

    setup() {
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

            referenceRequired: false,
            bankOriginRequired: false,
            bankDestRequired: false,

            payment_date: new Date().toISOString().slice(0, 10),
            payment_method: 'movil',
            bank_origin: '',
            bank_destination: '',
            reference: '',
            amount_vef: 0,
            exchange_rate: 0,
            amount_usd: 0,
            original_amount_vef: 0,
            is_valid_amount: true,
            rate_date: '',

            bankList: [],
            bankJournalList: [],

            bank_details: { bank_name: '', account_number: '', loading: false, error: null },
        });

        this.observers = [];
        this.debounceTimer = null;

        onWillStart(async () => {
            this.state.loading = true;
            try {
                const [providerId, banks, journalBanks] = await Promise.all([
                    rpc("/payment_proof/get_transfer_provider_id"),
                    rpc("/payment_proof/get_bank_list"),
                    rpc("/payment_proof/get_bank_journal_list")
                ]);

                this.state.transferProviderId = providerId;
                this.state.bankList = banks;
                this.state.bankJournalList = journalBanks;
                this._loadOriginalAmounts();
            } catch (err) {
                console.error(err);
            } finally {
                this.state.loading = false;
                this._forceCheckButton();
            }
        });

        onMounted(() => {
            console.log("✅ Componente montado - Modo:", window.innerWidth < 768 ? "MÓVIL" : "DESKTOP");
            this._bindEvents();
            setTimeout(() => this._onPaymentMethodChange(), 800);
        });

        onWillUnmount(() => this._cleanup());
    }

    _loadOriginalAmounts() {
        const origVef = document.getElementById('original_amount_vef');
        if (origVef) {
            this.state.original_amount_vef = this._normalizeNumber(origVef.innerText);
            this.state.amount_vef = this.state.original_amount_vef;
        }
    }

    _normalizeNumber(value) {
        if (!value) return 0;
        let clean = String(value).trim().replace(/[^\d.,-]/g, '').replace(',', '.');
        const num = parseFloat(clean);
        return isNaN(num) ? 0 : num;
    }

    _debounce(fn, delay = 150) {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(fn, delay);
    }

    // ==================== BOTÓN (MEJORADO PARA MÓVIL) ====================
    _findPaymentButton() {
        return document.querySelector('button[name="o_payment_submit_button"]') ||
               document.querySelector('.o_payment_btn') ||
               document.querySelector('#o_payment_form button[type="submit"]') ||
               document.querySelector('button.btn-primary[type="submit"]');
    }

    _setPaymentButtonEnabled(enable) {
        const btn = this._findPaymentButton();
        if (!btn) {
            console.warn("⚠️ Botón de pago no encontrado");
            return;
        }

        if (enable) {
            btn.removeAttribute('disabled');
            btn.classList.remove('disabled', 'o-disabled');
        } else {
            btn.setAttribute('disabled', 'disabled');
            btn.classList.add('disabled', 'o-disabled');
        }

        console.log(`🔘 Botón ${enable ? 'HABILITADO' : 'DESHABILITADO'} - Modo: ${window.innerWidth < 768 ? 'Móvil' : 'Desktop'}`);
    }

    _forceCheckButton() {
        this._updateValidationMessages();
        this._checkAndTogglePaymentButton();
    }

    // ==================== EVENTOS ====================
    _bindEvents() {
        this._paymentHandler = (e) => {
            if (e.target?.type === 'radio') this._onPaymentMethodChange();
        };
        document.addEventListener('change', this._paymentHandler);

        const mo = new MutationObserver(() => this._debounce(() => this._onPaymentMethodChange(), 300));
        mo.observe(document.body, { childList: true, subtree: true });
        this.observers.push(mo);

        this._setupPaymentButton();
    }

    _setupPaymentButton() {
        let attempts = 0;
        const tryFind = () => {
            const btn = this._findPaymentButton();
            if (btn && !btn.hasAttribute('data-proof-listener')) {
                btn.setAttribute('data-proof-listener', 'true');
                btn.addEventListener('click', this._onPaymentSubmit.bind(this), { capture: true });
                console.log("✅ Listener agregado al botón o_payment_submit_button");
            }
            if (attempts++ < 10) setTimeout(tryFind, 600);
        };
        tryFind();
    }

    _cleanup() {
        document.removeEventListener('change', this._paymentHandler);
        this.observers.forEach(o => o.disconnect());
        clearTimeout(this.debounceTimer);
    }

    // ==================== LÓGICA PRINCIPAL ====================
    _onPaymentMethodChange() {
        const radio = document.querySelector('input[name="o_payment_radio"]:checked') ||
                      document.querySelector('input[name*="payment"]:checked');

        let shouldShow = false;
        if (radio) {
            const pid = radio.getAttribute("data-payment-option-id") || 
                        radio.getAttribute("data-provider-id") || radio.value || '';

            const text = (radio.closest('label')?.innerText || radio.parentElement?.innerText || '').toLowerCase();

            if (String(pid) === String(this.state.transferProviderId) || 
                text.includes("transferencia") || text.includes("pago móvil") || text.includes("bank transfer")) {
                shouldShow = true;
            }
        }

        this.state.showSection = shouldShow;
        this._forceCheckButton();
    }

    _updateField = (event) => {
        const field = event.currentTarget.dataset.field;
        this.state[field] = event.target.value?.trim() || '';

        if (field === 'bank_destination' && this.state[field]) {
            this._loadBankDetails(this.state[field]);
        }

        this._updateValidationMessages();
        this._debounce(() => this._checkAndTogglePaymentButton(), 120);
    };

    _onAmountVefInput = (event) => {
        this.state.amount_vef = this._normalizeNumber(event.target.value);
        if (this.state.exchange_rate > 0) {
            this.state.amount_usd = Math.round((this.state.amount_vef / this.state.exchange_rate) * 100) / 100;
        }
        this._validateAmounts();
    };

    _validateAmounts() {
        this.state.is_valid_amount = this.state.amount_vef >= (this.state.original_amount_vef - 0.01);
        this._debounce(() => this._checkAndTogglePaymentButton(), 120);
    }

    _updateValidationMessages() {
        if (!this.state.showSection) {
            this.state.referenceRequired = this.state.bankOriginRequired = this.state.bankDestRequired = false;
            return;
        }

        this.state.referenceRequired = !this.state.reference?.trim();
        this.state.bankOriginRequired = !this.state.bank_origin;
        this.state.bankDestRequired = !this.state.bank_destination;
    }

    _checkAndTogglePaymentButton() {
        if (!this.state.showSection) {
            this._setPaymentButtonEnabled(true);
            return;
        }

        const enable = this.state.is_valid_amount &&
                       this.state.proof_valid &&
                       !!this.state.reference?.trim() &&
                       !!this.state.bank_origin &&
                       !!this.state.bank_destination;

        this._setPaymentButtonEnabled(enable);
    }

    _onPaymentSubmit(event) {
        if (!this.state.showSection) return;
        if (!this._validateBeforeSubmit()) {
            event.preventDefault();
            event.stopImmediatePropagation();
        }
    }

    _validateBeforeSubmit() {
        if (!this.state.proof_valid || !this.state.reference?.trim() || 
            !this.state.bank_origin || !this.state.bank_destination || !this.state.is_valid_amount) {
            this.notification.add("Por favor complete todos los campos obligatorios.", { type: "danger" });
            return false;
        }
        return true;
    }

    // ==================== UPLOAD ====================
    async _loadBankDetails(journalId) {
        if (!journalId) return;
        this.state.bank_details.loading = true;
        try {
            const data = await rpc("/payment_proof/get_bank_details", { journal_id: journalId });
            this.state.bank_details = { ...this.state.bank_details, ...data, loading: false, error: null };
        } catch (err) {
            this.state.bank_details.error = "Error cargando banco";
            this.state.bank_details.loading = false;
        }
    }

    async uploadFile(file) {
        if (!file) return;
        this.state.fileUploading = true;
        this.state.proof_valid = false;
        this._setPaymentButtonEnabled(false);

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

        try {
            const res = await fetch("/shop/upload_payment_proof", { method: "POST", body: formData });
            if (res.ok) {
                this.state.uploadSuccess = true;
                this.state.proof_valid = true;
                this.notification.add("Comprobante subido correctamente", { type: "success" });
            } else {
                throw new Error();
            }
        } catch {
            this.state.uploadError = "Error al subir";
            this.notification.add("Error al subir comprobante", { type: "danger" });
        } finally {
            this.state.fileUploading = false;
            this._forceCheckButton();
        }
    }

    _handleFileChange = (event) => {
        const file = event.target.files[0];
        if (file) {
            this.state.selectedFileName = file.name;
            this.uploadFile(file);
        }
    };
}

registry.category("public_components").add("bcv_rate_update_venezuela.PaymentProofComponent", PaymentProofComponent);