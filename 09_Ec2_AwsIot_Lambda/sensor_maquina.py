import time
import json
import random
import ssl
import paho.mqtt.client as mqtt

# --- CONFIGURACIÓN ---
ENDPOINT = "TU_ENDPOINT_ATS_AQUI" # Ej: xxxx-ats.iot.us-east-1.amazonaws.com
CLIENT_ID = "Maquina-01"
TOPIC = "fabrica/maquina1/telemetria"

# Pon el nombre exacto de los archivos que descargaste de AWS
PATH_TO_CERT = "xxx-certificate.pem.crt"
PATH_TO_KEY = "xxx-private.pem.key"
PATH_TO_ROOT = "AmazonRootCA1.pem"

# Configuración de seguridad MQTT con AWS (TLS)
client = mqtt.Client(client_id=CLIENT_ID)
client.tls_set(PATH_TO_ROOT, certfile=PATH_TO_CERT, keyfile=PATH_TO_KEY, 
               tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)

# Conexión a AWS IoT Core (Puerto 8883 es obligatorio para MQTT seguro)
print(f"Conectando a AWS IoT Core en {ENDPOINT}...")
client.connect(ENDPOINT, 8883, 60)
client.loop_start()

print("✅ Conectado. Iniciando envío de telemetría (Ctrl+C para parar).")

try:
    while True:
        # Simulamos datos normales (con picos ocasionales para disparar la alarma)
        temp = random.uniform(50.0, 85.0) # A veces pasará de 80
        vib = random.uniform(20.0, 105.0) # A veces pasará de 100
        
        payload = json.dumps({
            "maquina_id": CLIENT_ID, 
            "temperatura": round(temp, 2), 
            "vibracion": round(vib, 2)
        })
        
        print(f"📡 Publicando en {TOPIC}: {payload}")
        client.publish(TOPIC, payload, qos=1)
        
        time.sleep(5) # Enviar dato cada 5 segundos
except KeyboardInterrupt:
    print("\nDeteniendo máquina...")
    client.loop_stop()
    client.disconnect()