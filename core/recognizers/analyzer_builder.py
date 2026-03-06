"""
Constructor del motor de descubrimiento y clasificación con Microsoft Presidio.
Permite registrar dinámicamente detectores personalizados (como el RUT) desde el YAML.

Esto evita el 'vibe coding' al inyectar reglas deterministas parametrizables
en una herramienta estándar de la industria (Presidio).
"""
import logging
from typing import List
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider

# Importamos el modelo desde el parser que ya hicimos, para tipado fuerte.
from core.config_parser import RecognizerConfig

logger = logging.getLogger(__name__)

class PresidioBuilder:
    @staticmethod
    def build_analyzer(config_recognizers: List[RecognizerConfig], language: str = "es") -> AnalyzerEngine:
        """
        Lee la lista de RecognizerConfig provenientes del archivo YAML y 
        construye un AnalyzerEngine inyectándole los detectores específicos de la empresa
        o región (Ej: RUT Chileno).
        """
        # 1. Cargamos el registry con los detectores por defecto globales (Email, Tarjetas, IPs)
        registry = RecognizerRegistry()
        registry.supported_languages = [language, "en"]
        registry.load_predefined_recognizers(languages=[language, "en"])
        
        # 2. Iteramos sobre los definidos en nuestro YAML (Domain Specific)
        custom_entities_added = 0
        
        # 3. Configuramos el motor NLP explícitamente para Español e Inglés
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [
                {"lang_code": "es", "model_name": "es_core_news_md"},
                {"lang_code": "en", "model_name": "en_core_web_lg"}
            ]
        }
        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()
        
        for rec in config_recognizers:
            if rec.type == "regex" and rec.pattern:
                # Crear el patrón de Microsoft Presidio
                presidio_pattern = Pattern(
                    name=f"{rec.name}_pattern",
                    regex=rec.pattern,
                    score=rec.score
                )
                
                # El supported_entity en Presidio es la "clase" resultante, por ejemplo 'CHILEAN_RUT'
                entity_name = rec.name.upper()
                
                # Crear el recognizer custom instanciando PatternRecognizer
                custom_recognizer = PatternRecognizer(
                    supported_entity=entity_name,
                    patterns=[presidio_pattern],
                    supported_language=language
                )
                
                # Inyectarlo al registry general
                registry.add_recognizer(custom_recognizer)
                custom_entities_added += 1
                logger.info(f"Detector inyectado en Presidio: {entity_name} (Threshold: {rec.score})")
                
        # 4. Retornar el motor final listo para ser llamado en el orquestador
        logger.info(f"Presidio Analyzer inicializado con {custom_entities_added} reglas personalizadas locales.")
        return AnalyzerEngine(registry=registry, nlp_engine=nlp_engine, supported_languages=[language, "en"])

if __name__ == "__main__":
    # Test local rápido a nivel de módulo
    # Simulamos el objeto validado por Pydantic
    mock_config = [
        RecognizerConfig(
            name="chilean_rut",
            type="regex",
            pattern=r"\b\d{1,8}-[\dkK]\b",
            score=0.9
        )
    ]
    
    analyzer = PresidioBuilder.build_analyzer(mock_config)
    texto_prueba = "El cliente Juan Perez tiene el RUT 12345678-5 y su email es juan@test.cl."
    
    # Probamos analizar contra nuestro detector inyectado (CHILEAN_RUT) y built-in (EMAIL_ADDRESS)
    resultados = analyzer.analyze(text=texto_prueba, language="es")
    
    print("\nText:", texto_prueba)
    print("\n--- Resultados del Analizador Presidio ---")
    for res in resultados:
        print(f"Tipo PII: {res.entity_type} | Confianza: {res.score} | Dato Encontrado: '{texto_prueba[res.start:res.end]}'")
