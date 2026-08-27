#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Actualiza el workflow exportado de n8n para que el nodo
`Separar_variables_en_json` consuma `flow_map` de Odoo.

Reemplaza SOLO el bloque `const mapeoFlow = {...};` del jsCode:
  - Los defaults actuales quedan como `mapeoFlowBase` (fallback sin flow_map).
  - Se hace merge dinámico con `flow_map` (Odoo gana en conflictos).
El resto del nodo y del workflow quedan intactos.

Uso:
    python3 update_flow_map.py [workflow.json] [salida.json]

Salida con json.dump(indent=2, ensure_ascii=False).
"""

import json
import re
import sys

NODE_NAME = 'Separar_variables_en_json'
BLOCK_RE = re.compile(r'const mapeoFlow = \{.*?\n\};', re.DOTALL)

NEW_BLOCK_TEMPLATE = """const mapeoFlowBase = {mapeo};

// Merge dinámico: Odoo amplía el mapeo base con flow_map (defaults preservados).
let flowMapOdoo = {};
try {
  flowMapOdoo = $('Obtener_configuracion_agente').item.json.flow_map || {};
} catch (e) {
  flowMapOdoo = {};
}
const mapeoFlow = Object.assign({}, mapeoFlowBase, flowMapOdoo);"""


def find_node(workflow, name):
    for node in workflow.get('nodes', []):
        if node.get('name') == name:
            return node
    return None


def build_new_block(js_code):
    match = BLOCK_RE.search(js_code)
    if not match:
        raise ValueError(
            'No se encontró el bloque "const mapeoFlow = {...};" en el jsCode '
            f'del nodo "{NODE_NAME}".')
    mapeo_literal = match.group(0)
    mapeo = mapeo_literal[len('const mapeoFlow = '):-1]
    return match, NEW_BLOCK_TEMPLATE.replace('{mapeo}', mapeo)


def update_js_code(js_code):
    match, new_block = build_new_block(js_code)
    return js_code[:match.start()] + new_block + js_code[match.end():]


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    in_path, out_path = sys.argv[1], sys.argv[2]

    with open(in_path, encoding='utf-8') as f:
        data = json.load(f)

    workflow = data[0] if isinstance(data, list) else data
    node = find_node(workflow, NODE_NAME)
    if not node:
        raise SystemExit(f'Nodo "{NODE_NAME}" no encontrado en {in_path}.')

    js_code = node['parameters']['jsCode']
    node['parameters']['jsCode'] = update_js_code(js_code)

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f'✅ Workflow "{workflow.get("name")}": bloque mapeoFlow actualizado.')
    print(f'   Entrada : {in_path}')
    print(f'   Salida  : {out_path}')


if __name__ == '__main__':
    main()