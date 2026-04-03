import json
import urllib.parse
import boto3
import xmlrpc.client
import os

# 1. Inicializamos el cliente de S3
s3 = boto3.client('s3')

# 2. Variables de entorno (Configura esto en la pestaña "Configuration" de tu Lambda)
ODOO_URL = os.environ.get('ODOO_URL', 'http://TU_IP_DE_ODOO:8069')
ODOO_DB = os.environ.get('ODOO_DB', 'tu_base_de_datos')
ODOO_USER = os.environ.get('ODOO_USER', 'tu_usuario_admin')
ODOO_PASSWORD = os.environ.get('ODOO_PASSWORD', 'tu_contraseña')

def lambda_handler(event, context):
    # 3. Extraemos el nombre del bucket y el archivo que acaba de subir a S3
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    
    print(f"Detectado nuevo archivo: {key} en el bucket: {bucket}")
    
    try:
        # 4. Descargamos el archivo JSON de S3 a la memoria de Lambda
        response = s3.get_object(Bucket=bucket, Key=key)
        contenido_archivo = response['Body'].read().decode('utf-8')
        leads = json.loads(contenido_archivo)
        
        # 5. Conectamos con Odoo
        print("Autenticando en Odoo...")
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        
        if not uid:
            return {"statusCode": 401, "body": "Fallo de autenticación en Odoo"}
            
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        print("Autenticación exitosa. Insertando leads...")
        
        # 6. Recorremos el JSON y creamos los leads en el modelo 'crm.lead'
        leads_creados = 0
        for lead in leads:
            lead_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'crm.lead', 'create', [lead])
            print(f"Lead creado con éxito. ID de Odoo: {lead_id}")
            leads_creados += 1
            
        return {
            'statusCode': 200,
            'body': json.dumps(f'Proceso completado. Se insertaron {leads_creados} leads en Odoo CRM.')
        }
        
    except Exception as e:
        print(f"Error procesando el archivo {key} del bucket {bucket}: {str(e)}")
        raise e
