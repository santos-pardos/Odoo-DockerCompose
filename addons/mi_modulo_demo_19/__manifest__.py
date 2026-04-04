{
    "name": "Mi Módulo Demo 19",
    "version": "19.0.1.0.0",
    "summary": "Ejemplo sencillo y completo para Odoo 19",
    "description": '''
Módulo de ejemplo para Odoo 19.

Incluye:
- modelo básico
- vistas list, form y search
- menú y acción
- permisos de acceso
- datos demo
- botón Python que cambia el estado y muestra una notificación
''',
    "author": "OpenAI",
    "category": "Tools",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/demo_record_views.xml"
    ],
    "demo": [
        "data/demo_record_demo.xml"
    ],
    "installable": True,
    "application": True
}
