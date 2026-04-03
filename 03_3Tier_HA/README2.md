![alt text](Architecture.png)

## Tips

Fase 1: Preparación en AWS (Prerrequisitos)

Antes de tocar la terminal de Linux, asegúrate de que los "porteros" de AWS permiten la comunicación:

    RDS (PostgreSQL): Su Security Group debe permitir el puerto 5432 desde el Security Group de tu EC2.

    EFS (Disco de Red): Su Security Group debe permitir el puerto 2049 (NFS) desde el Security Group de tu EC2.

    EC2: Su Security Group debe permitir el puerto 8069 desde Internet (0.0.0.0/0).

Fase 2: Montaje y Persistencia de Amazon EFS

Conectamos el servidor Linux (EC2) al almacenamiento infinito de AWS.

1. Instalar utilidades y crear el punto de montaje:
Bash
```
sudo yum install -y amazon-efs-utils
sudo mkdir -p /mnt/efs
```
2. Montarlo temporalmente (reemplaza TU_ID_DE_EFS):
Bash
```
sudo mount -t efs fs-TU_ID_DE_EFS:/ /mnt/efs
```
3. Hacerlo resistente a reinicios:
Bash
```
sudo nano /etc/fstab
# Añade esta línea al final del archivo:
# fs-TU_ID_DE_EFS:/ /mnt/efs efs _netdev,noresvport,tls 0 0
```
Fase 3: Estructura de Carpetas y "Permisos Agresivos"

Preparamos la casa para que Docker y Odoo no se peleen por los permisos de escritura debido al desajuste de IDs internos.

1. Crear carpetas base y el archivo de configuración:
Bash
```
sudo mkdir -p /mnt/efs/odoo_data
sudo mkdir -p /mnt/efs/addons
sudo mkdir -p /mnt/efs/config
sudo touch /mnt/efs/config/odoo.conf
```
2. Pre-crear las carpetas ocultas que Odoo necesita:
(Para evitar el famoso Permission denied: '/var/lib/odoo/.local')
Bash
```
sudo mkdir -p /mnt/efs/odoo_data/.local/share/Odoo/sessions
```
3. Aplicar permisos universales (Fuerza Bruta Controlada):
(Abrimos los permisos al 777 para que el usuario interno de Odoo, sea el 101, 104 o el que sea, pueda escribir sin restricciones).
Bash
```
sudo chmod -R 777 /mnt/efs/odoo_data
sudo chmod -R 777 /mnt/efs/addons
sudo chmod -R 777 /mnt/efs/config
```
Fase 4: El Archivo docker-compose.yaml

Creamos el archivo que define la arquitectura.
Bash
```
mkdir -p ~/odoo_prod
cd ~/odoo_prod
nano docker-compose.yaml
```
Pega este código exacto:
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
      # Conexión a AWS RDS
      - HOST=tu-base-de-datos.cxxxxxx.us-east-1.rds.amazonaws.com
      - USER=postgres
      - PASSWORD=tu_contraseña_segura
      - PORT=5432
    volumes:
      # Conexión al almacenamiento AWS EFS
      - /mnt/efs/odoo_data:/var/lib/odoo
      - /mnt/efs/addons:/mnt/extra-addons
      - /mnt/efs/config:/etc/odoo
```
Fase 5: Inicialización "Francotirador" y Arranque Final

Como la base de datos de RDS está vacía, debemos inicializar la estructura de tablas de Odoo de forma manual antes de arrancar el servidor web.

1. Inicializar la base de datos (El Francotirador):
Este comando lanza un contenedor desechable que entra a RDS, crea las tablas base y se apaga automáticamente.
Bash
```
docker-compose run --rm odoo odoo -i base -d odoo --stop-after-init
or
docker-compose run --rm odoo odoo -u all -d odoo --stop-after-init
```
(Espera un par de minutos a que termine de procesar las tablas).

2. Levantar la arquitectura definitiva:
Una vez creada la base de datos, levantamos el servidor Odoo en segundo plano (-d).
Bash
```
docker-compose up -d
```
3. Abre tu navegador y accede a http://TU_IP_PUBLICA_EC2:8069.

