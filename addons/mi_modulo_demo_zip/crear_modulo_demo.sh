#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${1:-.}"
MODULE_DIR="$BASE_DIR/mi_modulo_demo"

mkdir -p "$MODULE_DIR/models" "$MODULE_DIR/security" "$MODULE_DIR/views"

cat > "$MODULE_DIR/__init__.py" <<'EOPY'
from . import models
EOPY

cat > "$MODULE_DIR/__manifest__.py" <<'EOPY'
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
EOPY

cat > "$MODULE_DIR/models/__init__.py" <<'EOPY'
from . import demo_model
EOPY

cat > "$MODULE_DIR/models/demo_model.py" <<'EOPY'
from odoo import models, fields


class DemoModel(models.Model):
    _name = "mi.modulo.demo"
    _description = "Modelo Demo"

    name = fields.Char(string="Nombre", required=True)
    description = fields.Text(string="Descripción")
    active = fields.Boolean(string="Activo", default=True)
EOPY

cat > "$MODULE_DIR/security/ir.model.access.csv" <<'EOPY'
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_mi_modulo_demo_user,access.mi.modulo.demo.user,model_mi_modulo_demo,base.group_user,1,1,1,1
EOPY

cat > "$MODULE_DIR/views/demo_views.xml" <<'EOPY'
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_mi_modulo_demo_tree" model="ir.ui.view">
        <field name="name">mi.modulo.demo.tree</field>
        <field name="model">mi.modulo.demo</field>
        <field name="arch" type="xml">
            <tree>
                <field name="name"/>
                <field name="active"/>
            </tree>
        </field>
    </record>

    <record id="view_mi_modulo_demo_form" model="ir.ui.view">
        <field name="name">mi.modulo.demo.form</field>
        <field name="model">mi.modulo.demo</field>
        <field name="arch" type="xml">
            <form>
                <sheet>
                    <group>
                        <field name="name"/>
                        <field name="description"/>
                        <field name="active"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <record id="action_mi_modulo_demo" model="ir.actions.act_window">
        <field name="name">Demo</field>
        <field name="res_model">mi.modulo.demo</field>
        <field name="view_mode">tree,form</field>
    </record>

    <menuitem id="menu_mi_modulo_demo_root" name="Módulo Demo" sequence="10"/>

    <menuitem
        id="menu_mi_modulo_demo"
        name="Registros"
        parent="menu_mi_modulo_demo_root"
        action="action_mi_modulo_demo"
        sequence="20"/>
</odoo>
EOPY

echo "Módulo creado en: $MODULE_DIR"
