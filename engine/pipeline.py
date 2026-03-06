"""
Orquestador principal (The Runner)

Este orquestador ilustra el End-to-End del sistema:
1. Inyecta dependencias (Carga configuración y KMS local)
2. Inicializa Spark y carga datos de prueba.
3. Aplica las UDFs basadas en la configuración YAML.
"""
import sys
import logging
import argparse
import os

# Add root project path to Python's sys.path so 'core' and 'engine' modules are found when running as script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

from core.config_parser import AppConfig
from core.crypto.providers.local_kms import LocalKMSProvider
from core.crypto.engine import CryptoEngine
from engine.udfs import get_hashing_udf, get_fpe_udf

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def create_mock_dataframe(spark: SparkSession):
    """Crea un DataFrame emulando la tabla 'Gold' o 'Raw'"""
    schema = StructType([
        StructField("id", IntegerType(), True),
        StructField("rut_cliente", StringType(), True),
        StructField("email", StringType(), True),
        StructField("nombre", StringType(), True)
    ])
    
    data = [
        (1, "12345678-5", "luis.felipe@example.com", "Luis"),
        (2, "9876543-K", "maria.perez@example.com", "Maria"),
        (3, "11223344-7", "juan.soto@test.cl", "Juan")
    ]
    return spark.createDataFrame(data, schema)

def run_pipeline(config_path: str, dummy_kek: bytes, input_path: str = None, input_format: str = "csv", output_path: str = None, delimiter: str = ",", quote: str = '"'):
    logger.info("⚡ Iniciando Medallion Shield Anonymizer Engine ⚡")
    
    # 1. PARSEAR Y VALIDAR (Fail-Fast)
    logger.info(f"Cargando configuración desde {config_path}...")
    try:
        config = AppConfig.from_yaml(config_path)
    except Exception as e:
        logger.error(f"Error de validación en configuración: {e}")
        sys.exit(1)
        
    # 2. INYECTAR KMS (Inversión de Dependencias)
    logger.info(f"Conectando al KMS Provider: {config.crypto.kms.provider.value.upper()}")
    provider = LocalKMSProvider(dummy_kek)
    
    if not provider.get_status():
        logger.error("KMS Provider inaccesible.")
        sys.exit(1)
        
    # Simulamos un blob cifrado (la PIK cifrada con la KEK)
    # En la vida real, sacarías esto de tu Vault/KMS (ej: `wrapped_key_blob` = provider.get_wrapped_pik() )
    # Para el MVP, creamos un blob en el aire con la criptografía de Fernet:
    real_pik = b"MySuperSecretCompanyWidePIK_2026"
    wrapped_blob = provider.fernet.encrypt(real_pik).decode('utf-8')
    
    logger.info("Desempaquetando la llave de datos (Unwrapping PIK)...")
    decrypted_pik = provider.unwrap_key(wrapped_blob)
    
    # 3. INICIALIZAR EL MOTOR CRIPTOGRÁFICO
    crypto_engine = CryptoEngine(decrypted_pik)
    logger.info("✅ Motor Criptográfico inicializado correctamente (Key Injected).")
    
    # 4. INICIAR SPARK Y DATOS
    logger.info("Iniciando sesión de Spark...")
    spark = SparkSession.builder.master("local[*]").appName("AnonymizerEngineLocal").getOrCreate()
    # Cambiar log level por stdout limpio
    spark.sparkContext.setLogLevel("ERROR")
    
    if input_path:
        logger.info(f"Leyendo archivo de entrada: {input_path} (Formato: {input_format})")
        if input_format.lower() == "csv":
            df = spark.read.option("delimiter", delimiter).option("quote", quote).csv(input_path, header=True, inferSchema=True)
        elif input_format.lower() == "parquet":
            df = spark.read.parquet(input_path)
        else:
            logger.error(f"Formato no soportado: {input_format}")
            sys.exit(1)
    else:
        logger.info("No se proveyó archivo de entrada. Cargando Mock DataFrame para pruebas.")
        df = create_mock_dataframe(spark)

    logger.info("=== DataFrame Original ===")
    df.show()
    
    # 5. APLICAR REGLAS Y TRANSFORMACIONES
    logger.info("Aplicando transformaciones criptográficas distribuidas...")
    
    transformed_df = df
    for rule in config.rules:
        col_name = rule.column
        # Para el MVP, simplificamos asumiendo que el yaml dice si es Hashing o FPE
        # en base al sufijo o a un cruce con crypto.methods, aquí simplemente checamos el nombre.
        if "fpe" in rule.anonymization.lower():
            tweak = rule.domain_tweak or "global_default"
            logger.info(f" -> Columna: {col_name} | Método: Pseudo-FPE | Tweak: {tweak}")
            fpe_udf = get_fpe_udf(crypto_engine, tweak)
            transformed_df = transformed_df.withColumn(col_name, fpe_udf(transformed_df[col_name]))
            
        elif "hash" in rule.anonymization.lower():
            logger.info(f" -> Columna: {col_name} | Método: SHA-256 HMAC (PIK)")
            hash_udf = get_hashing_udf(crypto_engine)
            transformed_df = transformed_df.withColumn(col_name, hash_udf(transformed_df[col_name]))
            
    logger.info("=== DataFrame Anonimizado (Medallion Shield Protected) ===")
    transformed_df.show(truncate=False)

    if output_path:
        logger.info(f"Guardando resultados en: {output_path} (Formato: {input_format})")
        if input_format.lower() == "csv":
            transformed_df.write.mode("overwrite").csv(output_path, header=True)
        else:
            transformed_df.write.mode("overwrite").parquet(output_path)
        logger.info("✅ Exportación finalizada.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Medallion Shield Anonymizer Engine")
    parser.add_argument(
        "--config", 
        type=str, 
        default="config/sample_config.yaml",
        help="Ruta al archivo de configuración YAML (ej: config/sample_config.yaml)"
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Ruta al archivo CSV o Parquet de entrada."
    )
    parser.add_argument(
        "--format",
        type=str,
        default="csv",
        choices=["csv", "parquet"],
        help="Formato del archivo de entrada y salida (csv o parquet)."
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Directorio donde guardar el resultado. Si se omite, solo se muestra en pantalla."
    )
    parser.add_argument(
        "--delimiter",
        type=str,
        default=",",
        help="Delimitador usado en el CSV."
    )
    parser.add_argument(
        "--quote",
        type=str,
        default='"',
        help="Carácter de encapsulamiento usado en el CSV (Ej: comillas)."
    )
    
    args = parser.parse_args()

    # En un entorno real, la KEK jamás debería estar en código.
    # Aquí simulamos leerla desde una variable de entorno inyectada por el orquestador (Airflow/Databricks).
    raw_kek = os.environ.get("MEDALLION_MASTER_KEY", "rY7b4Ww3F2yA-t9gN6_xLk8ZpQq5_vB1cJmXDeGzNRo=")
    kek_bytes = raw_kek.encode('utf-8')
    
    run_pipeline(args.config, kek_bytes, args.input, args.format, args.output, args.delimiter, args.quote)
