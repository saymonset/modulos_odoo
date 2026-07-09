/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { CustomButton } from "./custom_button/custom_button";

patch(Orderline, {
    components: {
        ...Orderline.components,
        CustomButton,
    },
});
