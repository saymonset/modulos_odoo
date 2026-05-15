/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.WebsiteCheckoutAutofill = publicWidget.Widget.extend({
    selector: '.oe_website_sale .checkout_autoformat',
    events: {
        'change input[name="email"]': '_onEmailChange',
        'change input[name="phone"]': '_onPhoneChange',
    },

    /**
     * @override
     */
    start: function () {
        this.$name = this.$('input[name="name"]');
        this.$street = this.$('input[name="street"]');
        this.$street2 = this.$('input[name="street2"]');
        this.$city = this.$('input[name="city"]');
        this.$zip = this.$('input[name="zip"]');
        this.$country = this.$('select[name="country_id"]');
        this.$state = this.$('select[name="state_id"]');
        this.$vat = this.$('input[name="vat"]');
        console.log("WebsiteCheckoutAutofill widget started");
        return this._super.apply(this, arguments);
    },

    _onEmailChange: function (ev) {
        const email = $(ev.currentTarget).val();
        if (email && email.includes('@')) {
            console.log("Searching for partner with email:", email);
            this._fetchPartnerData({email: email});
        }
    },

    _onPhoneChange: function (ev) {
        const phone = $(ev.currentTarget).val();
        if (phone && phone.length > 5) {
            console.log("Searching for partner with phone:", phone);
            this._fetchPartnerData({phone: phone});
        }
    },

    _fetchPartnerData: async function (params) {
        try {
            const data = await rpc("/shop/get_partner_data", params);
            if (data && data.name && !data.has_user) {
                console.log("Partner data found, auto-filling:", data);
                this._fillForm(data);
            } else if (data.has_user) {
                console.log("Partner found but has user account. Auto-fill disabled for security.");
            }
        } catch (error) {
            console.error("Error fetching partner data:", error);
        }
    },

    _fillForm: function (data) {
        // Fill fields only if they are currently empty
        if (data.name && !this.$name.val()) this.$name.val(data.name);
        if (data.street && !this.$street.val()) this.$street.val(data.street);
        if (data.street2 && !this.$street2.val()) this.$street2.val(data.street2);
        if (data.city && !this.$city.val()) this.$city.val(data.city);
        if (data.zip && !this.$zip.val()) this.$zip.val(data.zip);
        if (data.vat && !this.$vat.val()) this.$vat.val(data.vat);
        
        if (data.country_id && this.$country.val() != data.country_id) {
            this.$country.val(data.country_id).trigger('change');
            
            // Wait for states to load if country changed
            if (data.state_id) {
                const self = this;
                const checkState = setInterval(() => {
                    if (self.$state.find('option[value="' + data.state_id + '"]').length > 0) {
                        self.$state.val(data.state_id).trigger('change');
                        clearInterval(checkState);
                    }
                }, 100);
                setTimeout(() => clearInterval(checkState), 3000); // Timeout after 3s
            }
        } else if (data.state_id) {
            this.$state.val(data.state_id).trigger('change');
        }
    },
});

export default publicWidget.registry.WebsiteCheckoutAutofill;
