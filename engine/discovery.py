import sys
import logging
import argparse
import os
import yaml

# Add root project path to Python's sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pyspark.sql import SparkSession
from core.config_parser import AppConfig
from core.recognizers.analyzer_builder import PresidioBuilder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def generate_recommended_config(detected_columns: dict, base_config: AppConfig, output_yaml_path: str):
    """
    Toma los resultados heurísticos de Presidio y escribe un yaml sugerido.
    """
    
    # Template base structure compatible with AppConfig
    proposed_config = {
        "engine": {
            "name": "spark",
            "version": "3.5"
        },
        "crypto": {
            "kms": {
                "provider": base_config.crypto.kms.provider.value,
                "key_uri": base_config.crypto.kms.key_uri
            },
            "methods": [{"name": m.name, "algorithm": m.algorithm} for m in base_config.crypto.methods]
        },
        "recognizers": [{"name": r.name, "type": r.type, "pattern": r.pattern, "score": r.score} for r in base_config.recognizers],
        "rules": []
    }
    
    logger.info("=== Resultados del Escaneo Presidio ===")
    for column, entities in detected_columns.items():
        if not entities:
            continue
            
        # Get the most common entity detected in this column
        best_entity = max(entities.items(), key=lambda x: x[1])[0]
        
        # Decide the strategy. Numeric IDs (like RUTs) -> FPE usually. Other PII -> HASH or FPE
        strategy = "fpe_preservation" if ("RUT" in best_entity or "ID" in best_entity) else "hash_sha256"
        
        logger.info(f"Columna Mapeada Automáticamente -> '{column}': Detectado {best_entity} (Se recomienda {strategy})")
        
        proposed_config["rules"].append({
            "column": column,
            "recognizer": best_entity.lower(), # Attempt to map Presidio entity to recognizer config rule
            "anonymization": strategy,
            "domain_tweak": f"auto_{column.lower()}_tweak" if strategy == "fpe_preservation" else None
        })

    # Avoid generating rules with None values dynamically
    for rule in proposed_config["rules"]:
        if rule["domain_tweak"] is None:
            del rule["domain_tweak"]

    with open(output_yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(proposed_config, f, sort_keys=False, default_flow_style=False)
        
    logger.info(f"\n✅ Configuración auto-generada guardada en: {output_yaml_path}")
    logger.info("Revisa el archivo y ajustalo manualemte antes de correr pipeline.py")


def run_discovery(config_path: str, input_path: str, sample_size: int, output_yaml: str, delimiter: str = ",", quote: str = '"', input_format: str = "csv"):
    logger.info("⚡ Iniciando Módulo Discovery (Microsoft Presidio) Scanner ⚡")
    
    # 1. Cargar la configuración base (Principalmente necesitamos los custom Recognizers aquí, ej RUT Chileno)
    logger.info(f"Cargando detectores personalizados desde {config_path}...")
    try:
        config = AppConfig.from_yaml(config_path)
    except Exception as e:
        logger.error(f"Error cargando config base: {e}")
        sys.exit(1)

    # 2. Inicializar PySpark
    spark = SparkSession.builder.master("local[*]").appName("AnonymizerDiscovery").getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")

    # 3. Leer Tabla Cruda
    logger.info(f"Leyendo entrada {input_path}...")
    if input_format.lower() == "csv":
        df = spark.read.option("delimiter", delimiter).option("quote", quote).csv(input_path, header=True, inferSchema=True)
    elif input_format.lower() == "parquet":
        df = spark.read.parquet(input_path)
    else:
        logger.error("Formato no soportado en Discovery")
        sys.exit(1)

    columns = df.columns
    logger.info(f"Población detectada: {len(columns)} columnas evaluables.")
    
    # 4. Extraer un Sample Pequeño y subir a Driver RAM (Pandas Pandas Pandas)
    # Por rapidez del discovery MVP, lo haremos centralizado en el Driver.
    logger.info(f"Extrayendo sample de {sample_size} filas...")
    sample_df = df.limit(sample_size).toPandas()
    
    if sample_df.empty:
        logger.error("La tabla está vacía.")
        sys.exit(1)

    # 5. Inicializar Analizador Presidio con reglas locales Inyectadas
    analyzer = PresidioBuilder.build_analyzer(config.recognizers, language="es")
    
    # 6. Escanear
    detected_entities_per_column = {col: {} for col in columns}
    
    logger.info("Iniciando escaneo heurístico y regex...")
    for col in columns:
        valid_items = sample_df[col].dropna().astype(str).tolist()
        
        for text_item in valid_items:
            # Skip very empty or meaningless items to save CPU
            if len(text_item) < 3: 
                continue
                
            results = analyzer.analyze(text=text_item, language="es")
            
            for result in results:
                # Omit artifacts with low confidence
                if result.score >= 0.5:
                    entity_type = result.entity_type
                    detected_entities_per_column[col][entity_type] = detected_entities_per_column[col].get(entity_type, 0) + 1
                    
    # Filtrar columnas donde no detectamos NADA relevante
    meaningful_columns = {k: v for k, v in detected_entities_per_column.items() if len(v) > 0}
    
    if not meaningful_columns:
        logger.warning("\nNo se detectaron entidades PII con la configuración y muestra actual.")
        sys.exit(0)

    # 7. Generar Yaml
    generate_recommended_config(meaningful_columns, config, output_yaml)
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Medallion Shield Discovery Mode")
    parser.add_argument("--config", type=str, default="config/sample_config.yaml", help="Yaml base para inyectar recognizers custom a Presidio.")
    parser.add_argument("--input", type=str, required=True, help="Dataset csv o parquet objetivo a escanear.")
    parser.add_argument("--sample", type=int, default=1000, help="N° Récords aleatorios/Top para escanear.")
    parser.add_argument("--output_yaml", type=str, default="config/proposed_rules.yaml", help="Ruta de guardado para la recomendación.")
    parser.add_argument("--format", type=str, default="csv", choices=["csv", "parquet"])
    parser.add_argument("--delimiter", type=str, default=",")
    parser.add_argument("--quote", type=str, default='"')
    
    args = parser.parse_args()
    
    run_discovery(args.config, args.input, args.sample, args.output_yaml, args.delimiter, args.quote, args.format)
