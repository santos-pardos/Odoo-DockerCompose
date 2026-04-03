1. El Formato de los Leads (JSON)

Aunque Odoo permite importar archivos CSV, cuando trabajamos con integraciones automatizadas (Lambdas y APIs), el estándar indiscutible es JSON. Es un formato estructurado, ligero y que Python convierte nativamente en diccionarios (exactamente lo que Odoo necesita para crear registros).

Para importar en el módulo de CRM de Odoo (cuyo modelo interno se llama crm.lead), el archivo JSON que debes subir a S3 debería tener esta estructura.

Crea un archivo llamado nuevos_leads.json:
JSON
```
[
  {
    "name": "Interés en Curso de Arquitectura Cloud",
    "contact_name": "María García",
    "email_from": "maria.garcia@ejemplo.com",
    "phone": "+34 600 123 456",
    "description": "Viene desde la campaña de LinkedIn."
  },
  {
    "name": "Presupuesto para migración ERP",
    "contact_name": "Carlos López",
    "email_from": "carlos.lopez@empresa.com",
    "phone": "+34 699 987 654",
    "description": "Empresa de 50 empleados buscando pasar a la nube."
  }
]
```

Nota: Las claves (name, email_from, etc.) coinciden exactamente con los nombres técnicos de los campos en la base de datos de Odoo.
2. La Función Lambda (Python)

Esta función utiliza boto3 (la librería oficial de AWS preinstalada en Lambda) para descargar el archivo del bucket odoousj, y xmlrpc.client (nativa de Python) para hablar con Odoo. No necesitas instalar nada extra, funciona tal cual.

El código para tu función Lambda:
Python
```
import json
import urllib.parse
import boto3
import xmlrpc.client
import os

1. Inicializamos el cliente de S3
s3 = boto3.client('s3')

2. Variables de entorno (Configura esto en la pestaña "Configuration" de tu Lambda)
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
```
3. Pasos críticos para que esto funcione en AWS

Si tus alumnos van a desplegar esto en su cuenta de AWS, hay dos configuraciones clave en la consola de AWS que no deben olvidar:

    Permisos de la Lambda (IAM Role):
    Por defecto, Lambda no tiene permiso para leer tu bucket odoousj. Debes ir a la pestaña Configuración > Permisos de tu Lambda, abrir el Rol de Ejecución asociado y añadirle la política AmazonS3ReadOnlyAccess. Sin esto, el código fallará en la línea 4 con un error de "Access Denied".

    El Disparador (Trigger):
    Debes ir a la vista general de la Lambda y hacer clic en "Agregar desencadenador" (Add trigger). Seleccionas S3, eliges tu bucket odoousj y seleccionas el tipo de evento: PUT (Creación de objetos). Esto es lo que automatiza el proceso; le dice a AWS: "Cada vez que alguien ponga un archivo nuevo aquí, ejecuta este código Python inmediatamente".
