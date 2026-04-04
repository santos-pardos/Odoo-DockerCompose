import os
import urllib.parse
import xmlrpc.client

def lambda_handler(event, context):
    key = urllib.parse.unquote_plus(event['detail']['object']['key'])
    nombre_empleado = key.replace('_', ' ').replace('.pdf', '')

    url = os.environ.get('ODOO_URL')
    db = os.environ.get('ODOO_DB')
    user = os.environ.get('ODOO_USER')
    password = os.environ.get('ODOO_PASSWORD')

    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

    # Crear en el módulo de CRM (crm.lead) para asignarle su primer equipo/ordenador
    lead_id = models.execute_kw(db, uid, password, 'crm.lead', 'create', [{
        'name': f'Preparar equipo informático para {nombre_empleado}',
        'description': 'Lanzado automáticamente al firmar contrato.'
    }])

    return {"mensaje": f"Lead creado con ID {lead_id}"}
