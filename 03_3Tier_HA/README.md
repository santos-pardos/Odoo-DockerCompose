![alt text](Architecture.png)

## Create RDS Postgress 
```
User: odoo
Password A123456b
BBDD: odoo
```
## User-data - Ami Linux 2023
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
