![alt text](Architecture.png)

## Tips

1. docker-compose.yml

Asumiendo que has montado tu EFS en la ruta /mnt/efs de tu servidor EC2, el archivo quedaría así:
YAML
```
version: '3.8'

services:
  odoo:
    image: odoo:19.0
    container_name: odoo_app
    restart: always
    ports:
      - "8069:8069"
      - "8072:8072"
    environment:
      - HOST=tu-base-de-datos.cxxxxxxx.eu-west-1.rds.amazonaws.com
      - USER=postgres
      - PASSWORD=tu_contraseña_super_segura
      - PORT=5432
    volumes:
      # --- PERSISTENCIA EN EFS ---
      # Izquierda: Ruta real en tu servidor EC2 (donde está montado EFS)
      # Derecha: Ruta interna del contenedor Odoo
      - /mnt/efs/odoo_data:/var/lib/odoo
      
      # Mapeo de módulos
      - ./addons:/mnt/extra-addons

# Fíjate que hemos borrado la sección "volumes:" que había al final
# porque ya no le pedimos a Docker que gestione el volumen, lo gestiona AWS (EFS).
```

2. Pasos críticos en el Host (EC2) antes de hacer docker-compose up

Como el disco EFS está fuera de Docker, hay un detalle técnico vital: los permisos de lectura y escritura. El usuario interno del contenedor de Odoo (que se llama odoo y suele tener el ID 104) necesita permiso para escribir en esa carpeta de EFS.

Ejecuta estos comandos en tu terminal de la instancia EC2:

    Crea la carpeta dentro de tu EFS:
    Bash
```
    sudo mkdir -p /mnt/efs/odoo_data
```
    Dásela al usuario de Odoo (UID 104):
    Si no haces esto, Odoo arrancará, intentará crear la carpeta filestore o sessions dentro del EFS, Linux le dirá "Permiso denegado", y el contenedor se reiniciará en bucle.
    Bash
```
    sudo chown -R 104:104 /mnt/efs/odoo_data
    sudo chmod -R 775 /mnt/efs/odoo_data
```
3. Recordatorio del Security Group de EFS

Igual que te pasó con RDS, EFS tiene su propio Security Group. Para que tu EC2 pueda montar el disco EFS, el Security Group del EFS debe tener una regla de entrada (Inbound Rule) permitiendo el tráfico NFS (Puerto 2049) desde el Security Group de tu máquina EC2.

Una vez tengas la carpeta creada con los permisos 104:104 y el docker-compose.yml actualizado, simplemente levanta el servicio de nuevo. ¡Tendrás una arquitectura 3-Tier impecable y escalable!


La carpeta estándar y más profesional en Linux para montar sistemas de archivos externos (como EFS, discos EBS adicionales o recursos compartidos de red) es el directorio /mnt (que viene de mount o montaje).

Para mantener todo organizado, la mejor práctica es no montarlo directamente en /mnt, sino crear una subcarpeta con un nombre descriptivo. En tu caso, te recomiendo encarecidamente usar /mnt/efs.

Aquí tienes el proceso exacto de cómo prepararlo en tu Amazon Linux (EC2) para que quede perfecto y, lo más importante, para que sobreviva si reinicias el servidor.
Paso 1: Crear la carpeta de montaje

Abre la terminal de tu instancia EC2 y crea el directorio vacío que servirá como "puerta de enlace" hacia tu disco EFS:
Bash
```
sudo mkdir -p /mnt/efs
```
Paso 2: Instalar las utilidades de EFS (Recomendado)

Como estás usando Amazon Linux, AWS tiene una herramienta optimizada que hace que montar EFS sea mucho más fácil y seguro (encripta el tráfico por defecto). Instálala con:
Bash
```
sudo yum install -y amazon-efs-utils
```
Paso 3: Montar el EFS manualmente (Para probar)

Ahora vamos a conectar tu EC2 con el EFS. Necesitas el ID de tu sistema de archivos EFS (lo encuentras en la consola de AWS, empieza por fs- seguido de números y letras, por ejemplo: fs-0123456789abcdef0).
Bash
```
sudo mount -t efs fs-TU_ID_DE_EFS:/ /mnt/efs
```
Si no da ningún error, significa que ya está conectado. Puedes comprobarlo escribiendo df -h y verás tu EFS listado en la parte inferior apuntando a /mnt/efs.
🚨 Paso 4: Hacerlo persistente (El truco de experto)

Este es un error clásico en los despliegues: si dejas el montaje así, el día que reinicies la máquina EC2 o se actualice, el enlace a EFS desaparecerá, Docker arrancará, creará una carpeta local vacía y Odoo "perderá" todas sus imágenes y PDFs.

Para decirle a Linux que monte el EFS automáticamente cada vez que arranque, debemos editar el archivo de sistemas de archivos (/etc/fstab):

    Abre el archivo:
    Bash
```
    sudo nano /etc/fstab
```
    Ve a la última línea y añade esto (reemplazando tu ID):
    Plaintext
```
    fs-TU_ID_DE_EFS:/ /mnt/efs efs _netdev,noresvport,tls 0 0
```
    Guarda y sal (Ctrl+O, Enter, Ctrl+X).

Resumen de conexión con tu Docker:

Una vez que has hecho esto, tu sistema Linux local tiene un túnel directo hacia el almacenamiento infinito de AWS en /mnt/efs.

Es por eso que en el docker-compose.yml que te di antes, la línea del volumen era:
```
- /mnt/efs/odoo_data:/var/lib/odoo
```
Esto significa: "Coge todo lo que el contenedor intente guardar en su carpeta interna /var/lib/odoo y lánzalo a la carpeta /mnt/efs/odoo_data de mi máquina Linux, la cual viaja mágicamente hasta AWS EFS".
