# Estrategias de Exportación a Sistemas Externos (SFTP)

Cuando los datos procesados en el Data Lake/Lakehouse necesitan ser consumidos por sistemas externos o heredados (legacy) a través de mecanismos como SFTP, la arquitectura de anonimización debe adaptarse para equilibrar la seguridad con la compatibilidad.

El escenario planteado: **Data Lake -> Exportación CSV a SFTP -> Sistema Externo -> Front-End.**

Aquí detallamos los dos patrones principales para abordar este desafío:

## 1. Des-anonimización en el Borde (El Patrón Exportador / Reverse ETL)

Este es el enfoque más pragmático y común cuando el sistema externo no tiene la capacidad técnica de integrar nuestra lógica de descifrado o cuando pertenece a un tercero.

*   **El Flujo:**
    1.  El Data Lake contiene los datos anonimizados en la capa `Gold`.
    2.  Se programa un proceso orquestado (un "Job de Salida" en Spark o un DAG en Airflow).
    3.  Este job lee la tabla `Gold`, invoca nuestro motor de descifrado (ej. revirtiendo el FPE) **en la memoria del clúster**.
    4.  El job escribe el archivo CSV con los datos en texto plano directamente en la ruta del servidor SFTP.
    5.  El sistema externo recoge el CSV plano y lo procesa normalmente.

*   **Ventajas:** Es transparente para el sistema externo. Cero fricción de integración.
*   **Desventajas y Riesgos:** El archivo CSV que reside físicamente en el servidor SFTP contiene PII (Información de Identificación Personal) real. 
*   **Mitigación Obligatoria:** Si eliges este camino, el servidor SFTP se convierte en tu eslabón más débil. Debe estar detrás de una VPN/VPC estricta, usar encriptación en reposo, tener rotación de credenciales, y los archivos deben eliminarse automáticamente después de ser leídos por el sistema externo.

## 2. Delegación Criptográfica (El Patrón Zero-Trust)

En este escenario, mantienes la postura de seguridad máxima: nunca escribes datos sensibles en un archivo plano en un servidor intermedio.

*   **El Flujo:**
    1.  El job de salida toma la tabla `Gold` (que ya está anonimizada) y simplemente la exporta al SFTP tal cual. **El CSV en el SFTP contiene datos falsos/encriptados**.
    2.  El sistema externo toma el CSV y lo carga en su propia base de datos (seguirá encriptado).
    3.  El Front-End de ese sistema (o su Backend API) debe integrar nuestra librería de descifrado y estar autorizado para consumir la Master Key (ej. desde Azure Key Vault).
    4.  Cuando el Front-End necesita mostrar el dato al usuario final, invoca la función de descifrado al vuelo.

*   **Ventajas:** El servidor SFTP es completamente inofensivo si es vulnerado. Cumples con las normativas más estrictas de Zero-Trust.
*   **Desventajas:** Requiere un nivel de acoplamiento alto con el sistema externo. Tienes que entregarles la librería y gobernar sus accesos al KMS (Key Management Service). Si el sistema externo no puede ejecutar código personalizado o Python/Java, este patrón es inviable.

---

### Conclusión para tu Arquitectura

Si el "otro sistema" es una caja negra (ej. un software empaquetado comprado a un proveedor que solo lee CSVs por SFTP y pobla su base de datos), **tendrás que usar la Estrategia 1 (Des-anonimizar en el Borde)**. 

En ese caso tu proceso de *Reverse ETL* asume el rol de "Des-anonimizador Autorizado", transformando la data en memoria justo milisegundos antes de inyectarla por el túnel SFTP. El esfuerzo de seguridad debe trasladarse entonces a auditar quién puede acceder a ese servidor SFTP.
