/** @odoo-module **/
import { Component, useState, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

export class AddressAutofill extends Component {
    static template = "bcv_rate_update_venezuela.AddressAutofill";

    setup() {
        this.notification = useService("notification");

        onMounted(() => {
            console.log("🚀 AddressAutofill MONTADO (OWL)");
            setTimeout(() => {
                this._hideExtraFields();
                this._bindEvents();
            }, 800);
        });
    }

    _hideExtraFields() {
        console.log("🔒 Ocultando campos...");
        ['name','street','street2','city','zip','vat','country_id','state_id'].forEach(f => {
            const div = document.getElementById(`div_${f}`);
            if (div) div.style.display = 'none';
        });
    }

    _showExtraFields() {
        ['name','street','street2','city','zip','vat','country_id','state_id'].forEach(f => {
            const div = document.getElementById(`div_${f}`);
            if (div) div.style.display = '';
        });
    }

    _bindEvents() {
        const email = document.getElementById('o_email');
        const phone = document.getElementById('o_phone');

        const handler = () => {
            clearTimeout(this.timeout);
            this.timeout = setTimeout(() => {
                const e = email?.value.trim() || '';
                const p = phone?.value.trim() || '';
                if (e.length >= 5 || p.length >= 5) {
                    this._search(e, p);
                }
            }, 700);
        };

        email?.addEventListener('input', handler);
        phone?.addEventListener('input', handler);
    }

    async _search(email, phone) {
        try {
            const data = await rpc("/shop/search_partner_by_email_or_phone", { email, phone });
            if (data && Object.keys(data).length) {
                this._fillForm(data);
                this.notification.add(`✅ ${data.name} cargado`, { type: "success" });
            }
            this._showExtraFields();
        } catch (err) {
            console.error(err);
            this._showExtraFields();
        }
    }

    _fillForm(data) {
        Object.keys(data).forEach(key => {
            if (data[key]) {
                const el = document.querySelector(`[name="${key}"]`);
                if (el) el.value = data[key];
            }
        });
    }
}

registry.category("public_components").add("bcv_rate_update_venezuela.AddressAutofill", AddressAutofill);