from odoo import models, exceptions
import requests
import base64

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_generate_aws_pdf(self):
        for record in self:
            # Tu IP de AWS donde está corriendo Docker
            url_aws = "http://44.192.81.69:5000/generar-pdf"
            
            html_content = f"""
                <h1>Ficha de Cliente Generada en la Nube</h1>
                <p><strong>Nombre:</strong> {record.name}</p>
                <p><strong>Email:</strong> {record.email or 'Sin email'}</p>
                <br>
                <p><em>Este PDF no ha consumido recursos locales. Ha sido renderizado por un contenedor en AWS.</em></p>
            """
            
            try:
                # Odoo hace la llamada a tu servidor en AWS
                response = requests.post(url_aws, json={"html": html_content}, timeout=10)
                
                if response.status_code == 200:
                    pdf_b64 = base64.b64encode(response.content)
                    
                    # Se guarda el PDF recibido en la sección de adjuntos del cliente
                    self.env['ir.attachment'].create({
                        'name': f'AWS_{record.name}.pdf',
                        'type': 'binary',
                        'datas': pdf_b64,
                        'res_model': 'res.partner',
                        'res_id': record.id,
                        'mimetype': 'application/pdf'
                    })
                    
                    # Mensaje de éxito en el historial (Chatter) del cliente
                    if hasattr(record, 'message_post'):
                        record.message_post(body="✅ PDF generado exitosamente en AWS y guardado en adjuntos.")
                else:
                    raise exceptions.UserError(f"Error en AWS: Código {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                raise exceptions.UserError(f"Fallo de conexión con AWS: Asegúrate de que el contenedor está encendido y el puerto 5000 abierto en el Security Group. Detalle: {e}")
