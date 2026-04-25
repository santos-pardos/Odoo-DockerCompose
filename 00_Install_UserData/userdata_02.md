#!/bin/bash
set -e

# 1. Actualizar e instalar Docker
dnf update -y
dnf install -y docker
systemctl enable --now docker
usermod -aG docker ec2-user

# 2. Instalar Docker Compose V2
mkdir -p /usr/local/lib/docker/cli-plugins/
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# 3. Crear estructura de directorios
mkdir -p /opt/odoo/odoo-data/.local
mkdir -p /opt/odoo/postgres-data
mkdir -p /opt/odoo/nginx
mkdir -p /home/ec2-user/odoo-pilot

# 4. Permisos correctos para Odoo
chown -R 101:101 /opt/odoo/odoo-data
chmod -R 775 /opt/odoo/odoo-data

cd /home/ec2-user/odoo-pilot

# 5. Crear configuración de Odoo
cat <<EOF > odoo.conf
[options]
admin_passwd = admin_master_pilot
db_host = postgres
db_user = odoo
db_password = A123456b
db_port = 5432
http_port = 8069
proxy_mode = True
without_demo = all
EOF

# 6. Crear configuración de Nginx
cat <<EOF > /opt/odoo/nginx/default.conf
server {
    listen 80;
    server_name _;

    proxy_read_timeout 720s;
    proxy_connect_timeout 720s;
    proxy_send_timeout 720s;

    proxy_set_header X-Forwarded-Host \$host;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_set_header X-Real-IP \$remote_addr;

    client_max_body_size 100m;

    location / {
        proxy_pass http://odoo:8069;
    }

    location /longpolling {
        proxy_pass http://odoo:8072;
    }

    location /websocket {
        proxy_pass http://odoo:8072;
    }
}
EOF

# 7. Crear docker-compose.yml
cat <<EOF > docker-compose.yml
services:
  postgres:
    image: postgres:15
    container_name: postgres_odoo
    environment:
      POSTGRES_DB: postgres
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: A123456b
    volumes:
      - /opt/odoo/postgres-data:/var/lib/postgresql/data
    restart: always
    networks:
      - odoo-net

  odoo:
    image: odoo:19
    container_name: odoo_piloto
    depends_on:
      - postgres
    ports:
      - "8069:8069"
    volumes:
      - /opt/odoo/odoo-data:/var/lib/odoo
      - ./odoo.conf:/etc/odoo/odoo.conf:ro
    command: odoo -c /etc/odoo/odoo.conf
    restart: always
    networks:
      - odoo-net

  nginx:
    image: nginx:latest
    container_name: nginx_odoo
    depends_on:
      - odoo
    ports:
      - "80:80"
    volumes:
      - /opt/odoo/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
    restart: always
    networks:
      - odoo-net

networks:
  odoo-net:
    driver: bridge
EOF

# 8. Permisos del proyecto
chown -R ec2-user:ec2-user /home/ec2-user/odoo-pilot

# 9. Levantar PostgreSQL primero
docker compose up -d postgres
sleep 20

# 10. Crear base de datos Odoo limpia
docker exec -i postgres_odoo psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS odoo;"
docker exec -i postgres_odoo psql -U odoo -d postgres -c "CREATE DATABASE odoo OWNER odoo;"

# 11. Levantar Odoo
docker compose up -d odoo
sleep 20

# 12. Inicializar base de datos Odoo
docker exec -i odoo_piloto odoo -c /etc/odoo/odoo.conf -d odoo -i base --without-demo=all --stop-after-init || true

# 13. Reiniciar Odoo después de inicializar
docker compose restart odoo

# 14. Levantar Nginx
docker compose up -d nginx