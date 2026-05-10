/** @odoo-module **/

  import { Component } from "@odoo/owl";
  import { registry } from "@web/core/registry";

  export class OpenAI extends Component {
      static template = "ai_chatbot_0_core.OpenAI";
      static components = {};
      static props = {};

      setup() {}
  }

  registry.category("actions").add("ai_chatbot_0_core.OpenAI", OpenAI);
  