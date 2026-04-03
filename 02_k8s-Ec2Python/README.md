
## Diagrama Odoo → AWS EKS (generación de PDF)
![alt text](Architecture.png)
```
Flujo descrito en el diagrama:

    Odoo (EC2): Ejecuta la función action_generate_aws_pdf definida en el archivo res_partner.py del módulo.

    Petición: Odoo emite una petición HTTP hacia Internet buscando la IP del contenedor desplegado en AWS EKS, accediendo al puerto 5000 a través de un servicio con balanceador de carga.

    AWS EKS: El contenedor EKS recibe el HTML generado por Odoo, lo procesa con el motor interno wkhtmltopdf para “dibujar” el PDF y responde devolviendo el archivo PDF por el mismo camino.

    Resultado: Odoo recibe los datos binarios del PDF, los codifica a Base64 y crea un nuevo registro en la tabla de Adjuntos (ir.attachment).

    Feedback: En el Chatter (historial de la derecha) del registro, aparece un mensaje automático:
    ✅ PDF generado exitosamente en AWS.
```
## Ayuda

Hay que cambiar las IPs en el código odoo3.py
Coge el usuario Administrador, el primero de contactos de odoo.
```
docker build --no-cache -t api-pdf-odoo .
```
```
docker run -dp 5000:5000 api-pdf-odoo
```

## Modulo sin cargar en Odoo
```
Crear contenedor .py
Lanzar el contenedor puerto 5000
Cambiar la IP en el fichero odoo3.py de odoo y generador pdf
Mirar en usuario administrator de Odoo el PDF
```

## Modulo cargado en Odoo
```
Subir .zip a addons
Descomprimirlo
Cambiar permisos. chmod -R 755 .
Lanzar Odoo
Modo desarrollador en ajustes
Buscar módulo AWS
Ir a contactos y entrar en usuario
Levantar el contenedor en ECS o EKS por el puerto 5000
Ejecutar el boton arriba a la derecha
(Da error porque la IP del contenedor por el puerto 5000 ha cambiado, en res_partner.py cambiar la ip url_aws = "http://44.192.81.69:5000/generar-pdf")
Parar Odoo, cambiar el fichero, lanzar Odoo y probar el generador de PDF.
```
## K8s
```
kubectl apply -f .
```
## Tips
Fase 1: Creación del Microservicio (Python/Flask)

El primer paso es crear la pequeña aplicación que recibirá un código HTML (por ejemplo, el diseño de la factura) y devolverá un archivo PDF.

1. Preparar el entorno local
Crea una carpeta en tu ordenador llamada generador-pdf y dentro crea un archivo llamado requirements.txt con las dependencias necesarias.
Plaintext
```
Flask==2.3.2
pdfkit==1.0.0
gunicorn==20.1.0
```
2. Escribir la lógica de la API
Crea un archivo llamado app.py. Este código levantará un servidor web muy ligero que escucha peticiones POST.
Python
```
from flask import Flask, request, send_file
import pdfkit
import io

app = Flask(__name__)

@app.route('/generar-pdf', methods=['POST'])
def generar_pdf():
    # Recibimos el HTML en formato JSON desde Odoo
    datos = request.get_json()
    html_content = datos.get('html', '<h1>Error: No hay HTML</h1>')
    
    # Configuramos pdfkit y generamos el PDF en memoria (sin guardar en disco)
    pdf_bytes = pdfkit.from_string(html_content, False)
    
    # Devolvemos el PDF como un archivo descargable
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name='documento.pdf'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```
Fase 2: Contenedorización (Docker)

Para que AWS Fargate pueda ejecutar nuestra API sin que tengamos que instalar Python o configurar servidores, debemos empaquetarla en una imagen Docker.

1. Crear el Dockerfile
En la misma carpeta, crea un archivo llamado Dockerfile (sin extensión). Este archivo es la "receta" que instala Linux, Python, la herramienta de PDFs y nuestro código.
Dockerfile
```
 Usamos una imagen oficial de Python ligera
FROM python:3.9-slim

Instalamos wkhtmltopdf (el motor subyacente necesario para pdfkit)
RUN apt-get update && apt-get install -y wkhtmltopdf

Establecemos el directorio de trabajo
WORKDIR /app

Copiamos los requisitos y los instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

Copiamos el código de la API
COPY app.py .

Exponemos el puerto 5000
EXPOSE 5000

Arrancamos la aplicación usando Gunicorn para producción
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```
2. Construir la imagen localmente
Abre la terminal en la carpeta del proyecto y ejecuta el comando de construcción.
Bash
```
docker build -t api-pdf-odoo .
```
Fase 3: Subida a Amazon ECR (Elastic Container Registry)

Ahora llevaremos nuestro contenedor desde nuestro ordenador local hasta la nube de AWS.

1. Crear el Repositorio en AWS
Entra en la consola de AWS, busca Amazon ECR y haz clic en "Create repository". Llámalo api-pdf-odoo y déjalo como privado.

2. Autenticar y Subir
Selecciona tu nuevo repositorio y haz clic en el botón View push commands (Ver comandos de envío). AWS te dará exactamente los 4 comandos que debes copiar y pegar en tu terminal para:

    Autenticar tu Docker local con AWS.

    Etiquetar (tag) tu imagen.

    Subir (push) la imagen a la nube.

Fase 4: Despliegue en Amazon ECS con Fargate o EKS (K8S)

Esta es la parte "Serverless" para contenedores. AWS ejecutará la imagen sin que encendamos máquinas virtuales (EC2).

Crear el Clúster ECS o EKS
Ve a Amazon ECS y crea un nuevo clúster. Dale el nombre Cluster-Microservicios y selecciona la infraestructura AWS Fargate (Serverless).

2. Crear la Definición de Tarea (Task Definition)
La definición de tarea le dice a AWS cuántos recursos necesita tu contenedor.

    Crea una nueva Task Definition.

    Tipo de lanzamiento: Fargate.

    CPU y Memoria: Selecciona lo mínimo (ej. 0.25 vCPU y 0.5 GB RAM) para ahorrar costes.

    En la sección de contenedores, pon el nombre de tu contenedor y pega la URI de la imagen que subiste a ECR en el paso anterior.

    Mapeo de puertos: Abre el puerto 5000 (TCP).

3. Ejecutar el Servicio
Ve a tu clúster y crea un nuevo Service.

    Selecciona tu Task Definition.

    Tareas deseadas (Desired tasks): 1.

    En la sección de Redes (Networking), crea un nuevo Security Group y asegúrate de añadir una regla de entrada (Inbound Rule) que permita tráfico TCP por el puerto 5000 desde cualquier lugar (0.0.0.0/0).

4. Obtener la IP Pública
Una vez que el servicio esté en estado "Running", entra en los detalles de la Tarea y copia la IP Pública. Tu microservicio ya está vivo en Internet.
