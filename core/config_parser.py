"""
Validación de YAML con Pydantic puro para el motor de anonimización.
Asegura que el pipeline no falle en mitad de la ejecución (Fail-Fast).
"""
import yaml
from enum import Enum
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class EngineMode(str, Enum):
    SPARK = "spark"
    LOCAL = "local"


class EngineConfig(BaseModel):
    mode: EngineMode = EngineMode.SPARK
    log_level: str = "INFO"


class KMSProviderType(str, Enum):
    LOCAL = "local"
    AZURE = "azure"
    AWS = "aws"


class KMSConfig(BaseModel):
    provider: KMSProviderType
    key_uri: str = Field(..., description="URI de la Master Key (KEK)")


class CryptoMethodConfig(BaseModel):
    name: str = Field(..., description="Nombre referencial del método criptográfico")
    algorithm: Literal["SHA-256", "FF1", "FF3"] = Field(..., description="Algoritmo soportado")
    default_tweak: Optional[str] = Field(None, description="Tweak base para FPE")


class CryptoConfig(BaseModel):
    kms: KMSConfig
    methods: List[CryptoMethodConfig]


class RecognizerConfig(BaseModel):
    name: str
    type: Literal["regex", "presidio_built_in"] = "regex"
    pattern: Optional[str] = None
    score: float = Field(0.8, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_regex_pattern(self):
        if self.type == "regex" and not self.pattern:
            raise ValueError("Regex pattern is required for regex recognizers")
        return self


class RuleConfig(BaseModel):
    column: str
    recognizer: str = Field(..., description="Referencia a un recognizer configurado o built-in")
    anonymization: str = Field(..., description="Referencia a un método criptográfico configurado")
    domain_tweak: Optional[str] = Field(None, description="Tweak específico del dominio para variar el token (FPE)")


class AppConfig(BaseModel):
    engine: EngineConfig
    crypto: CryptoConfig
    recognizers: List[RecognizerConfig]
    rules: List[RuleConfig]

    @field_validator("rules")
    def validate_rule_references(cls, v, info):
        """Valida que los recognizers y anonymization referenciados en las reglas existan."""
        data = info.data
        if not data.get("crypto") or not data.get("recognizers"):
            return v
        
        valid_crypto_methods = {m.name for m in data["crypto"].methods}
        valid_recognizers = {r.name for r in data["recognizers"]}
        # Agregamos built-ins de presidio que asumimos válidos (ej: email)
        valid_recognizers.add("email") 
        valid_recognizers.add("phone")

        for rule in v:
            if rule.anonymization not in valid_crypto_methods:
                raise ValueError(f"Método criptográfico '{rule.anonymization}' no definido en crypto.methods")
            if rule.recognizer not in valid_recognizers:
                raise ValueError(f"Recognizer '{rule.recognizer}' no definido")
        return v

    @classmethod
    def from_yaml(cls, path: str) -> "AppConfig":
        """Carga y valida la configuración desde un archivo YAML."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)


if __name__ == "__main__":
    # Test rápido de fail-fast
    import sys
    try:
        config = AppConfig.from_yaml("config/sample_config.yaml")
        print("✅ Configuración válida:")
        print(config.model_dump_json(indent=2))
    except Exception as e:
        print("❌ Error de configuración:")
        print(e)
        sys.exit(1)
