/** @odoo-module **/
import { Component, useState, onWillStart, onError, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
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
        this.orm = useService("orm");

        onError((error) => {
            console.error("Error:", error);
            this.state.error = error.message;
            this.state.loading = false;
        });

        // Usar useEffect para reaccionar a cambios en el campo de plantilla.
        // OWL registrará esto como una dependencia reactiva.
        useEffect(
            (templateValue) => {
                console.log("🔄 useEffect: Cambio detectado en campaign_whatsapp_template_id:", templateValue);
                this._refresh();
            },
            () => [this.props.record.data.campaign_whatsapp_template_id]
        );

        onWillStart(async () => {
            await this._refresh();
        });
    }

    _getTemplateIdFromRecord() {
        // Obtenemos los datos completos para depurar
        const data = this.props.record?.data;
        const template = data?.campaign_whatsapp_template_id;
        
        console.log("🔍 [1] Evaluando Template ID. this.props.record.data:", data);
        console.log("🔍 [2] Template bruto:", template);
        
        if (template) {
            // Odoo 18/19: el objeto Many2one tiene formato {id: 3, display_name: "..."}
            if (template.id !== undefined) return template.id;
            // Odoo < 18: los campos Many2one suelen ser arrays: [id, "display_name"]
            if (Array.isArray(template) && template.length > 0) return template[0];
            // En algunas versiones es un objeto proxy tipo tupla
            if (template[0] !== undefined) return template[0];
            // O un objeto con res_id
            if (template.res_id) return template.res_id;
            // O el ID directo
            if (typeof template === 'number') return template;
        }
        return null;
    }

    async _refresh() {
        const templateId = this._getTemplateIdFromRecord();
        console.log("🔍 [3] ID de plantilla parseado en _refresh:", templateId);
        
        if (!templateId) {
            console.log("⚠️ No hay ID válido. Limpiando inputs.");
            this.state.inputs = [];
            this.state.templateId = null;
            return;
        }
        if (templateId === this.state.templateId) {
            console.log("✅ El ID de plantilla no ha cambiado. Omitiendo refresh.");
            return;
        }
        
        console.log("🚀 [4] Cargando esquema para plantilla ID:", templateId);
        this.state.loading = true;
        this.state.error = null;
        try {
            const result = await this.orm.read(
                "whatsapp.template",
                [templateId],
                ["parameter_schema", "has_video_header", "parameter_count"]
            );
            console.log("📊 [5] Resultado ORM read whatsapp.template:", result);
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
                console.log("⚠️ No se encontraron resultados de la plantilla en la BD.");
                this.state.inputs = [];
                this.state.templateId = null;
            }
        } catch (err) {
            console.error("❌ Error de red/ORM al cargar la plantilla:", err);
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
        } catch (e) {
            console.error("Error parseando parameter_schema:", e);
        }
        const count = template.parameter_count;
        const hasVideo = template.has_video_header || false;
        
        console.log(`🛠️ [6] Generando ${count} inputs... Schema:`, schema);

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
            let isUrl = false;
            
            if (hasVideo && i === 1) {
                placeholder = "URL del video (ej. https://.../video.mp4)";
                paramName = "URL del video";
                isUrl = true;
            } else {
                placeholder = `Valor para {{${i}}}`;
            }
            
            inputs.push({
                index: i,
                paramName: paramName,
                value: currentValues[i - 1],
                placeholder: placeholder,
                isUrl: isUrl,
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

export const dynamicParametersField = {
    component: DynamicParametersWidget,
    supportedTypes: ["text", "char"],
    fieldDependencies: [
        { name: "campaign_whatsapp_template_id", type: "many2one" }
    ],
};

registry.category("fields").add("dynamic_parameters", dynamicParametersField);