import pytest
import yaml
from pydantic import ValidationError
from core.config_parser import AppConfig

def create_temp_yaml(tmp_path, data):
    file_path = tmp_path / "test_config.yaml"
    with open(file_path, "w") as f:
        yaml.dump(data, f)
    return str(file_path)

@pytest.fixture
def valid_config_data():
    return {
        "engine": {
            "mode": "local",
            "log_level": "DEBUG"
        },
        "crypto": {
            "kms": {
                "provider": "local",
                "key_uri": "test-key"
            },
            "methods": [
                {
                    "name": "hash_method",
                    "algorithm": "SHA-256"
                },
                {
                    "name": "fpe_method",
                    "algorithm": "FF1",
                    "default_tweak": "tweak1"
                }
            ]
        },
        "recognizers": [
            {
                "name": "my_rut",
                "type": "regex",
                "pattern": "^\\d{1,8}-[\\dkK]$",
                "score": 0.9
            }
        ],
        "rules": [
            {
                "column": "rut_cliente",
                "recognizer": "my_rut",
                "anonymization": "fpe_method",
                "domain_tweak": "domain_a"
            },
            {
                "column": "email",
                "recognizer": "email",  # built-in
                "anonymization": "hash_method"
            }
        ]
    }

def test_valid_config(tmp_path, valid_config_data):
    yaml_path = create_temp_yaml(tmp_path, valid_config_data)
    config = AppConfig.from_yaml(yaml_path)
    assert config.engine.mode == "local"
    assert config.crypto.kms.provider == "local"
    assert len(config.rules) == 2

def test_missing_required_field(tmp_path, valid_config_data):
    # Romper el config quitando key_uri
    del valid_config_data["crypto"]["kms"]["key_uri"]
    yaml_path = create_temp_yaml(tmp_path, valid_config_data)
    
    with pytest.raises(ValidationError) as exc_info:
        AppConfig.from_yaml(yaml_path)
    
    assert "key_uri" in str(exc_info.value)
    assert "Field required" in str(exc_info.value)

def test_invalid_rule_crypto_reference(tmp_path, valid_config_data):
    # La regla hace referencia a un metodo cryptografico que no existe
    valid_config_data["rules"][0]["anonymization"] = "metodo_fantasma"
    yaml_path = create_temp_yaml(tmp_path, valid_config_data)
    
    with pytest.raises(ValidationError) as exc_info:
        AppConfig.from_yaml(yaml_path)
    
    assert "no definido en crypto.methods" in str(exc_info.value)

def test_invalid_rule_recognizer_reference(tmp_path, valid_config_data):
    valid_config_data["rules"][0]["recognizer"] = "recognizer_fantasma"
    yaml_path = create_temp_yaml(tmp_path, valid_config_data)
    
    with pytest.raises(ValidationError) as exc_info:
        AppConfig.from_yaml(yaml_path)
    
    assert "Recognizer 'recognizer_fantasma' no definido" in str(exc_info.value)

def test_regex_recognizer_requires_pattern(tmp_path, valid_config_data):
    # Quitar el pattern de un recognizer tipo regex
    del valid_config_data["recognizers"][0]["pattern"]
    yaml_path = create_temp_yaml(tmp_path, valid_config_data)
    
    with pytest.raises(ValidationError) as exc_info:
        AppConfig.from_yaml(yaml_path)
    
    assert "Regex pattern is required" in str(exc_info.value)

def test_invalid_score_range(tmp_path, valid_config_data):
    valid_config_data["recognizers"][0]["score"] = 1.5
    yaml_path = create_temp_yaml(tmp_path, valid_config_data)
    
    with pytest.raises(ValidationError) as exc_info:
        AppConfig.from_yaml(yaml_path)
    
    assert "less than or equal to 1" in str(exc_info.value)
