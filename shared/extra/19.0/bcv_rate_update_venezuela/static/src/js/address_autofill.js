/** @odoo-module **/
import { Component, useState, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

const FIELD_WRAPPERS = [
    'div_name',
    'div_email',
    'company_name_div',
    'div_vat',
    'div_street',
    'div_street2',
    'div_city',
    'div_zip',
    'div_country',
    'div_state',
];

const FIELD_INPUTS = {
    name: 'o_name',
    email: 'o_email',
    company_name: 'o_company_name',
    vat: 'o_vat',
    street: 'o_street',
    street2: 'o_street2',
    city: 'o_city',
    zip: 'o_zip',
    country_id: 'o_country_id',
    state_id: 'o_state_id',
};

export class AddressAutofill extends Component {
    static template = "bcv_rate_update_venezuela.AddressAutofill";

    setup() {
        this.state = useState({
            status: 'idle', // idle | loading | found | not_found
            name: '',
        });

        onMounted(() => {
            const phone = document.getElementById('o_phone');
            if (!phone) return;

            const trigger = () => this._searchByPhone(phone.value);
            phone.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    trigger();
                }
            });
            phone.addEventListener('blur', trigger);
        });
    }

    _setStatus(status, name = '') {
        this.state.status = status;
        this.state.name = name || '';
    }

    _revealFields() {
        FIELD_WRAPPERS.forEach(id => {
            const div = document.getElementById(id);
            if (div) div.style.display = '';
        });
    }

    async _searchByPhone(rawPhone) {
        if (this.state.status === 'loading') return;

        const digits = (rawPhone || '').replace(/\D/g, '');
        if (digits.length < 7) {
            this._revealFields();
            this._setStatus('not_found');
            return;
        }

        this._setStatus('loading');
        try {
            const data = await rpc("/shop/find_partner_by_phone", { phone: rawPhone });
            if (data && data.found) {
                this._fillForm(data.partner);
                this._setStatus('found', data.partner.name || '');
            } else {
                this._revealFields();
                this._setStatus('not_found');
            }
        } catch (err) {
            console.error(err);
            this._revealFields();
            this._setStatus('not_found');
        }
    }

    _fillForm(partner) {
        Object.entries(FIELD_INPUTS).forEach(([key, id]) => {
            const value = partner[key];
            if (value) {
                const el = document.getElementById(id);
                if (el) el.value = value;
            }
        });
    }

    _notYou() {
        this._revealFields();
        this._setStatus('not_found');
    }
}

registry.category("public_components").add("bcv_rate_update_venezuela.AddressAutofill", AddressAutofill);