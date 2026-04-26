Cómo trabajar de ahora en adelante:
1. EDITAR módulos: Siempre en la central
bash
# ✅ CORRECTO - Editar aquí
cd /home/odoo/modulos_odoo/shared/chat_bot_n8n_ia/19.0/
nano models/chat_bot.py

# ❌ INCORRECTO - No editar aquí (es un enlace, pero funciona igual)
cd /home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/extra/chat_bot_n8n_ia/
# Aunque funciona, no es la práctica recomendada
2. COMMIT de cambios: Usar Git en la central
bash
cd /home/odoo/modulos_odoo/shared/chat_bot_n8n_ia/19.0/

# Ver qué cambió
git status
git diff

# Guardar cambios
git add .
git commit -m "feat: Añadida nueva funcionalidad X"

# Ver historial
git log --oneline
3. PROBAR cambios: Reiniciar Odoo
bash
# Los cambios se ven inmediatamente porque el enlace apunta a la central
docker restart odoo-19-web

# O si usas docker-compose
cd /home/odoo/odoo-from-13-to-18/arquitectura/odoo19/
docker-compose restart web
📋 Flujo de trabajo diario:
Cuando vas a trabajar en un módulo:
bash
# 1. Ir a la central
cd /home/odoo/modulos_odoo/shared/chat_bot_n8n_ia/19.0/

# 2. Asegurarse de estar en la rama correcta
git branch  # Debe mostrar * 19.0

# 3. Hacer cambios
nano models/algo.py

# 4. Probar (reiniciar Odoo)
docker restart odoo-19-web

# 5. Guardar en Git
git add .
git commit -m "Descripción del cambio"

# 6. (Opcional) Subir a repositorio remoto
git push origin 19.0
Cuando creas un módulo NUEVO:
bash
# 1. Crear en la central
cd /home/odoo/modulos_odoo
./1_migrar_modulo.sh /ruta/temporal nombre_nuevo_modulo 19.0

# 2. Crear enlace en el proyecto
./2_enlazar_modulo.sh /home/odoo/odoo-from-13-to-18/.../extra/nombre_nuevo_modulo nombre_nuevo_modulo 19.0

# 3. Registrar
./4_registrar_modulo.sh nombre_nuevo_modulo 19.0 integraiadev_19 development
🔄 Cómo promover a producción:
Opción 1: Manual (seguro y controlado)
bash
# 1. En desarrollo, asegurar que todo funciona
cd /home/odoo/modulos_odoo/shared/chat_bot_n8n_ia/19.0/
git status  # Debe estar limpio

# 2. Copiar a producción
rsync -av --delete \
  /home/odoo/modulos_odoo/shared/chat_bot_n8n_ia/19.0/ \
  /home/odoo/odoo19-skeleton/postiz-n8n-chatwoot-pgadmin-odoo_19/v19/data/addons/extra/chat_bot_n8n_ia/

# 3. Reiniciar Odoo en producción
cd /home/odoo/odoo19-skeleton/postiz-n8n-chatwoot-pgadmin-odoo_19/
docker restart odoo-19-web

# 4. Registrar versión en producción
./4_registrar_modulo.sh chat_bot_n8n_ia 19.0 integraiadev_19 production
Opción 2: Usando Git (más elegante)
bash
# En desarrollo: crear tag
cd /home/odoo/modulos_odoo/shared/chat_bot_n8n_ia/19.0/
git tag production/2026-04-20
git push --tags

# En producción: desplegar tag
cd /home/odoo/odoo19-skeleton/.../extra/chat_bot_n8n_ia/
git pull
git checkout production/2026-04-20
docker restart odoo-19-web
⚠️ Cosas importantes que debes saber:
1. Los .bak son tus respaldos
Puedes eliminarlos cuando confirmes que todo funciona

rm -rf /ruta/*.bak

2. Si necesitas recuperar el original
bash
# Eliminar enlace
rm /ruta/del/enlace

# Restaurar backup
mv /ruta/del/enlace.bak /ruta/del/enlace
3. Mantén actualizado el inventario
bash
# Ver módulos en desarrollo
grep "development" INVENTARIO.csv

# Ver módulos en producción
grep "production" INVENTARIO.csv
4. Respaldar la central regularmente
bash
# Backup completo
cd /home/odoo
tar -czf modulos_backup_$(date +%Y%m%d).tar.gz modulos_odoo/

# Restaurar si es necesario
tar -xzf modulos_backup_20260420.tar.gz
🎯 Resumen de comandos que usarás a diario:
bash
# Ir a un módulo
cd /home/odoo/modulos_odoo/shared/NOMBRE/19.0/

# Ver cambios
git status

# Guardar cambios
git add . && git commit -m "mensaje"

# Ver historial
git log --oneline

# Ver inventario
cat /home/odoo/modulos_odoo/INVENTARIO.csv

# Listar todos los módulos
ls /home/odoo/modulos_odoo/shared/

# Ver qué módulos están enlazados en tu proyecto
ls -la /home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/extra/ | grep "^l"
✅ Checklist para tus tareas diarias:
¿Voy a editar un módulo? → Voy a modulos_odoo/shared/

¿Terminé un cambio? → Hago git commit

¿Funciona en desarrollo? → Promuevo a producción con rsync

¿Actualicé producción? → Registro en inventario como production

¿Todo estable? → Hago backup de modulos_odoo/

