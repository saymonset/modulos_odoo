markdown
# Sistema de Gestión de Módulos Odoo

## Estructura de Directorios
/home/odoo/modulos_odoo/
├── shared/ # Módulos reutilizables (todos los clientes)
│ └── nombre_modulo/
│ ├── 18.0/ # Código específico para Odoo 18
│ └── 19.0/ # Código específico para Odoo 19
├── clientes/ # Módulos exclusivos por cliente
├── logs/ # Registros de operaciones
├── INVENTARIO.csv # Base de datos de módulos
└── Scripts:
├── 0_init_modulos_structure.sh # (Opcional) Ya ejecutado
├── 1_migrar_modulo.sh # Importar módulo existente
├── 2_enlazar_modulo.sh # Reemplazar original por enlace
├── 3_ver_modulos.sh # Listar módulos migrados
└── 4_registrar_modulo.sh # Añadir al inventario

text

## Flujo de Trabajo Estándar

### 1. MIGRAR un módulo existente a la estructura central
```bash
./1_migrar_modulo.sh <ruta_origen> <nombre_modulo> <version_odoo>
Ejemplo:

bash
./1_migrar_modulo.sh \
  "/home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/extra/chat_bot_n8n_ia" \
  chat_bot_n8n_ia \
  19.0
Qué hace:

Copia el módulo a /home/odoo/modulos_odoo/shared/chat_bot_n8n_ia/19.0/

Inicializa Git en esa carpeta

Crea commit inicial

Cambia a la rama 19.0

2. ENLAZAR el módulo a su ubicación original
bash
./2_enlazar_modulo.sh <ruta_original> <nombre_modulo> <version_odoo>
Ejemplo:

bash
./2_enlazar_modulo.sh \
  "/home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/extra/chat_bot_n8n_ia" \
  chat_bot_n8n_ia \
  19.0
Qué hace:

Respaldar la carpeta original como .bak

Crear un enlace simbólico apuntando a la central

El proyecto Docker sigue funcionando igual

3. REGISTRAR el módulo en el inventario
bash
./4_registrar_modulo.sh <nombre_modulo> <version> <cliente> <entorno>
Ejemplo:

bash
./4_registrar_modulo.sh chat_bot_n8n_ia 19.0 integraiadev_19 development
Entornos válidos: development, staging, production

4. VER todos los módulos migrados
bash
./3_ver_modulos.sh
Muestra:

Lista de módulos en shared/

Versiones disponibles de cada módulo

Ejemplo Completo (Migrar un módulo real)
bash
cd /home/odoo/modulos_odoo

# PASO 1: Migrar
./1_migrar_modulo.sh \
  "/home/odoo/odoo19-skeleton/postiz-n8n-chatwoot-pgadmin-odoo_19/v19/data/addons/extra/bcv_rate_update_venezuela" \
  bcv_rate_update_venezuela \
  19.0

# PASO 2: Enlazar
./2_enlazar_modulo.sh \
  "/home/odoo/odoo19-skeleton/postiz-n8n-chatwoot-pgadmin-odoo_19/v19/data/addons/extra/bcv_rate_update_venezuela" \
  bcv_rate_update_venezuela \
  19.0

# PASO 3: Registrar
./4_registrar_modulo.sh bcv_rate_update_venezuela 19.0 integraiadev_19 production

# PASO 4: Verificar
./3_ver_modulos.sh
Promover de Desarrollo a Producción
Opción A: Manual (recomendado para control)
bash
# 1. Trabajar en desarrollo (shared/modulo/18.0/)
cd /home/odoo/modulos_odoo/shared/mi_modulo/18.0/
# ... hacer cambios, commit, push ...

# 2. Copiar a producción (en el servidor destino)
rsync -av /home/odoo/modulos_odoo/shared/mi_modulo/18.0/ \
          usuario@produccion:/opt/odoo/custom-addons/mi_modulo/

# 3. Reiniciar Odoo en producción
ssh usuario@produccion "docker restart odoo-web"
Opción B: Con Git (avanzado)
bash
# En desarrollo
cd /home/odoo/modulos_odoo/shared/mi_modulo/18.0/
git tag production/2026-04-20
git push --tags

# En producción
cd /opt/odoo/custom-addons/mi_modulo/
git pull
git checkout production/2026-04-20
Consultar el Inventario
bash
# Ver todo el inventario
cat INVENTARIO.csv

# Buscar módulo específico
grep "chat_bot" INVENTARIO.csv

# Ver módulos por cliente
grep "integraiadev_19" INVENTARIO.csv

# Ver solo producción
grep "production" INVENTARIO.csv
Comandos Útiles de Git
bash
# Ver estado del módulo
cd /home/odoo/modulos_odoo/shared/mi_modulo/19.0/
git status

# Ver historial de cambios
git log --oneline

# Ver diferencias
git diff

# Crear nueva versión
git add .
git commit -m "v19.0.2.0.0: Nueva funcionalidad X"
git tag v19.0.2.0.0
Backup de la Central de Módulos
bash
# Backup completo con Git (incluye historial)
cd /home/odoo/modulos_odoo
tar -czf modulos_odoo_backup_$(date +%Y%m%d).tar.gz shared/ INVENTARIO.csv

# Restaurar backup
tar -xzf modulos_odoo_backup_20260420.tar.gz
Resolución de Problemas
El enlace simbólico no funciona
bash
# Verificar el enlace
ls -la /ruta/al/modulo

# Recrear enlace
rm /ruta/al/modulo
./2_enlazar_modulo.sh /ruta/al/modulo nombre version
El módulo no aparece en Odoo
bash
# Verificar permisos
chmod -R 755 /home/odoo/modulos_odoo/shared/mi_modulo/

# Reiniciar Odoo
docker restart odoo-19-web

# Actualizar lista de módulos (desde Odoo UI)
# Apps → Actualizar lista de módulos
Conflicto de versiones
bash
# Verificar en qué rama estás
cd /home/odoo/modulos_odoo/shared/mi_modulo/
git branch

# Cambiar a la rama correcta
git checkout 19.0
Reglas de Nomenclatura
Tipo	Formato	Ejemplo
Módulo genérico	nombre_modulo	chat_bot_n8n_ia
Cliente específico	nombre_modulo_cliente	chat_bot_n8n_ia_integra
Personalización	modulo_original_custom	sale_custom_approval
Versión en manifest	19.0.mayor.menor.patch	'version': '19.0.2.1.0'
Contacto y Soporte
Ante cualquier duda:

Revisar el inventario: cat INVENTARIO.csv

Verificar el enlace: ls -la /ruta/del/modulo

Consultar logs: tail -f logs/migracion.log

Última actualización: 2026-04-20
Versión del sistema: 1.0