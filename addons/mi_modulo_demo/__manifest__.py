{
    "name": "Mi Módulo Demo",
    "version": "17.0.1.0.0",
    "summary": "Addon de prueba muy sencillo",
    "description": "Un módulo de ejemplo para aprender la estructura básica de Odoo.",
    "author": "OpenAI",
    "category": "Tools",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/demo_views.xml",
    ],
    "installable": True,
    "application": True,
}
