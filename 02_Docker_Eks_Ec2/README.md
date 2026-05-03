
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

## Modulo Odoo - Generación PDF
Cambia los permisos a la carpeta addons y al módulo antes de lanzar odoo
```
chmod -R 755 .
```
Cómo instalar el módulo en Odoo 19

Dado que tienes tu Odoo en localhost, la forma oficial y más fiable de instalar módulos personalizados es esta:

    Descomprime el ZIP: Extrae la carpeta aws_pdf_generator que viene dentro del ZIP.

    Copia la carpeta a tus addons: Pega esa carpeta dentro del directorio addons de tu instalación local de Odoo (normalmente está en la ruta donde instalaste Odoo, en la carpeta server/odoo/addons o un directorio de addons personalizado si lo configuraste así).

    Reinicia Odoo: Detén el servicio de Odoo y vuelve a iniciarlo para que lea la nueva carpeta.

    Actualiza la lista de aplicaciones:

        Abre Odoo en tu navegador e inicia sesión.

        Activa el Modo Desarrollador (Ajustes > Activar modo desarrollador).

        Ve al menú superior Aplicaciones (Apps).

        En el menú superior (Odoo 19 suele esconderlo bajo la opción "Aplicaciones" o en un menú desplegable "Acción"), haz clic en "Actualizar lista de aplicaciones" (Update Apps List) y confirma.

    Instala el módulo: En el buscador, quita el filtro por defecto de "Aplicaciones", busca la palabra AWS, y te aparecerá tu nuevo módulo Generador de PDF en AWS Fargate. ¡Dale a Instalar!

Cuando entres en la ficha de cualquier cliente en la app de Contactos, verás en la parte superior un flamante botón azul llamado "Generar PDF (Nube AWS)". Ya tienes una integración real, empaquetada como un módulo profesional de Odoo.

1. ¿Dónde aparecerá el botón?

Si vas a la aplicación de Contactos y abres a cualquier persona o empresa, verás una barra gris en la parte superior (el "Header"). Ahí aparecerá un botón azul brillante con el texto: "Generar PDF (Nube AWS)" y un pequeño icono de una nube.
2. ¿Qué ocurre técnicamente cuando haces clic?

Cuando pulses ese botón, se dispara el siguiente flujo arquitectónico:

    Odoo (Local): Ejecuta la función action_generate_aws_pdf que escribimos en el archivo res_partner.py del módulo.

    La Petición: Odoo emite una señal hacia Internet buscando la IP de tu instancia de AWS (44.192.81.69) por el puerto 5000.

    AWS Fargate/Docker: El contenedor recibe el HTML que Odoo le envía, usa su motor interno (wkhtmltopdf) para "dibujar" el PDF y lo envía de vuelta por el mismo camino.

    El Resultado: Odoo recibe los datos binarios del PDF, los transforma a Base64 y crea un nuevo registro en la tabla de Adjuntos.

    Feedback: En el "Chatter" (el historial de la derecha), aparecerá un mensaje automático diciendo: "✅ PDF generado exitosamente en AWS".

3. Checklist para que el botón NO falle

Para que cuando pulses el botón no te dé un error de "Connection Timeout", asegúrate de estos tres puntos (muy importantes para explicar a los alumnos):

    Contenedor Vivo: En tu terminal de AWS, el comando docker ps debe mostrar que el contenedor api-pdf-odoo está en estado "Up".

    Puerto Abierto: En el Security Group de AWS, la regla para el puerto 5000 debe estar activa para 0.0.0.0/0.

    Librería Python: Tu Odoo local debe tener instalada la librería requests. Como usas Odoo 19 Community, es casi seguro que ya la tiene, pero si fallara, tendrías que hacer un pip install requests en el entorno donde corre tu Odoo.

 Los últimos pasos en Odoo:

    Reinicia tu servicio de Odoo para que vuelva a escanear el disco duro con sus nuevos permisos. (Dependiendo de cómo lo hayas instalado, suele ser algo como sudo systemctl restart odoo o simplemente detener y volver a lanzar tu comando de ejecución).

    Ve a Odoo y asegúrate de tener el Modo Desarrollador activado.

    Ve a Aplicaciones.

    Haz clic en Actualizar lista de aplicaciones (Update Apps List) en el menú superior.

    Quita el filtro azul de "Aplicaciones" de la barra de búsqueda y busca la palabra AWS.

    Paso 1: Ve a la aplicación de Contactos

    Vuelve a la pantalla principal de tu Odoo.

    Entra en la aplicación de Contactos.

    Haz clic en cualquier cliente que tengas creado (o crea uno nuevo con un nombre y un email de prueba).

Paso 2: Busca el nuevo botón

    Una vez dentro de la ficha del cliente, fíjate en la parte superior izquierda del formulario, justo encima del nombre del cliente (en la zona gris clara que llamamos el Header).

    Deberías ver tu nuevo botón destacado que dice "Generar PDF (Nube AWS)" con el icono de una nubecita.

Paso 3: ¡Haz la prueba de fuego!

    (Importante: Asegúrate de que tu contenedor Docker en AWS sigue encendido ejecutando docker run -d -p 5000:5000 api-pdf-odoo en tu terminal de AWS, de lo contrario dará error de conexión).

    Haz clic en el botón "Generar PDF (Nube AWS)".

    Odoo se quedará "pensando" un par de segundos. En este exacto momento, Odoo está viajando por internet, golpeando el puerto 5000 de tu IP de AWS, el contenedor Docker está procesando el HTML, creando el archivo binario y devolviéndolo a Odoo.

Paso 4: Comprueba el resultado
Si la integración ha sido un éxito, la página se refrescará ligeramente y verás dos evidencias de que ha funcionado:

    En el historial (Chatter): En el panel derecho (o en la parte inferior, según el tamaño de tu monitor), verás un nuevo mensaje automático en el registro del cliente que dice: "✅ PDF generado exitosamente en AWS y guardado en adjuntos."

    El archivo PDF: En la parte superior derecha de la pantalla, busca el icono del clip de papel 📎 (Adjuntos). Verás que ahora marca que hay un documento. Haz clic en el clip y ahí estará tu archivo AWS_NombreDelCliente.pdf.

## AWS IP Changed
Paso 1: Averiguar tu nueva IP en AWS

    Ve a la consola de AWS.

    Entra en EC2 > Instancias.

    Selecciona tu instancia y copia la nueva Dirección IPv4 pública que aparece en los detalles.

Paso 2: Actualizar el código en Odoo

Como ya tienes el módulo instalado en tu carpeta addons, vamos a editar el archivo directamente:

    Ve a tu instalación de Odoo y entra en la ruta: addons/aws_pdf_generator/models/res_partner.py

    Abre el archivo res_partner.py con cualquier editor de texto.

    Localiza la línea 10, que dice así:
    Python

    url_aws = "http://44.192.81.69:5000/generar-pdf"

    Cambia la IP antigua (44.192.81.69) por la nueva IP que acabas de copiar de AWS.

    Guarda el archivo.

Paso 3: Reiniciar Odoo (¡Muy importante!)

Cuando cambias un archivo .xml en Odoo basta con actualizar la aplicación en el navegador, pero cuando cambias un archivo .py (código Python), debes reiniciar el servidor de Odoo obligatoriamente para que vuelva a leer el código en la memoria RAM.

    Detén tu servidor Odoo y vuelve a iniciarlo (con Ctrl+C en la terminal, o con sudo service odoo restart si lo tienes como servicio de sistema).

Paso 4: ¡Vuelve a probar!

Entra en la ficha de tu cliente, haz clic en el botón de "Generar PDF (Nube AWS)" y esta vez la conexión volverá a funcionar perfectamente.
