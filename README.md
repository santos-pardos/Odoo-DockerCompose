## Odoo Installation - Docker

## LABs - Arquitecturas Modernas / Integraciones

| # | Tema | # | Tema |
|---|------|---|------|
| 0 | Instalación | 8 | Backup |
| 1 | Desacoplo | 9 | IoT |
| 2 | Microservicios | 10 | AI |
| 3 | Alta Disponibilidad | 11 | CQRS |
| 4 | Serverless | 12 | Gen AI |
| 5 | Workflows | 13 | Multi Region |
| 6 | Analítica | 14 | Seguridad |
| 7 | Escalado | | | 15 EKS Kubernetes |


### 1. Install Docker
#### Ubuntu
```
# Add Docker's official GPG key:
sudo apt update
sudo apt install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
```
```
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```
```
sudo usermod -aG docker $USER
newgrp docker
```
```
sudo apt install docker-compose -y
sudo apt install git -y
```



#### AMI Linux 2023
```
sudo dnf install docker -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
sudo newgrp docker
```
```
sudo curl -s https://api.github.com/repos/docker/compose/releases/latest | grep browser_download_url | grep docker-compose-linux-x86_64 | cut -d '"' -f 4 | wget -qi -
sudo chmod +x docker-compose-linux-x86_64
sudo mv docker-compose-linux-x86_64 /usr/local/bin/docker-compose
docker-compose --version
```
```
mkdir -p ~/.docker/cli-plugins
curl -L https://github.com/docker/buildx/releases/download/v0.17.0/buildx-v0.17.0.linux-amd64 \
  -o ~/.docker/cli-plugins/docker-buildx
chmod +x ~/.docker/cli-plugins/docker-buildx
docker buildx version
```
```
sudo dnf install git -y
```
### 2. Clone Git Repository
```
git clone https://github.com/santos-pardos/Odoo-DockerCompose.git
```

### 3. EC2 EIP
```
Assing an EIP to EC2 Odoo
```
```
http://EIP:8069
```
Note: Open the 8069 port in the SG in EC2

### 4. NGINX - Reverse Proxy
```
sudo dnf install nginx -y
sudo systemctl start nginx
sudo systemctl enable nginx
```
```
sudo nano /etc/nginx/conf.d/odoo.conf
```
```
server {
    listen 80;

    location / {
        proxy_pass http://127.0.0.1:8069;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```
```
sudo systemctl restart nginx
```
### 5. Launch
```
cd Odoo-DockerCompose
sudo chown -R $USER:$USER addons config sessions
docker-compose up -d
```
```
docker-compose build --no-cache && docker compose up
```
### 6. Stop
```
docker-compose down
```

### 7. Tips
```
sudo chown -R $USER:$USER addons config sessions
```
```
docker logs <container_name>
The actual log will also be at /etc/odoo/odoo.log inside the container
```
### 8. DdBeaver
```
docker run -d --network odoo-docker_default --name cloudbeaver --restart unless-stopped -p 8978:8978 -v /opt/cloudbeaver/workspace dbeaver/cloudbeaver:latest
```

### 9. PSQL
```
docker-compose ps
docker-compose logs db
docker-compose exec db ss -lnt
docker-compose exec db psql -U odoo -d postgres
docker-compose exec db bash
docker exec -it ID-Postgress /bin/bash
psql -U odoo -d postgres
\du               usuarios
\l                bases de datos
\dt               tables
\dt *.*
\c nombre_bd_odoo cambia de bbdd
\d nombre-tabla   estructura tabla
\dt res_*
\dt ir_*
\dt sale_*
###  Links
```
```
https://medium.com/@rajeshpachaikani/deploying-odoo-in-minutes-with-docker-compose-61a4d07b8877
```





