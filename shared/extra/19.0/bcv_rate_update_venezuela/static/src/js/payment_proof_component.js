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
            referenceRequired: false,
            bankOriginRequired: false,
            bankDestRequired: false,
            payment_date: new Date().toISOString().slice(0, 10),
            payment_method: 'movil',
            bank_origin: '',
            bank_destination: 'N/A',
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
                this._updateValidationMessages();
                this._checkAndTogglePaymentButton();
            }
        });

        onMounted(() => {
            console.log("✅ Componente montado");
            this._bindPaymentMethodChange();
            this._interceptPaymentButton();
        });

        onWillUnmount(() => {
            console.log("🔌 Desmontando componente, limpiando listeners");
            this._unbindPaymentMethodChange();
            if (this.observer) this.observer.disconnect();
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
        this._updateValidationMessages();
        this._checkAndTogglePaymentButton();
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
        console.log("Validación montos:", { amountVef, originalAmountVef, isValid });
        this._updateValidationMessages();
        this._checkAndTogglePaymentButton();
    }

    _updateValidationMessages() {
        if (this.state.showSection) {
            this.state.referenceRequired = !(this.state.reference && this.state.reference.trim() !== '');
            this.state.bankOriginRequired = !(this.state.bank_origin && this.state.bank_origin !== '');
            this.state.bankDestRequired = !(this.state.bank_destination && this.state.bank_destination !== '');
        } else {
            this.state.referenceRequired = false;
            this.state.bankOriginRequired = false;
            this.state.bankDestRequired = false;
        }
    }

    _checkAndTogglePaymentButton() {
        let enable = true;
        if (this.state.showSection) {
            const isAmountValid = this.state.is_valid_amount;
            const hasValidProof = this.state.proof_valid;
            const hasReference = this.state.reference && this.state.reference.trim() !== '';
            const hasBankOrigin = this.state.bank_origin && this.state.bank_origin !== '';
            const hasBankDest = this.state.bank_destination && this.state.bank_destination !== '';
            enable = isAmountValid && hasValidProof && hasReference && hasBankOrigin && hasBankDest;
            console.log("Validación botón:", { isAmountValid, hasValidProof, hasReference, hasBankOrigin, hasBankDest, enable });
        }
        this._setPaymentButtonEnabled(enable);
    }

    _setPaymentButtonEnabled(enable) {
        const paymentButton = document.querySelector('button[name="o_payment_submit_button"]') ||
                              document.querySelector('.o_payment_btn') ||
                              document.querySelector('#o_payment_form button[type="submit"]');
        if (paymentButton) {
            if (enable) {
                paymentButton.removeAttribute('disabled');
                paymentButton.classList.remove('disabled');
            } else {
                paymentButton.setAttribute('disabled', 'disabled');
                paymentButton.classList.add('disabled');
            }
        } else {
            console.warn("No se encontró el botón de pago");
        }
    }

    _interceptPaymentButton() {
        // Obtenemos el botón de pago original (sin clonar)
        const paymentButton = document.querySelector('button[name="o_payment_submit_button"]') ||
                              document.querySelector('.o_payment_btn') ||
                              document.querySelector('#o_payment_form button[type="submit"]');
        if (!paymentButton) {
            setTimeout(() => this._interceptPaymentButton(), 300);
            return;
        }
        if (paymentButton.hasAttribute('data-validated')) return;
        paymentButton.setAttribute('data-validated', 'true');
        
        // Guardamos el manejador original (si existe) para ejecutarlo después
        const self = this;
        // Añadimos nuestro evento antes que cualquier otro (capture fase)
        paymentButton.addEventListener('click', (event) => {
            if (self.state.showSection) {
                if (!self._validateBeforeSubmit()) {
                    event.preventDefault();
                    event.stopImmediatePropagation();
                    return false;
                }
            }
            // Si pasa la validación, permitimos que se ejecuten otros manejadores
            return true;
        }, { capture: true }); // capture: true para interceptar antes
    }

    _validateBeforeSubmit() {
        const hasValidProof = this.state.proof_valid;
        const hasReference = this.state.reference && this.state.reference.trim() !== '';
        const hasBankOrigin = this.state.bank_origin && this.state.bank_origin !== '';
        const hasBankDest = this.state.bank_destination && this.state.bank_destination !== '';
        const isAmountValid = this.state.is_valid_amount;
        if (!hasValidProof) {
            this.notification.add("Debe adjuntar el comprobante de pago.", { type: "danger" });
            return false;
        }
        if (!hasReference) {
            this.notification.add("La referencia es obligatoria.", { type: "danger" });
            return false;
        }
        if (!hasBankOrigin) {
            this.notification.add("Debe seleccionar el banco origen.", { type: "danger" });
            return false;
        }
        if (!hasBankDest) {
            this.notification.add("Debe seleccionar el banco destino.", { type: "danger" });
            return false;
        }
        if (!isAmountValid) {
            this.notification.add("El monto pagado debe ser igual o mayor al total de la orden.", { type: "danger" });
            return false;
        }
        return true;
    }

    _bindPaymentMethodChange() {
        let radioContainer = document.querySelector("div[id='payment_method']") ||
            document.querySelector(".o_payment_methods") ||
            document.querySelector("[data-payment-methods]") ||
            document.querySelector(".payment_methods") ||
            document.querySelector("#payment_method");
        if (radioContainer) {
            radioContainer.addEventListener("change", this._onPaymentMethodChange.bind(this));
            const radios = radioContainer.querySelectorAll('input[type="radio"]');
            radios.forEach(radio => {
                radio.addEventListener("click", this._onPaymentMethodChange.bind(this));
            });
            this._onPaymentMethodChange();
        } else {
            const targetNode = document.body;
            const config = { childList: true, subtree: true };
            this.observer = new MutationObserver((mutations, obs) => {
                let container = document.querySelector("div[id='payment_method']") ||
                    document.querySelector(".o_payment_methods") ||
                    document.querySelector("[data-payment-methods]") ||
                    document.querySelector(".payment_methods") ||
                    document.querySelector("#payment_method");
                if (container) {
                    obs.disconnect();
                    container.addEventListener("change", this._onPaymentMethodChange.bind(this));
                    const radios = container.querySelectorAll('input[type="radio"]');
                    radios.forEach(radio => {
                        radio.addEventListener("click", this._onPaymentMethodChange.bind(this));
                    });
                    this._onPaymentMethodChange();
                }
            });
            this.observer.observe(targetNode, config);
        }
    }

    _unbindPaymentMethodChange() {
        const radioContainer = document.querySelector("div[id='payment_method']") ||
            document.querySelector(".o_payment_methods") ||
            document.querySelector("[data-payment-methods]");
        if (radioContainer) {
            radioContainer.removeEventListener("change", this._onPaymentMethodChange);
        }
    }

    _onPaymentMethodChange() {
        let selectedRadio = document.querySelector('input[name="o_payment_radio"]:checked') ||
            document.querySelector('input[name="payment_method"]:checked') ||
            document.querySelector('input[type="radio"][name*="payment"]:checked') ||
            document.querySelector('.o_payment_methods input[type="radio"]:checked');
        if (!selectedRadio) {
            this.state.showSection = false;
            this._updateValidationMessages();
            this._checkAndTogglePaymentButton();
            return;
        }
        let providerId = selectedRadio.getAttribute("data-payment-option-id") ||
            selectedRadio.getAttribute("data-provider-id") ||
            selectedRadio.getAttribute("data-id") ||
            selectedRadio.value;
        let paymentText = "";
        const label = selectedRadio.closest('label') ||
            selectedRadio.parentElement.querySelector('label, span') ||
            selectedRadio.parentElement;
        if (label) paymentText = label.innerText.trim();
        const parentDiv = selectedRadio.closest('.payment_method');
        if (parentDiv) {
            const titleElem = parentDiv.querySelector('.payment_method_title, .method-name, h4, strong');
            if (titleElem) paymentText = titleElem.innerText.trim();
        }
        let shouldShow = false;
        if (providerId && this.state.transferProviderId && String(providerId) === String(this.state.transferProviderId)) {
            shouldShow = true;
        } else if (paymentText) {
            const lowerText = paymentText.toLowerCase();
            if (lowerText.includes("wire transfer") || lowerText.includes("transferencia bancaria") ||
                lowerText.includes("transferencia") || lowerText.includes("bank transfer") || lowerText.includes("wire")) {
                shouldShow = true;
            }
        }
        this.state.showSection = shouldShow;
        this._updateValidationMessages();
        this._checkAndTogglePaymentButton();
    }

    async uploadFile(file) {
        this.state.fileUploading = true;
        this.state.uploadError = null;
        this.state.uploadSuccess = false;
        this.state.proof_valid = false;
        this._setPaymentButtonEnabled(false);
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
            this._updateValidationMessages();
            this._checkAndTogglePaymentButton();
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
            this._updateValidationMessages();
            this._checkAndTogglePaymentButton();
        }
    }
}

registry.category("public_components").add("bcv_rate_update_venezuela.PaymentProofComponent", PaymentProofComponent);