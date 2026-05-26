 Resumen final: Configuración de S3 para alojar tu video (Opción 2: Bucket Policy)
Después de varios intentos con ACL, la solución más limpia y recomendada por AWS fue usar una Bucket Policy para hacer públicos los objetos. Aquí tienes el resumen de lo que hicimos y cómo queda configurado todo para tu campaña de WhatsApp.

1. Creaste el bucket en S3
Nombre del bucket: mis-videos-unisa

Región: us-east-1 (N. Virginia)

2. Subiste tu video
Archivo: tarjeta.mp4 (12.1 MB)

Se encuentra dentro del bucket.

3. Configuraste el bloqueo de acceso público
Para poder aplicar una política de bucket que otorgue acceso público, era necesario desmarcar las opciones que bloquean el acceso a través de políticas de bucket (no solo ACL).
En la pestaña Permissions → Block public access (bucket settings) hiciste lo siguiente:

Opción	Estado
Block all public access	DESMARCADO
Block public access to buckets and objects granted through new ACLs	(da igual)
Block public access to buckets and objects granted through any ACLs	(da igual)
Block public access to buckets and objects granted through new public bucket policies	DESMARCADO
Block public and cross-account access through any public bucket policies	DESMARCADO
Esto permite que las políticas de bucket puedan conceder acceso público.

4. Aplicaste la Bucket Policy (Opción 2)
En la misma sección Permissions, en Bucket Policy, pegaste el siguiente JSON:

json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::mis-videos-unisa/*"
    }
  ]
}
Importante: El Resource usa /* al final, lo que hace público todos los objetos dentro del bucket. Si en el futuro quieres más seguridad y solo exponer un archivo específico, puedes cambiar esa línea por:

json
"Resource": "arn:aws:s3:::mis-videos-unisa/tarjeta.mp4"
5. Guardaste los cambios
Hiciste clic en Save changes y confirmaste la acción escribiendo confirm.

6. Obtuviste la URL pública
Una vez aplicada la política, cualquier persona puede acceder al objeto. La URL pública del video es:

text
https://mis-videos-unisa.s3.us-east-1.amazonaws.com/tarjeta.mp4
Puedes confirmar su accesibilidad pegándola en un navegador en modo incógnito o usando curl.

7. Usaste la URL en Odoo
En tu módulo Campañas WhatsApp de Odoo:

Creaste una nueva campaña o editaste una existente.

Desmarcaste la opción Usar plantilla aprobada (para modo texto libre).

En el campo URL del Video o Imagen pegaste la URL de S3.

En Texto del Mensaje escribiste el caption promocional.

Seleccionaste los contactos con consentimiento_whatsapp = True.

Hiciste clic en Enviar.

8. Ventajas de esta configuración
Sin depender de DNS ni subdominios propios. El bucket de S3 ya es público.

Sin problemas de permisos ACL. La política de bucket es más predecible.

Capa gratuita de AWS aplicable: almacenamiento (5 GB), GET requests (20,000/mes) y transferencia (100 GB/mes) suficientes para tu campaña.

9. Posible paso adicional (opcional)
Si por seguridad prefieres no dejar todo el bucket público para siempre, puedes:

Eliminar la política de bucket después de la campaña.

O cambiar la política para que solo afecte al archivo tarjeta.mp4 (como se mostró arriba).

🧪 Verificación rápida
bash
curl -I https://mis-videos-unisa.s3.us-east-1.amazonaws.com/tarjeta.mp4
Debe responder HTTP/1.1 200 OK.

