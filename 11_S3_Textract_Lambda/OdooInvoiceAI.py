import json
import boto3
import urllib.parse
import xmlrpc.client
import os

# --- CONFIGURACIÓN DE ODOO ---
# (Recomendado: poner esto en Variables de Entorno de la Lambda)
ODOO_URL = os.environ.get('ODOO_URL', 'http://TU_IP_DE_EC2:8069')
ODOO_DB = os.environ.get('ODOO_DB', 'odoo')
ODOO_USER = os.environ.get('ODOO_USER', 's@s.com')
ODOO_PASSWORD = os.environ.get('ODOO_PASSWORD', 'A123456b')

# Inicializar clientes de AWS
s3 = boto3.client('s3')
textract = boto3.client('textract')

def lambda_handler(event, context):
    try:
        # 1. Obtener el nombre del bucket y del archivo que acaba de subir
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
        
        print(f"📄 Procesando factura: s3://{bucket}/{key}")
        
        # 2. Llamar a la IA especializada en facturas de Textract
        response = textract.analyze_expense(
            Document={'S3Object': {'Bucket': bucket, 'Name': key}}
        )
        
        # 3. Extraer los datos inteligentemente
        total = 0.0
        fecha = "Desconocida"
        proveedor = "Proveedor Escaneado con IA"
        
        for expense_doc in response['ExpenseDocuments']:
            for field in expense_doc['SummaryFields']:
                field_type = field.get('Type', {}).get('Text')
                field_value = field.get('ValueDetection', {}).get('Text', '')
                
                if field_type == 'TOTAL':
                    # Limpiar símbolo de euro o texto para quedarnos con el número
                    num_str = field_value.replace('€', '').replace(',', '.').strip()
                    try:
                        total = float(num_str)
                    except ValueError:
                        pass
                elif field_type == 'INVOICE_RECEIPT_DATE':
                    fecha = field_value
                elif field_type == 'VENDOR_NAME':
                    proveedor = field_value

        print(f"🤖 Datos extraídos -> Proveedor: {proveedor} | Total: {total} | Fecha: {fecha}")
        
        # 4. Inyectar en Odoo vía XML-RPC
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        
        if not uid:
            raise Exception("Error de autenticación con Odoo")
            
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        # 4.1 Buscar o crear el proveedor en Odoo
        partner_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'res.partner', 'search', [[('name', '=', proveedor)]])
        if partner_ids:
            partner_id = partner_ids[0]
        else:
            partner_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'res.partner', 'create', [{
                'name': proveedor,
                'supplier_rank': 1, # Es un proveedor
                'comment': 'Creado automáticamente por AWS Textract'
            }])
            
        # 4.2 Crear el borrador de la factura (Vendor Bill)
        invoice_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'account.move', 'create', [{
            'move_type': 'in_invoice', # Tipo: Factura de proveedor
            'partner_id': partner_id,
            'ref': f"Factura escaneada - Fecha original: {fecha}",
            # Añadimos una línea de detalle con el total detectado
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'Importe detectado por IA (Revisar)',
                    'price_unit': total,
                    'quantity': 1
                })
            ]
        }])
        
        print(f"✅ ¡Éxito! Factura borrador creada en Odoo con ID: {invoice_id}")
        return {"statusCode": 200, "body": f"Factura {invoice_id} creada."}

    except Exception as e:
        print(f"❌ Error crítico: {str(e)}")
        raise e