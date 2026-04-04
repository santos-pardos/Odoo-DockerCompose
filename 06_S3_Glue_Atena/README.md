![alt text](Architecture.png)

## CSV

¿Qué aspecto tiene el CSV?

```
order_id,date_order,customer_name,country,product_category,product_name,quantity,unit_price,total_amount,status
SO0842,2025-01-01 00:00:00,Comercial Sur,Chile,Hardware,Servidor Dell PowerEdge,14,1382.45,19354.3,Sale
SO0311,2025-01-02 00:00:00,Tech Solutions,España,Servicios Cloud,Migración de Servidores,3,845.2,2535.6,Sale
SO0991,2025-01-02 00:00:00,Industrias XYZ,México,Consultoría,Diseño de Arquitectura,8,150.75,1206.0,Cancelled
SO0105,2025-01-04 00:00:00,Empresa Alfa,Perú,Licencias Software,Odoo Enterprise (50 Users),1,950.0,950.0,Sale
SO0450,2025-01-05 00:00:00,Consultoría Global,Colombia,Soporte Técnico,Bolsa de 50h,2,600.0,1200.0,Draft
... (hasta 1000 registros)
```

## Glue - Athena
Al tener columnas como country y product_category, cuando AWS Glue lo rastree (con un Crawler), creará automáticamente una tabla en el Data Catalog. Luego, con Amazon Athena, tus alumnos podrán lanzar consultas SQL reales como SELECT country, SUM(total_amount) FROM ventas_odoo GROUP BY country; sin necesidad de tener un motor de base de datos encendido.

## Steps
Fase 1: Amazon S3 (Subir tu archivo al Data Lake)

Vamos a crear el "disco duro infinito" donde vivirán tus datos históricos.

    Ve a la consola de AWS y abre S3.

    Haz clic en Crear bucket.

    Ponle un nombre único, por ejemplo: datalake-odoo-ventas-tuapellido.

        Asegúrate de dejar marcada la opción "Bloquear todo el acceso público". ¡Son datos de ventas reales!

    Entra en el bucket y crea una Carpeta llamada ventas_crm.

        💡 Regla de oro del Data Lake: Si mañana descargas los datos de "Facturas" o "Empleados", irán en carpetas distintas. Athena asume que todo lo que hay dentro de una carpeta tiene las mismas columnas.

    Entra en la carpeta ventas_crm y haz clic en Cargar para subir tu archivo ventas_odoo_export.csv.

Fase 2: AWS Glue (Descubrir las columnas del CSV)

Tu archivo CSV tiene columnas específicas (como date_order, amount_total, partner_id, etc.). AWS Glue va a leer el archivo y a crear una tabla para nosotros automáticamente.

    Abre la consola de AWS Glue.

    En el menú izquierdo, ve a Databases y haz clic en Add database. Llámala odoo_analytics y créala.

    En el menú izquierdo, ve a Crawlers (Rastreadores) y haz clic en Create crawler.

    Name: Ponle rastreador-ventas-crm y dale a Next.

    Choose data sources: Haz clic en Add a data source. Selecciona S3 y dale a Browse. Selecciona la carpeta ventas_crm (no selecciones el archivo CSV directamente, selecciona la carpeta que lo contiene). Dale a Add y luego a Next.

    IAM Role: Haz clic en Create new IAM role. AWS le pondrá un nombre por defecto (ej. AWSGlueServiceRole-ventas). Esto le da la llave para leer tu S3. Dale a Next.

    Output configuration: En Target database, selecciona odoo_analytics.

    Revisa todo, dale a Create crawler y, cuando vuelva a la pantalla principal, selecciónalo y pulsa Run crawler.

        Espera 1 o 2 minutos. Cuando el "Status" vuelva a "Ready", te dirá que ha creado 1 tabla nueva.

Fase 3: Amazon Athena (Configurar el motor SQL Serverless)

¡Vamos a lanzar consultas! Pero antes, hay que evitar la trampa clásica de Athena.

    Abre la consola de Amazon Athena.

    🚨 Paso Obligatorio: Athena necesita un lugar temporal para guardar los resultados de las consultas.

        Ve a la pestaña Settings (Configuración) > Manage.

        En Query result location, escribe la ruta a tu bucket con una carpeta nueva. Por ejemplo: s3://datalake-odoo-ventas-tuapellido/resultados-athena/ y guárdalo.

    Vuelve a la pestaña Editor.

    A la izquierda, en el desplegable de Database, selecciona odoo_analytics.

    Verás que aparece tu tabla (se llamará ventas_crm). Haz clic en los tres puntitos a su derecha y selecciona Preview Table.

        ¡Magia! Verás los datos de tu CSV de Odoo en formato tabla de base de datos.

Fase 4: Analítica de Negocio (El Reporte Directivo)

Ahora que los datos están listos, vamos a responder a las preguntas de negocio.

Nota: AWS Glue lee las cabeceras de tu CSV. En mis ejemplos uso los nombres de columna estándar de Odoo (como amount_total o date_order). Si en tu CSV se llaman en español o diferente (ej. total, fecha_pedido), simplemente cambia el nombre en el código SQL.

Borra el código que haya en el Editor de Athena y prueba estas consultas de Nivel Experto:

1. El Top 5 de Mejores Clientes (Quién nos compra más)
SQL
```
SELECT 
    partner_id AS "Cliente", 
    COUNT(*) AS "Número de Pedidos", 
    SUM(CAST(amount_total AS DOUBLE)) AS "Volumen Total (€)"
FROM ventas_crm
WHERE state = 'sale' OR state = 'done' -- Solo pedidos confirmados
GROUP BY partner_id
ORDER BY "Volumen Total (€)" DESC
LIMIT 5;
```

2. Rendimiento de los Comerciales (Quién vende más)
SQL
```

SELECT 
    user_id AS "Comercial", 
    SUM(CAST(amount_total AS DOUBLE)) AS "Ventas Totales",
    AVG(CAST(amount_total AS DOUBLE)) AS "Ticket Medio"
FROM ventas_crm
GROUP BY user_id
ORDER BY "Ventas Totales" DESC;
```

3. Evolución de Ventas por Mes (Para ver la estacionalidad)
SQL
```
SELECT 
    SUBSTR(date_order, 1, 7) AS "Mes", 
    SUM(CAST(amount_total AS DOUBLE)) AS "Ingresos"
FROM ventas_crm
GROUP BY SUBSTR(date_order, 1, 7)
ORDER BY "Mes" ASC;
```
La reflexión final para tu práctica:

Cuando le des al botón de Run y veas que el resultado aparece en apenas 1 o 2 segundos, recuerda el concepto core del Módulo 6: Hemos hecho una agrupación matemática pesada sobre un histórico de ventas, y Odoo no se ha enterado en absoluto. Tu base de datos transaccional (RDS) sigue libre y rápida, mientras los directivos pueden jugar con los datos usando Athena pagando solo fracciones de céntimo por cada consulta. ¡El aislamiento perfecto!
