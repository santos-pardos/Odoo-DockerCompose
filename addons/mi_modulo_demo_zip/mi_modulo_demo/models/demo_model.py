from odoo import models, fields


class DemoModel(models.Model):
    _name = "mi.modulo.demo"
    _description = "Modelo Demo"

    name = fields.Char(string="Nombre", required=True)
    description = fields.Text(string="Descripción")
    active = fields.Boolean(string="Activo", default=True)
