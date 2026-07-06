/** @odoo-module **/

/**
 * Estado compartido entre componentes POS.
 * - currentOrder: orden activa en PaymentScreen
 * - paymentMethodName: nombre del método de pago seleccionado
 * - is_igtf: si el método actual tiene IGTF habilitado
 */
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
