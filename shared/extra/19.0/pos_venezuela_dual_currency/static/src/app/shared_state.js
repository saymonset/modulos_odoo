/** @odoo-module **/

export const posState = {
    currentOrder: null,
    paymentMethodName: '',
    is_igtf: false,

    setCurrentOrder(order) {
        this.currentOrder = order;
    },
    getCurrentOrder() {
        return this.currentOrder;
    },
    setPaymentMethodName(name) {
        this.paymentMethodName = name;
    },
    getPaymentMethodName() {
        return this.paymentMethodName;
    },
};
