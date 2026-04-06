import os
import urllib.parse
import xmlrpc.client

def lambda_handler(event, context):
    # 1. EventBridge + Step Functions nos enviarán los detalles del archivo
    key = urllib.parse.unquote_plus(event['detail']['object']['key'])

    # 2. Limpiamos el nombre del archivo para sacar el nombre del empleado
    nombre_empleado = key.replace('_', ' ').replace('.pdf', '')

    # 3. Conexión a Odoo
    url = os.environ.get('ODOO_URL')
    db = os.environ.get('ODOO_DB')
    user = os.environ.get('ODOO_USER')
    password = os.environ.get('ODOO_PASSWORD')

    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, user, password, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

    # 4. Crear en el módulo de Empleados (hr.employee)
    empleado_id = models.execute_kw(db, uid, password, 'hr.employee', 'create', [{
        'name': nombre_empleado,
        'job_title': 'Nuevo Ingreso'
    }])

    return {"mensaje": f"Empleado {nombre_empleado} creado con ID {empleado_id}"}
