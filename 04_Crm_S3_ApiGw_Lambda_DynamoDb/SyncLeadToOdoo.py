import xmlrpc.client
import os

# Credenciales de tu Odoo (Idealmente deberían ir en Variables de Entorno de la Lambda)
ODOO_URL = os.environ.get('ODOO_URL', 'http://TU_IP_DE_EC2:8069')
ODOO_DB = os.environ.get('ODOO_DB', 'odoo_produccion')
ODOO_USER = os.environ.get('ODOO_USER', 'tu_email_admin@empresa.com')
ODOO_PASSWORD = os.environ.get('ODOO_PASSWORD', 'tu_contraseña')

def lambda_handler(event, context):
    try:
        # 1. Autenticación con Odoo
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(ODOO_URL))
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        
        if not uid:
            print("Error: No se pudo autenticar en Odoo")
            return
            
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(ODOO_URL))

        # 2. Procesar los registros que vienen de DynamoDB Streams
        for record in event['Records']:
            # Solo nos interesan los registros nuevos (INSERT)
            if record['eventName'] == 'INSERT':
                # Extraer los datos (DynamoDB Streams usa un formato JSON con tipos de datos como 'S' para String)
                new_image = record['dynamodb']['NewImage']
                
                nombre = new_image.get('nombre', {}).get('S', 'Sin nombre')
                email = new_image.get('email', {}).get('S', '')
                empresa = new_image.get('empresa', {}).get('S', '')
                
                # 3. Inyectar en el módulo CRM de Odoo (Modelo: crm.lead)
                lead_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                    'crm.lead', 'create', [{
                        'name': f'Lead Feria: {nombre}', # Título de la oportunidad
                        'contact_name': nombre,
                        'email_from': email,
                        'partner_name': empresa,
                        'description': 'Lead capturado vía Serverless / S3'
                    }])
                
                print(f"Éxito: Lead {nombre} creado en Odoo con ID {lead_id}")
                
        return "Sincronización completada"
        
    except Exception as e:
        print(f"Error crítico en la sincronización: {str(e)}")
        # Al lanzar el error, DynamoDB retendrá el evento y lo reintentará más tarde
        raise e