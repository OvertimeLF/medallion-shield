# Estrategias Avanzadas de Anonimización para Tablas EAV (Entity-Attribute-Value)

Las tablas EAV, donde la columna D (Valor) depende semánticamente de la columna C (Atributo), representan un caso borde complejo para los motores PII tradicionales.

Dado nuestro ecosistema actual basado en PySpark y el Medallion Shield, aquí te detallo tres estrategias arquitectónicas sin modificar código actual.

## 1. El Enfoque del Pivotaje Distribuido (El más recomendado en Medallion Architecture)

En lugar de anonimizar la tabla cruda (Bronze), la protección se aplica en la zona Silver.
* **Proceso**: Usar PySpark para hacer un `pivot` de la tabla transformando las filas en columnas relacionales (`df.groupBy("GORSDAV_PK_PARENTTAB").pivot("GORSDAV_ATTR_NAME").agg(...)`).
* **Anonimización**: Con la tabla aplanada, el motor Medallion Shield puede aplicar reglas de Yaml específicas exactas. Por ejemplo, decirle firmemente que FPE aplica a `rut_cliente` y Ocultamiento Facial a `estado_civil`.
* **Desventajas**: Computacionalmente costoso en el clúster si los atributos varían demasiado (Sparsity Data).

## 2. Dynamic Routing UDF (UDF de Doble Parámetro)

Spark permite pasar múltiples columnas a una UDF.
* **Proceso**: Reescribir la UDF para que acepte dos columnas: el valor y el nombre de su atributo.
  `transformed = df.withColumn("Value", get_dynamic_udf("AttributeName", "Value"))`
* **Anonimización**: La UDF internamente carga un diccionario (proveniente del Yaml) y utiliza sentencias lógicas. Si el "Atributo" recibido es `SUELDO`, no le hace FPE, le hace Rango (Bucketization). Si el "Atributo" es `RUT` aplica FPE.
* **Desventajas**: Spark no puede optimizar bien el plan de ejecución de UDFs con saltos lógicos internos tan fuertes (if/else), causando cuellos de botella ("Serialization Overheads").

## 3. Reconocimiento de Contexto en Flight (Microsoft Presidio)

Esta alternativa recae puramente en la NLP en lugar del esquema.
* **Proceso**: La UDF o un Microservicio pasa cada fila a Microsoft Presidio en tiempo de ejecución.
* **Anonimización**: Sin importar qué decía la tabla EAV, Presidio lee cada celda como string, dice "Ah, este valor es un RUT -> Aplico FPE", o lee el siguiente valor y dice "Ah, esto es texto de Diagnóstico Médico -> Aplico Redaction".
* **Desventajas**: Ejecutar inferencias NLP contra millones de registros durante el ETL de Data Engineering (Batching) no es viable. Tomaría horas. Solo sirve para sistemas MLOps en Streaming donde los datos entran de a gotas.
