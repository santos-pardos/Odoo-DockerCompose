![alt text](Architecture.png)

## Create RDS Postgress (Copy Endpoint, change it in the db_host variable in the user-data file)
```
User: odoo
Password A123456b
BBDD: odoo
```
## Create EFS (Copy Endpoint, change it twice in the fs-xxxxxxx variable in the user-data file)

## User-data - Ami Linux 2023
```
#!/bin/bash
# 1. Actualizar e instalar Docker y utilidades de EFS
dnf update -y
dnf install -y docker amazon-efs-utils
systemctl enable --now docker
usermod -aG docker ec2-user

# 2. Instalar Docker Compose V2
mkdir -p /usr/local/lib/docker/cli-plugins/
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# 3. Configurar el montaje de EFS (REEMPLAZA fs-XXXXXX con tu ID)
mkdir -p /mnt/odoo-data
# Montamos el EFS
sudo mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport fs-04bb2995d5c63aab7.efs.us-east-1.amazonaws.com:/ /mnt/odoo-data
# Aseguramos que se monte en cada reinicio
echo "fs-04bb2995d5c63aab7.efs.us-east-1.amazonaws.com:/ /mnt/odoo-data efs _netdev,tls 0 0" >> /etc/fstab

# 4. PASO CLAVE: Permisos para el contenedor (UID 101 es el usuario 'odoo')
chown -R 101:101 /mnt/odoo-data
chmod -R 775 /mnt/odoo-data

# 5. Preparar directorio de trabajo
mkdir -p /home/ec2-user/odoo-pilot
cd /home/ec2-user/odoo-pilot

# 6. Crear el archivo odoo.conf (Añadimos proxy_mode para el balanceador)
cat <<EOF > odoo.conf
[options]
admin_passwd = admin_master_pilot
db_host = odoo.cfiy5oksqwsu.us-east-1.rds.amazonaws.com
db_user = odoo
db_password = A123456b
db_port = 5432
http_port = 8069
proxy_mode = True
EOF

# 7. Crear el archivo docker-compose.yml usando el EFS
cat <<EOF > docker-compose.yml
services:
  odoo:
    image: odoo:latest
    container_name: odoo_piloto
    ports:
      - "80:8069"
    volumes:
      - /mnt/odoo-data:/var/lib/odoo
      - ./odoo.conf:/etc/odoo/odoo.conf
    environment:
      - HOST=odoo.cfiy5oksqwsu.us-east-1.rds.amazonaws.com
      - USER=odoo
      - PASSWORD=A123456b
    restart: always
EOF

# 8. Lanzar Odoo
docker compose up -d

# 9. Permisos finales para la carpeta del proyecto
chown -R ec2-user:ec2-user /home/ec2-user/odoo-pilot
```


## First Version (Don't use it)
### User-data 
Note: Change RDS Endpoint in the user-data file
```
#!/bin/bash
# 1. Actualizar e instalar Docker en Amazon Linux 2023
dnf update -y
dnf install -y docker
systemctl enable --now docker
usermod -aG docker ec2-user

# 2. Instalar Docker Compose V2
mkdir -p /usr/local/lib/docker/cli-plugins/
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# 3. Preparar directorio de trabajo
mkdir -p /home/ec2-user/odoo-pilot
cd /home/ec2-user/odoo-pilot

# 4. Crear el archivo odoo.conf con tus credenciales de RDS
cat <<EOF > odoo.conf
[options]
admin_passwd = admin_master_pilot
db_host = odoo.cfiy5oksqwsu.us-east-1.rds.amazonaws.com
db_user = odoo
db_password = A123456b
db_port = 5432
http_port = 8069
EOF

# 5. Crear el archivo docker-compose.yml
cat <<EOF > docker-compose.yml
services:
  odoo:
    image: odoo:latest
    ports:
      - "80:8069"
    volumes:
      - odoo-web-data:/var/lib/odoo
      - ./odoo.conf:/etc/odoo/odoo.conf
    environment:
      - HOST=odoo.cfiy5oksqwsu.us-east-1.rds.amazonaws.com
      - USER=odoo
      - PASSWORD=A123456b
    restart: always

volumes:
  odoo-web-data:
EOF

# 6. Lanzar Odoo
docker compose up -d

# 7. Asegurar permisos para el usuario ec2-user
chown -R ec2-user:ec2-user /home/ec2-user/odoo-pilot
```

## Create Odoo tables
```
sudo dnf install -y postgresql15
```
```
docker run --rm -it \
  -v odoo-data:/var/lib/odoo \
  -v /home/ec2-user/odoo-pilot/odoo.conf:/etc/odoo/odoo.conf \
  odoo:latest odoo -c /etc/odoo/odoo.conf -d odoo -i sale,stock,account --stop-after-init
```
```
docker stop odoo
docker start odoo
```
```
Login user: admin
Password user: admin
```

## Delete Odoo Tables
```
psql -h odoo.cfiy5oksqwsu.us-east-1.rds.amazonaws.com -U odoo -d odoo
```
```
-- 1. Borrar todo el contenido (tablas, vistas, tipos)
DROP SCHEMA public CASCADE;

-- 2. Recrear el espacio vacío
CREATE SCHEMA public;

-- 3. Devolver permisos al usuario odoo
GRANT ALL ON SCHEMA public TO odoo;
GRANT ALL ON SCHEMA public TO public;

-- 4. Salir
\q
```
## ALB - ASG
Modificación necesaria en el odoo.conf
```
Cuando hay un balanceador delante, Odoo debe saber que no está recibiendo tráfico directo. Debes añadir estas líneas a tu archivo de configuración en ambas instancias:

proxy_mode = True
```
```
La configuración del Target Group de tu balanceador en AWS, debes activar las Sticky Sessions (Sesiones basadas en cookies)
```
## EFS
```
sudo mkdir /mnt/odoo-data
sudo mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport fs-04bb2995d5c63aab7.efs.us-east-1.amazonaws.com:/ /mnt/odoo-data
```
```
DAR PERMISOS AL USUARIO DE ODOO (Paso Clave)
Cambiamos el dueño del EFS al UID 101 que usa el contenedor
sudo chown -R 101:101 /mnt/odoo-data
sudo chmod -R 775 /mnt/odoo-data
```
```
services:
  odoo:
    image: odoo:latest
    ports:
      - "80:8069"
    volumes:
      - /mnt/odoo-data:/var/lib/odoo
      - ./odoo.conf:/etc/odoo/odoo.conf
    environment:
      - HOST=odoo.cfiy5oksqwsu.us-east-1.rds.amazonaws.com
      - USER=odoo
      - PASSWORD=A123456b
    restart: always

volumes:
  odoo-web-data:
```
```
docker run --rm -it \
  -v /mnt/odoo-data:/var/lib/odoo \
  -v /home/ec2-user/odoo-pilot/odoo.conf:/etc/odoo/odoo.conf \
  odoo:latest odoo -c /etc/odoo/odoo.conf -d odoo -u web --stop-after-init
```


## Login
user/email: admin
password: admin
