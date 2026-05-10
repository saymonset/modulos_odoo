# 🚀 Cómo trabajar con la Central de Módulos

Ahora que los módulos están organizados en carpetas `oca/` y `extra/` por versión, el flujo de trabajo es mucho más sencillo. Ya no necesitas crear enlaces simbólicos ni usar scripts de migración complejos.

---

## ⚙️ 1. Configuración de Odoo (addons_path)

Para que Odoo reconozca los módulos de la central, simplemente añade las rutas correspondientes a tu archivo de configuración (`odoo.conf`) o en tu comando de ejecución:

```ini
addons_path = 
    /home/odoo/odoo-from-13-to-18/odoo/addons,
    /home/odoo/modulos_odoo/shared/oca/19.0,
    /home/odoo/modulos_odoo/shared/extra/19.0
```

---

## 🛠️ 2. Flujo de Trabajo Diario

### 📝 Editar un módulo
Los cambios se realizan directamente en la central. Odoo los leerá de ahí al reiniciar.

```bash
# Ejemplo: Editar el bot de n8n
cd /home/odoo/modulos_odoo/shared/extra/19.0/chat_bot_n8n_ia/
nano models/chat_bot.py
```

### 🔄 Aplicar cambios
Como Odoo apunta directamente a estas carpetas, solo necesitas reiniciar el servicio:

```bash
docker restart odoo-19-web
```

---

## 📥 3. Incorporar nuevos módulos

Si tienes módulos en una carpeta de descarga o en otro proyecto y quieres traerlos a la central:

1. Edita el script `9_3_mover_destino_aqui.sh` con la ruta de origen.
2. Ejecútalo:
   ```bash
   ./9_3_mover_destino_aqui.sh
   ```
   *Este script moverá automáticamente los módulos detectados a `shared/extra/19.0/`.*

---

## 📊 4. Herramientas útiles

### Ver inventario de la central
Para ver qué módulos tienes y en qué versiones:
```bash
./3_ver_modulos.sh
```

---

## ⚠️ Notas Importantes

*   **Sin enlaces simbólicos**: Ya no es necesario usar `ln -s`. Odoo lee las carpetas directamente.
*   **Git**: El control de versiones se realiza dentro de cada módulo en la central.
*   **Limpieza**: Mantén siempre los módulos de terceros en `oca/` y los desarrollos propios o extras en `extra/`.

---

*Desarrollado con ❤️ para el equipo de Odoo 19*
*Última actualización: Mayo 2026*
