


## Tips

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



## Steps

Paso 1: Crear las 2 Funciones Lambda (Los "Trabajadores")

Primero necesitamos el código que se conectará a Odoo. Como solo subimos un PDF, vamos a programar las Lambdas para que "deduzcan" el nombre del empleado leyendo el nombre del archivo (por ejemplo, si subes Juan_Perez.pdf, crearán a "Juan Perez").

1. Ve a AWS Lambda y crea la primera función:

    Nombre: Odoo_CrearEmpleado

    Runtime: Python 3.x

    Configuración: En la pestaña "Configuración > Variables de entorno", añade las credenciales de tu Odoo
   ```
   (ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD)
   ```

    Código Python:
    Python
```
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
```
2. Crea la segunda función Lambda:

    Nombre: Odoo_CrearLeadCRM

    Runtime y Variables: Igual que la anterior.

    Código Python:
    Python
```
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
```
(Copia los ARN de ambas Lambdas, los necesitarás en el siguiente paso).
Paso 2: Configurar Step Functions (El "Orquestador")

Aquí es donde creamos el flujo visual que dice "ejecuta estas dos cosas a la vez".

    Ve al servicio AWS Step Functions.

    Haz clic en Crear máquina de estado (Create state machine).

    Elige Escribir tu propio código (Write your workflow in code).

    Pega el siguiente código JSON. Importante: Reemplaza los ARN_DE_TU_LAMBDA_... por los ARNs reales que copiaste en el paso anterior.
    JSON
```
    {
      "Comment": "Flujo paralelo de Onboarding para Odoo",
      "StartAt": "Procesamiento Paralelo",
      "States": {
        "Procesamiento Paralelo": {
          "Type": "Parallel",
          "End": true,
          "Branches": [
            {
              "StartAt": "Crear Empleado",
              "States": {
                "Crear Empleado": {
                  "Type": "Task",
                  "Resource": "arn:aws:lambda:REGION:CUENTA:function:Odoo_CrearEmpleado",
                  "End": true
                }
              }
            },
            {
              "StartAt": "Crear Lead Informática",
              "States": {
                "Crear Lead Informática": {
                  "Type": "Task",
                  "Resource": "arn:aws:lambda:REGION:CUENTA:function:Odoo_CrearLeadCRM",
                  "End": true
                }
              }
            }
          ]
        }
      }
    }
```
    Guarda la máquina de estado con el nombre FlujoOnboardingOdoo. Copia el ARN de esta máquina de estado.

Paso 3: Crear el Bucket S3 (El "Gatillo")

    Ve a Amazon S3 y crea un bucket (ej. contratos-empleados-odoo).

    ¡Paso crítico! Una vez creado, entra al bucket, ve a la pestaña Propiedades (Properties).

    Baja hasta la sección Amazon EventBridge y haz clic en Editar.

    Activa la opción Enviar notificaciones a Amazon EventBridge y guarda. (Si no haces esto, S3 no avisará de que ha llegado un archivo nuevo).

Paso 4: Configurar EventBridge (El "Router")

Por último, necesitamos el "cable" que conecte S3 con Step Functions.

    Ve al servicio Amazon EventBridge.

    En el menú lateral, selecciona Reglas (Rules) y dale a Crear regla.

    Nombre: CapturarContratoS3. Tipo de regla: Regla con un patrón de eventos.

    En la sección Patrón de creación, elige Patrón personalizado (JSON) y pega esto (cambiando el nombre de tu bucket):
    JSON

    {
      "source": ["aws.s3"],
      "detail-type": ["Object Created"],
      "detail": {
        "bucket": {
          "name": ["contratos-empleados-odoo"]
        }
      }
    }

    Dale a Siguiente. En la pantalla de Destinos (Targets), elige:

        Tipo de destino: Servicio de AWS

        Destino: Máquina de estado de Step Functions

        Máquina de estado: Selecciona la que creaste en el Paso 2 (FlujoOnboardingOdoo).

        Tipo de ejecución: Estándar.

    Termina y crea la regla.


Tu arquitectura está lista.

    Abre tres pestañas: tu módulo de Empleados en Odoo, tu módulo de CRM en Odoo y el flujo visual de tu Step Function en AWS.

    Sube un archivo llamado Ana_Martinez.pdf a tu bucket de S3.

    Inmediatamente, la ejecución en Step Functions se iluminará en verde mostrando cómo las dos ramas paralelas se completan.

    Refresca Odoo: ¡Tendrás a "Ana Martinez" creada como empleada y un nuevo Lead en el CRM pidiendo su ordenador portátil!
