
## Steps

1. Configuración de Infraestructura (Consola AWS)
A. AWS EFS (El Disco)

    Crear el File System: Crea un EFS en la misma VPC de tu EKS. Anota el fs-XXXXXXXX.

    Mount Targets: Asegúrate de que el EFS tenga puntos de montaje en todas las subredes de tu clúster.

    Security Groups (Clave de conexión): * El SG del EFS debe permitir la entrada al puerto NFS (2049) desde el SG de los nodos de EKS.

        El SG de los Nodos debe permitir la entrada al puerto PostgreSQL (5432) desde el propio SG de los nodos (para que Odoo y la DB hablen entre sí).

2. Preparación del EFS (Desde una EC2)

Monta el EFS en cualquier instancia EC2 de la misma VPC para preparar las carpetas.
A. Montaje y Creación de Carpetas
Bash

Montar el disco
sudo mkdir -p /mnt/efs
sudo mount -t efs fs-XXXXXXXX:/ /mnt/efs

Crear la estructura necesaria para los YAML
sudo mkdir -p /mnt/efs/addons
sudo mkdir -p /mnt/efs/config
sudo mkdir -p /mnt/efs/odoo-data
sudo mkdir -p /mnt/efs/postgres-data

B. El archivo odoo.conf (Imprescindible)

Crea el archivo en /mnt/efs/config/odoo.conf con este contenido exacto:
Ini, TOML
```
[options]
admin_passwd = admin_password_maestra
db_host = odoo-db
db_port = 5432
db_user = odoo
db_password = tu_password_segura
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
data_dir = /var/lib/odoo
proxy_mode = True
```
C. Permisos Totales (Para Piloto/Demo)

Como es un piloto y queremos evitar cualquier bloqueo de sistema, aplicamos los permisos máximos (777) y asignamos los propietarios que usan los contenedores por defecto:
Bash

1. Asignar propietarios (101 para Odoo, 999 para Postgres)
sudo chown -R 101:101 /mnt/efs/addons /mnt/efs/config /mnt/efs/odoo-data
sudo chown -R 999:999 /mnt/efs/postgres-data

2. Dar permisos totales (Lectura, Escritura, Ejecución para todos)
sudo chmod -R 777 /mnt/efs/addons
sudo chmod -R 777 /mnt/efs/config
sudo chmod -R 777 /mnt/efs/odoo-data
sudo chmod -R 777 /mnt/efs/postgres-data

Nota: Postgres es muy delicado; si con 777 te da error en los logs, ponle chmod 700 /mnt/efs/postgres-data.
3. Resumen de ejecución (kubectl)

Una vez que el EFS tiene las carpetas y el archivo de configuración, lanza tus archivos en este orden:

    Secretos (01): Crea la contraseña de la DB (en base64).

    Almacenamiento (02): Crea el StorageClass (CSI de EFS), el PersistentVolume (con tu ID de EFS) y el PVC.

    Base de Datos (03): Lanza el Deployment y el Service de Postgres. Espera a que esté Running.

    Odoo Web (04): Lanza el Deployment de Odoo. Utilizará el odoo.conf que ya pusiste en el EFS.

    Servicio/ALB (05): Lanza el Service tipo LoadBalancer para generar la URL pública de AWS.

4. Checklist de Verificación Final

    ¿No carga la web? Revisa que el ALB en AWS tenga sus Health Checks en verde.

    ¿Error 500? Revisa kubectl logs deployment/odoo-web. Si dice "Connection Refused", revisa el Security Group (Puerto 5432).

    ¿Persistencia? Puedes borrar todos los Pods; al volver a subir, Odoo leerá el EFS y mantendrá tu base de datos y tus fotos/logos intactos
