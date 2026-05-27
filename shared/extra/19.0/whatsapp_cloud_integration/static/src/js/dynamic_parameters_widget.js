/** @odoo-module **/
import { Component, useState, onWillStart, onError, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class DynamicParametersWidget extends Component {
    static template = "whatsapp_cloud_integration.DynamicParametersWidget";
    static props = { ...standardFieldProps };

    setup() {
        console.log("🚀 Widget iniciado");
        this.state = useState({
            inputs: [],
            templateId: null,
            loading: false,
            error: null,
        });
        this.notification = useService("notification");
        this._interval = null;

        onError((error) => {
            console.error("Error:", error);
            this.state.error = error.message;
            this.state.loading = false;
        });

        onWillStart(async () => {
            await this._refresh();
            this._startPolling();
        });

        onWillUnmount(() => {
            if (this._interval) clearInterval(this._interval);
        });
    }

    _startPolling() {
        this._interval = setInterval(() => {
            const newId = this._getTemplateIdFromRecord();
            if (newId !== this.state.templateId) {
                console.log("🔄 Cambio detectado, nuevo ID:", newId);
                this._refresh();
            }
        }, 500);
    }

    _getTemplateIdFromRecord() {
        // Intentar obtener el ID desde el record
        const template = this.props.record?.data?.campaign_whatsapp_template_id;
        if (template && template.res_id) return template.res_id;
        // Si es un objeto Many2one directo
        if (template && typeof template === 'number') return template;
        return null;
    }

    async _refresh() {
        const templateId = this._getTemplateIdFromRecord();
        console.log("🔍 ID de plantilla actual:", templateId);
        if (!templateId) {
            this.state.inputs = [];
            this.state.templateId = null;
            return;
        }
        if (templateId === this.state.templateId) return;
        this.state.loading = true;
        this.state.error = null;
        try {
            const result = await rpc("/web/dataset/call_kw", {
                model: "whatsapp.template",
                method: "read",
                args: [[templateId], ["parameter_schema", "has_video_header", "parameter_count"]],
                kwargs: {},
            });
            if (result && result.length) {
                const template = result[0];
                // Si el campo parameter_count no existe, usamos un valor simulado
                if (template.parameter_count === undefined) {
                    console.warn("⚠️ El campo 'parameter_count' no existe en whatsapp.template. Usando valor simulado 2.");
                    template.parameter_count = 2;
                    template.parameter_schema = template.parameter_schema || '{"1":"Video URL","2":"Texto"}';
                }
                this.state.templateId = templateId;
                this._generateInputs(template);
            } else {
                this.state.inputs = [];
                this.state.templateId = null;
            }
        } catch (err) {
            console.error(err);
            this.state.error = err.message;
            this.notification.add("Error al cargar la plantilla: " + err.message, { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    _generateInputs(template) {
        let schema = {};
        try {
            schema = JSON.parse(template.parameter_schema || "{}");
        } catch (e) {}
        const count = template.parameter_count;
        const hasVideo = template.has_video_header || false;

        let currentValues = [];
        const paramValuesStr = this.props.record?.data?.parameter_values || "[]";
        try {
            currentValues = JSON.parse(paramValuesStr);
            if (!Array.isArray(currentValues)) currentValues = [];
        } catch (e) {
            currentValues = [];
        }
        while (currentValues.length < count) currentValues.push("");
        if (currentValues.length > count) currentValues = currentValues.slice(0, count);

        const inputs = [];
        for (let i = 1; i <= count; i++) {
            let paramName = schema[i] || `Parámetro ${i}`;
            let placeholder = "";
            if (hasVideo && i === 1) {
                placeholder = "URL del video (ej. https://.../video.mp4)";
                paramName = "URL del video";
            } else {
                placeholder = `Valor para {{${i}}}`;
            }
            inputs.push({
                index: i,
                paramName: paramName,
                value: currentValues[i - 1],
                placeholder: placeholder,
            });
        }
        this.state.inputs = inputs;
        console.log("✅ Inputs generados:", inputs);
    }

    _onInputChange(event, idx) {
        const newValue = event.target.value;
        this.state.inputs[idx].value = newValue;
        this._updateParameterValues();
    }

    _updateParameterValues() {
        const values = this.state.inputs.map(input => input.value);
        const jsonValue = JSON.stringify(values);
        if (this.props.record && this.props.record.update) {
            this.props.record.update({ parameter_values: jsonValue });
        }
    }
}

registry.category("fields").add("dynamic_parameters", {
    component: DynamicParametersWidget,
});