from odoo import fields, models


class DemoRecord(models.Model):
    _name = "mi.modulo.demo.record"
    _description = "Registro Demo Odoo 19"
    _order = "sequence, id"

    name = fields.Char(string="Nombre", required=True)
    description = fields.Text(string="Descripción")
    active = fields.Boolean(string="Activo", default=True)
    sequence = fields.Integer(string="Secuencia", default=10)
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("done", "Hecho"),
        ],
        string="Estado",
        default="draft",
        required=True,
    )
    date_note = fields.Date(string="Fecha")
    amount = fields.Float(string="Importe")

    def action_mark_done(self):
        self.write({"state": "done"})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Registro actualizado",
                "message": "El registro se ha marcado como hecho.",
                "type": "success",
                "sticky": False,
            },
        }

    def action_reset_draft(self):
        self.write({"state": "draft"})
        return True
