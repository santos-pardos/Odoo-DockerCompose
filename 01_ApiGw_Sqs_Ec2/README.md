
![alt text](Architecture2.png)
```
curl -X POST https://ci6oe0r1lb.execute-api.us-east-1.amazonaws.com/prod/pedido \
-H "Content-Type: application/json" \
-d '{"contacto": {"nombre": "Prueba"}, "producto": {"nombre": "Test", "precio_venta": 10}}'
```

```
curl -X POST https://ci6oe0r1lb.execute-api.us-east-1.amazonaws.com/prod/pedido \
-H "Content-Type: application/json" \
-d '{
  "contacto": {
    "nombre": "Prueba desde cURL",
    "email": "test-curl@sistemas.com"
  },
  "producto": {
    "nombre": "Monitor UltraWide",
    "precio_venta": 250.00,
    "coste": 190.00,
    "tipo": "consu",
    "referencia": "MON-UW-01",
    "codigo_barras": "123456789"
  }
}'
```
## Odoo
```
Instala Odoo (3 contenedores) y los módulos de ventas y contactos.
```

## El Flujo de Trabajo

    Cliente: Envía un JSON con un pedido a una URL (API Gateway).

    API Gateway: Recibe el pedido y lo mete en una cola (SQS). Responde al cliente "Recibido".

    SQS: Guarda el mensaje de forma segura.

    Tu Código Python (Worker): "Vigila" la cola. Cuando ve un mensaje, lo saca, lo procesa y crea el cliente en Odoo.

PASO 1: Configurar la "Sala de Espera" (Amazon SQS)

    Entra en la consola de AWS y busca SQS.

    Dale a Create queue.

    Selecciona Standard (es más barata y rápida).

    Nombre: PedidosOdoo.

    Deja todo lo demás por defecto y dale a Create queue.

    IMPORTANTE: Copia la URL de la cola (ej. https://sqs.us-east-1.amazonaws.com/123456/PedidosOdoo). La necesitaremos para el código.

PASO 2: Configurar la "Puerta de Entrada" (API Gateway)

Aquí crearemos la URL que recibirá los datos.

    Busca API Gateway en AWS y dale a Create API.

    Elige REST API (Build).

    Nombre: API-Odoo-Integracion.

    En el menú de la izquierda, ve a Resources -> Create Resource. Nombre: pedido.

    Selecciona /pedido y dale a Create Method. Elige POST.

    Configuración del POST:

        Integration type: AWS Service.

        AWS Region: La misma donde creaste la SQS (ej. us-east-1).

        AWS Service: Simple Queue Service (SQS).

        HTTP method: POST.

        Action Name: SendMessage.

        URL request headers parameters
        Name
        Content-Type
        Mapped from Info
        'application/x-www-form-urlencoded'
        Caching
        
        
        Mapping templates
        Content type
        application/json
        Generate template
        Template body
        Action=SendMessage&QueueUrl=https://sqs.us-east-1.amazonaws.com/658620698452/odoo&MessageBody=$util.urlEncode($input.body)

    Dale a Deploy API, crea un Stage llamado prod y copia la Invoke URL.

PASO 3: El Código Python (El "Obrero" que conecta todo)

Este script debe estar corriendo en tu ordenador (o en una EC2). Es el puente que une AWS con Odoo.

Instala las librerías:
```
sudo dnf install pip -y
pip install boto3
```
```
aws configure
```
Crea el archivo worker_odoo.py:
Python
```
import boto3
import xmlrpc.client
import json
import time
import traceback


# ============================================================
# 1. CONFIGURACIÓN DE ODOO
# ============================================================

ODOO_URL = 'http://TU_IP_PUBLICA_EC2'
ODOO_DB = 'odoo'
ODOO_USER = 'admin'
ODOO_PASS = 'admin'


# ============================================================
# 2. CONFIGURACIÓN DE AWS SQS
# ============================================================

AWS_REGION = 'us-east-1'
QUEUE_NAME = 'PedidosOdoo'


# ============================================================
# 3. FUNCIONES AUXILIARES
# ============================================================

def conectar_odoo():
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})

    if not uid:
        raise Exception("No se pudo autenticar con Odoo. Revisa ODOO_DB, ODOO_USER y ODOO_PASS.")

    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

    print(f"✅ Conectado a Odoo con UID: {uid}")

    return uid, models


def conectar_sqs():
    sqs = boto3.client('sqs', region_name=AWS_REGION)

    response = sqs.get_queue_url(QueueName=QUEUE_NAME)
    queue_url = response['QueueUrl']

    print(f"✅ Conectado a SQS: {queue_url}")

    return sqs, queue_url


def obtener_campos_modelo(models, uid, modelo):
    return models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_PASS,
        modelo,
        'fields_get',
        [],
        {'attributes': ['string']}
    )


def buscar_o_crear_cliente(models, uid, nombre_cliente, email_cliente):
    dominio = []

    if email_cliente:
        dominio = [['email', '=', email_cliente]]
    else:
        dominio = [['name', '=', nombre_cliente]]

    clientes = models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_PASS,
        'res.partner',
        'search',
        [dominio],
        {'limit': 1}
    )

    if clientes:
        id_cliente = clientes[0]
        print(f"ℹ️ Cliente ya existe con ID: {id_cliente}")
        return id_cliente

    valores_cliente = {
        'name': nombre_cliente,
        'email': email_cliente or False,
        'customer_rank': 1,
    }

    id_cliente = models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_PASS,
        'res.partner',
        'create',
        [valores_cliente]
    )

    print(f"✅ Cliente creado con ID: {id_cliente}")

    return id_cliente


def buscar_o_crear_producto(
    models,
    uid,
    nombre_producto,
    precio_venta,
    coste,
    tipo,
    referencia,
    codigo_barras
):
    # Primero buscamos por referencia interna
    if referencia:
        productos = models.execute_kw(
            ODOO_DB,
            uid,
            ODOO_PASS,
            'product.template',
            'search',
            [[['default_code', '=', referencia]]],
            {'limit': 1}
        )

        if productos:
            id_producto_template = productos[0]
            print(f"ℹ️ Producto ya existe con ID template: {id_producto_template}")
            return id_producto_template

    campos_producto = obtener_campos_modelo(models, uid, 'product.template')

    valores_producto = {
        'name': nombre_producto,
        'list_price': float(precio_venta or 0),
        'standard_price': float(coste or 0),
        'default_code': referencia or False,
        'sale_ok': True,
        'purchase_ok': True,
    }

    # Tu Odoo ha dado error con detailed_type,
    # por eso usamos type si existe.
    if 'type' in campos_producto:
        valores_producto['type'] = tipo or 'consu'
    elif 'detailed_type' in campos_producto:
        valores_producto['detailed_type'] = tipo or 'consu'

    if 'barcode' in campos_producto and codigo_barras:
        valores_producto['barcode'] = codigo_barras

    id_producto_template = models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_PASS,
        'product.template',
        'create',
        [valores_producto]
    )

    print(f"✅ Producto creado con ID template: {id_producto_template}")

    return id_producto_template


def obtener_variante_producto(models, uid, id_producto_template):
    producto_template = models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_PASS,
        'product.template',
        'read',
        [[id_producto_template]],
        {'fields': ['product_variant_id']}
    )

    if not producto_template:
        raise Exception("No se pudo leer el producto creado.")

    product_variant_id = producto_template[0].get('product_variant_id')

    if not product_variant_id:
        raise Exception("El producto no tiene variante product.product.")

    id_producto = product_variant_id[0]

    print(f"✅ Variante product.product ID: {id_producto}")

    return id_producto


def crear_pedido_venta(models, uid, id_cliente, id_producto, precio_venta):
    valores_pedido = {
        'partner_id': id_cliente,
        'order_line': [
            (0, 0, {
                'product_id': id_producto,
                'product_uom_qty': 1,
                'price_unit': float(precio_venta or 0),
            })
        ]
    }

    id_pedido = models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_PASS,
        'sale.order',
        'create',
        [valores_pedido]
    )

    print(f"✅ Pedido de venta creado con ID: {id_pedido}")

    return id_pedido


def procesar_mensaje(models, uid, body):
    print("📩 Mensaje recibido:")
    print(body)

    datos = json.loads(body)

    contacto = datos.get('contacto', {})
    producto = datos.get('producto', {})

    nombre_cliente = contacto.get('nombre')
    email_cliente = contacto.get('email')

    nombre_producto = producto.get('nombre')
    precio_venta = producto.get('precio_venta', 0)
    coste = producto.get('coste', 0)
    tipo = producto.get('tipo', 'consu')
    referencia = producto.get('referencia')
    codigo_barras = producto.get('codigo_barras')

    if not nombre_cliente:
        raise Exception("Falta contacto.nombre en el JSON.")

    if not nombre_producto:
        raise Exception("Falta producto.nombre en el JSON.")

    print(f"📦 Procesando pedido de cliente: {nombre_cliente}")
    print(f"🛒 Producto: {nombre_producto}")

    id_cliente = buscar_o_crear_cliente(
        models=models,
        uid=uid,
        nombre_cliente=nombre_cliente,
        email_cliente=email_cliente
    )

    id_producto_template = buscar_o_crear_producto(
        models=models,
        uid=uid,
        nombre_producto=nombre_producto,
        precio_venta=precio_venta,
        coste=coste,
        tipo=tipo,
        referencia=referencia,
        codigo_barras=codigo_barras
    )

    id_producto = obtener_variante_producto(
        models=models,
        uid=uid,
        id_producto_template=id_producto_template
    )

    id_pedido = crear_pedido_venta(
        models=models,
        uid=uid,
        id_cliente=id_cliente,
        id_producto=id_producto,
        precio_venta=precio_venta
    )

    return id_pedido


# ============================================================
# 4. WORKER PRINCIPAL
# ============================================================

def ejecutar_integracion():
    sqs, queue_url = conectar_sqs()
    uid, models = conectar_odoo()

    print("🚀 Worker conectado y esperando mensajes...")

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=10,
                VisibilityTimeout=60
            )

            mensajes = response.get('Messages', [])

            if not mensajes:
                continue

            for msg in mensajes:
                receipt_handle = msg['ReceiptHandle']
                body = msg['Body']

                try:
                    id_pedido = procesar_mensaje(models, uid, body)

                    sqs.delete_message(
                        QueueUrl=queue_url,
                        ReceiptHandle=receipt_handle
                    )

                    print(f"🗑️ Mensaje eliminado de SQS. Pedido Odoo ID: {id_pedido}")
                    print("-" * 60)

                except Exception as e:
                    print("❌ Error procesando mensaje:")
                    print(e)
                    print("Traceback:")
                    traceback.print_exc()
                    print("Mensaje completo:")
                    print(body)

                    # No borramos el mensaje si falla.
                    # SQS lo volverá a entregar tras el VisibilityTimeout.
                    print("⚠️ El mensaje NO se ha borrado de SQS.")
                    print("-" * 60)

        except KeyboardInterrupt:
            print("🛑 Worker detenido manualmente.")
            break

        except Exception as e:
            print("❌ Error general del worker:")
            print(e)
            traceback.print_exc()
            time.sleep(5)


if __name__ == "__main__":
    ejecutar_integracion()
```
PASO 4: ¿Cómo lo ejecuto y lo pruebo?

Para que ver que funciona, sigue este orden:

    En la terminal: Ejecuta el script de Python:
    python worker_odoo.py
    (Verás el mensaje: "Worker conectado y esperando...")

    A. Usa el HTML en un bucket de S3. Cambia la url del api gw. Rellena el formulario y dale enviar. Mira los datos en Odoo.
    B. Desde otra terminal (o usando Postman): Vamos a simular que un cliente compra en la web enviando un pedido a la API Gateway:
    Bash
```
    curl -X POST https://tu-api-id.execute-api.us-east-1.amazonaws.com/prod/pedido \
    -H "Content-Type: application/json" \
    -d '{"nombre": "Empresa Sistemas L2", "email": "info@sistemas.com"}'
```
    Observa :

        La terminal donde corre el Python dirá instantáneamente: "Procesando pedido de: Empresa Sistemas L2".

        Entra en tu Odoo en la EC2, ve a Contactos y ¡verás que el nuevo cliente ha aparecido mágicamente sin que hayas tocado el ERP!

## API GW - Edit integration request
```
AWS Region
us-east-1
```
```
AWS service
Simple Queue Service (SQS)
```
```
HTTP method
POST
```
```
Action type
Use action name
```
```
Action name
SendMessage
```
```
Execution role
arn:aws:iam::658620698452:role/LabRole
```
```
URL request headers parameters
Name
Content-Type
Mapped from Info
'application/x-www-form-urlencoded'
Caching
```
```
Mapping templates
Content type
application/json
Generate template
Template body
Action=SendMessage&QueueUrl=https://sqs.us-east-1.amazonaws.com/658620698452/odoo&MessageBody=$util.urlEncode($input.body)
```

¿Qué tenemos ahora mismo configurado? 

    Action type: Use action name -> SendMessage

    HTTP Headers: Content-Type -> 'application/x-www-form-urlencoded'

    Mapping Template (application/json): Action=SendMessage&QueueUrl=https://sqs.us-east-1.amazonaws.com/658620698452/odoo&MessageBody=$util.urlEncode($input.body)

