 # Desinstalar un módulo de Odoo vía base de datos (PostgreSQL)

Este procedimiento se utiliza cuando el comando `--uninstall` no está disponible o falla, y se necesita eliminar un módulo problemático directamente desde la base de datos.

## Contexto
- Módulo a desinstalar: `web_responsive`
- Base de datos: `dbodoo19`
- Contenedor de PostgreSQL: `odoo-db19-n8n`
- Contenedor de Odoo: `odoo-19-web`

## Pasos realizados

### 1. Acceder al contenedor de la base de datos
```bash
docker exec -it odoo-db19-n8n bash
2. Conectarse a la base de datos de Odoo
bash
psql -U odoo -d dbodoo19
3. Verificar que el módulo está instalado
sql
SELECT name, state FROM ir_module_module WHERE name = 'web_responsive';
Salida esperada:

text
      name      |   state   
----------------+-----------
 web_responsive | installed
4. Cambiar el estado del módulo a uninstalled
sql
UPDATE ir_module_module SET state = 'uninstalled' WHERE name = 'web_responsive';
5. Eliminar las dependencias del módulo
sql
DELETE FROM ir_module_module_dependency 
WHERE module_id = (SELECT id FROM ir_module_module WHERE name = 'web_responsive');
6. Eliminar los datos asociados al módulo
sql
DELETE FROM ir_model_data WHERE module = 'web_responsive';
7. Salir de psql
sql
\q
8. Reiniciar el contenedor de Odoo
bash
docker restart odoo-19-web
Verificación final
Accede a http://localhost:18069 – el error debe haber desaparecido.

Revisa los logs si persiste algún problema:

bash
docker logs odoo-19-web --tail 50
Nota sobre dependencias
Si otros módulos dependen del módulo que estás desinstalando, debes desinstalarlos primero (siguiendo los mismos pasos).
Para listar los módulos dependientes:

sql
SELECT name FROM ir_module_module 
WHERE id IN (
    SELECT module_id FROM ir_module_module_dependency 
    WHERE depend_id = (SELECT id FROM ir_module_module WHERE name = 'web_responsive')
);
Alternativa (si --uninstall funciona)
En versiones recientes de Odoo (como Odoo 19), se puede usar directamente:

bash
/opt/odoo/odoo-core/odoo-bin -c /etc/odoo/odoo.conf --database dbodoo19 --uninstall web_responsive --stop-after-init
Pero si ese comando falla con no such option: --uninstall, la vía PostgreSQL es la solución.

text
