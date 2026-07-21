/** @odoo-module **/
import { Component, useState, onWillStart, onWillDestroy } from "@odoo/owl";
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
            amount_cop: 0,
            cop_rate: 0,
            show_cop: false,
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

        this._syncPaymentButtonState();

        onWillStart(async () => {
            try {
                const banks = await rpc("/payment_proof/get_bank_list");
                this.state.bankList = banks;
                const journalBanks = await rpc("/payment_proof/get_bank_journal_list");
                this.state.bankJournalList = journalBanks;
                const origVefSpan = document.getElementById('original_amount_vef');
                const rateSpan = document.getElementById('bcv_exchange_rate');
                const rateDateSpan = document.getElementById('bcv_rate_date');
                const origCopSpan = document.getElementById('original_amount_cop');
                const copRateSpan = document.getElementById('cop_exchange_rate');
                if (origVefSpan && rateSpan) {
                    this.state.original_amount_vef = this._normalizeNumber(origVefSpan.innerText);
                    this.state.exchange_rate = this._normalizeNumber(rateSpan.innerText);
                    this.state.rate_date = rateDateSpan ? rateDateSpan.innerText : '';
                    this.state.amount_vef = this.state.original_amount_vef;
                    this.state.amount_usd = this._round(this.state.amount_vef / this.state.exchange_rate);
                    this._validateAmounts();
                }
                if (origCopSpan && copRateSpan) {
                    this.state.show_cop = true;
                    this.state.cop_rate = this._normalizeNumber(copRateSpan.innerText);
                    this.state.amount_cop = this._round(this.state.amount_usd * this.state.cop_rate);
                }
            } catch (err) {
                console.error(err);
                this.notification.add("Error al cargar datos de pago", { type: "danger" });
            } finally {
                this._syncPaymentButtonState();
            }
        });

        onWillDestroy(() => {
            delete document.body.dataset.bcvPaymentProofValid;
        });
    }

    _isValid() {
        return this.state.bank_origin
            && this.state.bank_destination
            && this.state.reference
            && this.state.uploadSuccess
            && this.state.is_valid_amount;
    }

    _syncPaymentButtonState() {
        const disabled = !this._isValid();
        document.body.dataset.bcvPaymentProofValid = disabled ? '0' : '1';
        document.querySelectorAll('button[name="o_payment_submit_button"], #payment_submit_btn').forEach(btn => {
            btn.disabled = disabled;
            btn.classList.toggle('disabled', disabled);
            btn.classList.toggle('pe-none', disabled);
            btn.classList.toggle('opacity-50', disabled);
        });
    }

    _normalizeNumber(v) {
        let s = String(v).replace(/[^\d.,-]/g, '').trim();
        let lastDot = s.lastIndexOf('.');
        let lastComma = s.lastIndexOf(',');
        if (lastComma > lastDot) {
            s = s.replace(/\./g, '').replace(',', '.');
        } else if (lastDot > lastComma) {
            s = s.replace(/,/g, '');
        } else {
            s = s.replace(',', '.');
        }
        let n = parseFloat(s);
        return isNaN(n) ? 0 : n;
    }

    _round(v) {
        return Math.round(v * 100) / 100;
    }

    /**
     * Comprime imagen en cliente usando Canvas.
     * Reduce a max 1920px, calidad 0.7, formato JPEG.
     * Soluciona subida de fotos grandes desde cámara móvil.
     */
    _compressImage(file) {
        return new Promise((resolve, reject) => {
            if (!file.type.startsWith('image/')) {
                resolve(file);
                return;
            }
            const img = new Image();
            img.onload = () => {
                const MAX_SIZE = 1920;
                let { width, height } = img;
                if (width <= MAX_SIZE && height <= MAX_SIZE && file.size < 1 * 1024 * 1024) {
                    resolve(file);
                    return;
                }
                if (width > height && width > MAX_SIZE) {
                    height = Math.round(height * MAX_SIZE / width);
                    width = MAX_SIZE;
                } else if (height > MAX_SIZE) {
                    width = Math.round(width * MAX_SIZE / height);
                    height = MAX_SIZE;
                }
                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);
                canvas.toBlob((blob) => {
                    const name = file.name || 'comprobante.jpg';
                    resolve(new File([blob], name, { type: 'image/jpeg', lastModified: Date.now() }));
                }, 'image/jpeg', 0.7);
            };
            img.onerror = () => reject(new Error('No se pudo leer la imagen'));
            const reader = new FileReader();
            reader.onload = (e) => { img.src = e.target.result; };
            reader.onerror = () => reject(new Error('Error al leer el archivo'));
            reader.readAsDataURL(file);
        });
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
        this._syncPaymentButtonState();
    }

    _onAmountVefInput(e) {
        let rawValue = e.target.value;
        let value = this._normalizeNumber(rawValue);
        this.state.amount_vef = value;
        if (this.state.exchange_rate > 0) {
            this.state.amount_usd = this._round(value / this.state.exchange_rate);
            if (this.state.show_cop && this.state.cop_rate > 0) {
                this.state.amount_cop = this._round(this.state.amount_usd * this.state.cop_rate);
            }
        } else {
            this.state.amount_usd = 0;
            this.state.amount_cop = 0;
        }
        this._validateAmounts();
        this._syncPaymentButtonState();
    }

    _onAmountUsdInput(e) {
        let rawValue = e.target.value;
        let value = this._normalizeNumber(rawValue);
        this.state.amount_usd = value;
        if (this.state.exchange_rate > 0) {
            this.state.amount_vef = this._round(value * this.state.exchange_rate);
            if (this.state.show_cop && this.state.cop_rate > 0) {
                this.state.amount_cop = this._round(value * this.state.cop_rate);
            }
        } else {
            this.state.amount_vef = 0;
            this.state.amount_cop = 0;
        }
        this._validateAmounts();
        this._syncPaymentButtonState();
    }

    _onAmountCopInput(e) {
        let rawValue = e.target.value;
        let value = this._normalizeNumber(rawValue);
        this.state.amount_cop = value;
        if (this.state.cop_rate > 0) {
            this.state.amount_usd = this._round(value / this.state.cop_rate);
            if (this.state.exchange_rate > 0) {
                this.state.amount_vef = this._round(this.state.amount_usd * this.state.exchange_rate);
            }
        } else {
            this.state.amount_usd = 0;
            this.state.amount_vef = 0;
        }
        this._validateAmounts();
        this._syncPaymentButtonState();
    }

    _validateAmounts() {
        this.state.is_valid_amount = this.state.amount_vef >= (this.state.original_amount_vef - 0.01);
        this._syncPaymentButtonState();
    }

    async uploadFile(file) {
        this.state.fileUploading = true;
        this.state.proof_valid = false;
        this.state.uploadError = null;
        try {
            if (file.size > 10 * 1024 * 1024) {
                throw new Error('La imagen es demasiado grande. Máximo 10MB.');
            }
            const compressedFile = await this._compressImage(file);
            const formData = new FormData();
            formData.append("payment_proof_file", compressedFile);
            formData.append("payment_date", this.state.payment_date);
            formData.append("payment_method", this.state.payment_method);
            formData.append("bank_origin", this.state.bank_origin);
            formData.append("bank_destination", this.state.bank_destination);
            formData.append("reference", this.state.reference);
            formData.append("amount_vef", this.state.amount_vef || 0);
            formData.append("exchange_rate", this.state.exchange_rate || 0);
            formData.append("amount_usd", this.state.amount_usd || 0);
            formData.append("amount_cop", this.state.amount_cop || 0);
            const response = await fetch("/shop/upload_payment_proof", {
                method: "POST",
                body: formData,
                credentials: "same-origin",
            });
            if (!response.ok) {
                const text = await response.text();
                if (text === 'MONTO_INSUFICIENTE') {
                    throw new Error('El monto pagado es menor al total de la orden');
                }
                throw new Error('Error al subir. Intenta con una imagen más pequeña o verifica tu conexión.');
            }
            this.notification.add("Comprobante subido correctamente", { type: "success" });
            this.state.uploadSuccess = true;
            this.state.proof_valid = true;
            this._syncPaymentButtonState();
        } catch (err) {
            this.state.uploadError = err.message || "Error al subir";
            this.notification.add(this.state.uploadError, { type: "danger" });
        } finally {
            this.state.fileUploading = false;
            this._syncPaymentButtonState();
        }
    }

    _handleFileChange(e) {
        const file = e.target.files[0];
        if (file) {
            this.state.selectedFileName = file.name || 'comprobante.jpg';
            this.state.proof_valid = false;
            this.uploadFile(file);
        } else {
            this.state.selectedFileName = null;
            this.state.proof_valid = false;
            this._syncPaymentButtonState();
        }
    }
}

registry.category("public_components").add("bcv_rate_update_venezuela.PaymentProofComponent", PaymentProofComponent);
