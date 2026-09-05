# CHECKLIST — Alta de cliente / VPS (menú determinista, SPEC 13)

> Objetivo: que cada VPS nuevo sirva el menú de **su** empresa, con la marca en
> la primera línea (`*MARCA*`), sin depender de la IA ni del RAG en el saludo.
> La garantía la pone el workflow n8n (`Separar_variables_en_json`): si la
> intención es MENU, usa el texto guardado de la sección `=== MENÚ DE OPCIONES ===`.

## Pasos

- [ ] **1. Crear la config.** `Chatbot > Configuraciones > Nueva`. Completar
      `Nombre del negocio` y el `Rol / objetivo` (TÚ ERES). Guardar. Debe quedar
      como la config **activa** (es la única que el bot lee por VPS).
- [ ] **2. Setear `brand_name`.** En la misma ficha, `Nombre de marca` = la
      marca que ve el cliente final (ej. `KARLA CAMPOVERDE`). Si queda vacío, el
      menú usará `Nombre del negocio`. La marca se imprime en negrita WhatsApp
      como `*MARCA*` en la línea 1 del menú.
- [ ] **3. Sincronizar el RAG.** Ejecutar `Sincronizar todo desde RAG`
      (`action_recargar_todo_desde_rag`). Requiere que `n8n_vectors` ya tenga
      los documentos comerciales ingeridos (no el prompt del bot). Esto regenera
      intenciones, detecta flujos y (re)genera los Chatwoot Mappings.
- [ ] **4. Regenerar el menú con IA.** Pulsar `Regenerar menú según rol`
      (`action_regenerar_menu`). Genera etiquetas y tagline desde el rol del
      negocio (IA) y siembra `*MARCA*` en la línea 1. Si la IA falla, avisa con
      warning: el menú sale con marca pero sin tagline del rol (ver API key de
      OpenAI en `openai.config`).
- [ ] **5. Verificar "hola".** Enviar `hola` al bot del VPS:
      - Responde el menú de la config activa con `*MARCA*` en la línea 1.
      - El flujo es determinista: el texto proviene del system_prompt
        (`=== MENÚ DE OPCIONES ===`), no de la IA ni del RAG.
      - `isMenu=true` y el JSON de salida es plano (sin JSON anidado).

## Reglas de oro

- **Un VPS = una BD = una config activa.** No hay ruteo multicliente por
  `account_id`; la empresa "de turno" se resuelve por despliegue.
- El menú **nunca** consulta el RAG en el saludo: es el texto guardado.
- Si cambias `brand_name`, `role` o los flujos, la config marca el menú como
  desactualizado (`menu_stale`); regenera el menú (paso 4) y verifica (paso 5).
- La desobediencia de formato de la IA no rompe el flujo: el workflow n8n
  des-nidifica `output` y fuerza `isMenu=true` en intención MENU.

## Referencias

- Render del menú: `services/prompt_renderer.py` → `_render_menu` /
  `=== MENÚ DE OPCIONES ===`.
- Generación del menú por rol: `models/chatbot_config.py` →
  `_generar_menu_desde_flujos`, `action_regenerar_menu`.
- Ruteo determinista + des-nidificación: nodo n8n `Separar_variables_en_json`
  (workflow `n8n/ycloud_create_lead_0_con_menu_whatsapp.json`).
- Verificación automática del nodo (replay): `node n8n/test_replay_menu.js`
  (reproduce "hola" → menú con marca, des-nidificación y sin regresión).
