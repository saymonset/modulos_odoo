#!/usr/bin/env node
/**
 * Replay test for the n8n node `Separar_variables_en_json` (SPEC 13).
 *
 * Executes the actual jsCode from the workflow JSON against captured scenarios
 * to verify: de-nesting of nested JSON, deterministic MENU routing (branded
 * menu with isMenu=true) and no regression on informative intents.
 *
 * Run: node test_replay_menu.js
 */

const fs = require('fs');
const path = require('path');

const WORKFLOW = path.join(__dirname, 'ycloud_create_lead_0_con_menu_whatsapp.json');

function loadNodeCode(nodeName) {
  const data = JSON.parse(fs.readFileSync(WORKFLOW, 'utf8'));
  const node = data.nodes.find((n) => n.name === nodeName);
  if (!node) throw new Error(`Node ${nodeName} not found`);
  return node.parameters.jsCode;
}

// Sample branded system_prompt (matches Odoo render_prompt output).
function buildSystemPrompt(brand, menuText) {
  return [
    '=== INTENCIONES (clasifica en este orden de prioridad) ===',
    '1. MENU — palabras clave: hola,menu,menu_principal,menú,opciones,ayuda → tipoPregunta "MENU" (muestra el menú)',
    '2. PRECIOS — palabras clave: precio,costo,cuánto',
    '',
    '=== MENÚ DE OPCIONES ===',
    menuText,
    '=== FLUJOS DISPONIBLES (usa EXACTAMENTE estos valores) ===',
    '1. flow_name: flujo_agendamiento_precios',
  ].join('\n');
}

// Mock n8n environment and run the node code.
function runNode(items, agentConfig) {
  const code = loadNodeCode('Separar_variables_en_json');
  const $input = { all: () => items };
  const $ = (name) => ({
    item: { json: agentConfig[name] || {} },
  });
  // eslint-disable-next-line no-new-func
  const fn = new Function('$input', '$', code);
  return fn($input, $);
}

const brand = 'KARLA CAMPOVERDE';
const menuText = `*${brand}*\n¡Hola! 👋 ¿Qué necesitas hoy?\n1️⃣ Servicios\n2️⃣ Precios`;
const systemPrompt = buildSystemPrompt(brand, menuText);
const agentConfig = {
  Obtener_configuracion_agente: {
    system_prompt: systemPrompt,
    fallback_message: 'Disculpa, no entendí.',
    flow_map: { Agendamiento_Precios: 'flujo_agendamiento_precios' },
    menu_enabled: true,
  },
};

// Mock del modo conversacional (SPEC 18): menu_enabled=false, sin sección
// de menú en el system prompt.
const agentConfigConversacional = {
  Obtener_configuracion_agente: {
    system_prompt: buildSystemPrompt(brand, '').replace(
      '=== MENÚ DE OPCIONES ===\n\n=== FLUJOS', '=== FLUJOS'),
    fallback_message: 'Disculpa, no entendí.',
    flow_map: { Agendamiento_Precios: 'flujo_agendamiento_precios' },
    menu_enabled: false,
  },
};

let passed = 0;
let failed = 0;

function check(name, condition, detail) {
  if (condition) {
    passed++;
    console.log(`  ✓ ${name}`);
  } else {
    failed++;
    console.log(`  ✗ ${name}  ${detail ? '-> ' + JSON.stringify(detail) : ''}`);
  }
}

function baseItem(text, output) {
  return {
    json: {
      text,
      output,
      session_id: 's1',
      conversation_id: 'c1',
      account_id: 'a1',
      platform: 'whatsapp',
      timestamp_actividad: 'now',
    },
  };
}

console.log('Scenario 1: "hola" con IA devolviendo isMenu=false (debe forzar menú)');
{
  const out = runNode(
    [baseItem('hola', '{"output":"¡Hola! ¿Qué deseas?","isMenu":false,"tipoPregunta":"MENU"}')],
    agentConfig,
  );
  const r = out[0].json;
  check('output = menú con marca', r.output === menuText, r.output);
  check('línea 1 empieza con *MARCA*', r.output.split('\n')[0].startsWith(`*${brand}*`), r.output.split('\n')[0]);
  check('isMenu = true', r.isMenu === true, r.isMenu);
  check('tipoPregunta = MENU', r.tipoPregunta === 'MENU', r.tipoPregunta);
  check('flow_name = ""', r.flow_name === '', r.flow_name);
  check('equipo_asignado = ""', r.equipo_asignado === '', r.equipo_asignado);
  check('JSON plano (output no anidado)', !(typeof r.output === 'string' && r.output.startsWith('{')), r.output);
}

console.log('Scenario 2: "menu" por keyword (IA sin tipoPregunta)');
{
  const out = runNode(
    [baseItem('quiero el menu', '{"output":"Respuesta genérica","isMenu":false,"tipoPregunta":"INFO"}')],
    agentConfig,
  );
  const r = out[0].json;
  check('output = menú con marca', r.output === menuText, r.output);
  check('isMenu = true', r.isMenu === true, r.isMenu);
  check('tipoPregunta = MENU', r.tipoPregunta === 'MENU', r.tipoPregunta);
}

console.log('Scenario 3: output anidado (JSON dentro de output) se des-nifica');
{
  const nestedOutput = JSON.stringify({
    output: 'Hola, ¿cómo puedo ayudarte?',
    isMenu: true,
    tipoPregunta: 'MENU',
  });
  const out = runNode(
    [baseItem('hola', JSON.stringify({ output: nestedOutput, isMenu: false, tipoPregunta: 'INFO' }))],
    agentConfig,
  );
  const r = out[0].json;
  check('output = menú con marca', r.output === menuText, r.output);
  check('isMenu = true', r.isMenu === true, r.isMenu);
  check('tipoPregunta = MENU', r.tipoPregunta === 'MENU', r.tipoPregunta);
}

console.log('Scenario 4: intención informativa sin regresión (no fuerza menú)');
{
  const out = runNode(
    [baseItem('¿cuánto cuesta el servicio?', '{"output":"El servicio cuesta $50.","isMenu":false,"tipoPregunta":"PRECIOS"}')],
    agentConfig,
  );
  const r = out[0].json;
  check('output = respuesta de la IA', r.output === 'El servicio cuesta $50.', r.output);
  check('isMenu = false', r.isMenu === false, r.isMenu);
  check('tipoPregunta = PRECIOS', r.tipoPregunta === 'PRECIOS', r.tipoPregunta);
}

console.log('Scenario 5: intención de flujo sin regresión (flujo preservado)');
{
  const out = runNode(
    [baseItem('quiero cotizar', '{"output":"¡Perfecto! (flujo_agendamiento_precios)","isMenu":false,"tipoPregunta":"Agendamiento_Precios","flow_name":"Agendamiento_Precios"}')],
    agentConfig,
  );
  const r = out[0].json;
  check('no fuerza menú', r.output !== menuText, r.output);
  check('flow_name = flujo_agendamiento_precios', r.flow_name === 'flujo_agendamiento_precios', r.flow_name);
}

console.log('Scenario 6: texto ultra-corto (≤2 chars) fuerza menú determinista');
{
  const out = runNode(
    [baseItem('k', '{"output":"No entendí tu mensaje.","isMenu":false,"tipoPregunta":"FALLBACK"}')],
    agentConfig,
  );
  const r = out[0].json;
  check('output = menú con marca', r.output === menuText, r.output);
  check('isMenu = true', r.isMenu === true, r.isMenu);
  check('tipoPregunta = MENU', r.tipoPregunta === 'MENU', r.tipoPregunta);
}

console.log('Scenario 7 (SPEC 18): modo conversacional — saludo no fuerza menú');
{
  const iaOutput = '¡Hola! 👋 Te saluda *KARLA CAMPOVERDE*. Nos dedicamos a... ¿qué te gustaría saber?';
  const out = runNode(
    [baseItem('hola', JSON.stringify({ output: iaOutput, isMenu: false, tipoPregunta: 'INFO' }))],
    agentConfigConversacional,
  );
  const r = out[0].json;
  check('output = introducción de la IA (sin menú)', r.output === iaOutput, r.output);
  check('isMenu = false', r.isMenu === false, r.isMenu);
  check('tipoPregunta ≠ MENU', r.tipoPregunta !== 'MENU', r.tipoPregunta);
}

console.log('Scenario 8 (SPEC 18): texto ultra-corto NO fuerza menú');
{
  const iaOutput = 'Respuesta conversacional de la IA.';
  const out = runNode(
    [baseItem('k', JSON.stringify({ output: iaOutput, isMenu: false, tipoPregunta: 'FALLBACK' }))],
    agentConfigConversacional,
  );
  const r = out[0].json;
  check('output = IA (sin menú forzado)', r.output === iaOutput, r.output);
  check('isMenu = false', r.isMenu === false, r.isMenu);
}

console.log('Scenario 9 (SPEC 18): flujo se dispara intacto en conversacional');
{
  const out = runNode(
    [baseItem('sí, agéndame', '{"output":"¡Perfecto! Voy a hacerte unas preguntas. (flujo_agendamiento_precios)","isMenu":false,"tipoPregunta":"Agendamiento_Precios","flow_name":"Agendamiento_Precios"}')],
    agentConfigConversacional,
  );
  const r = out[0].json;
  check('isMenu = false', r.isMenu === false, r.isMenu);
  check('flow_name = flujo_agendamiento_precios', r.flow_name === 'flujo_agendamiento_precios', r.flow_name);
}

console.log('Scenario 10 (SPEC 18): fallback por defecto sin mención de menú');
{
  const out = runNode(
    [baseItem('xyz', '{"output":"   ","isMenu":false,"tipoPregunta":"FALLBACK"}')],
    agentConfigConversacional,
  );
  const r = out[0].json;
  check('sin "menu" en el fallback', !(r.output || '').includes('menu'), r.output);
}

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
