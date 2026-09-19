# -*- coding: utf-8 -*-
"""SPEC 29: renombra flujo_carrito -> flujo_carrito_compra, inactivo y sin pasos.

El record XML conserva el xmlid 'flujo_carrito' (noupdate), así que en upgrades
existentes el nombre queda como flujo_carrito hasta esta migración, que lo
renombra, lo desactiva y elimina los pasos genéricos de captura.
"""


def migrate(cr, version):
    cr.execute("SELECT id FROM chatbot_flujo WHERE name = 'flujo_carrito'")
    flow_ids = [row[0] for row in cr.fetchall()]
    for flow_id in flow_ids:
        cr.execute(
            "UPDATE chatbot_flujo "
            "SET name = 'flujo_carrito_compra', "
            "    routing_key = 'flujo_carrito_compra', "
            "    active = %s, "
            "    generar_pasos_automatico = %s "
            "WHERE id = %s",
            (False, False, flow_id),
        )
        cr.execute(
            "DELETE FROM chatbot_paso WHERE flujo_id = %s",
            (flow_id,),
        )