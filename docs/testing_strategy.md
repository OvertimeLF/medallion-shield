# Estrategia de Testing y Validación (Fail-Fast)

En las arquitecturas de datos distribuidas (como PySpark), es crítico que la configuración se valide de manera estricta **antes** de iniciar el procesamiento. Si un archivo YAML tiene un error, preferimos que el sistema falle inmediatamente (Fail-Fast) en la máquina cliente, en lugar de fallar 30 minutos después en un clúster de Spark consumiendo recursos.

Para lograr esto, utilizamos **Pydantic** para definir esquemas rígidos y **Pytest** para verificar que estos esquemas reaccionan correctamente ante configuraciones erróneas.

## Herramientas Base (Fixtures y Helpers)

El archivo `tests/test_config_parser.py` cuenta con utilidades para simular la carga de configuraciones:

- `create_temp_yaml(tmp_path, data)`: Toma un diccionario de Python y lo guarda como un archivo temporal `.yaml`. `tmp_path` es una herramienta de Pytest que crea y destruye un directorio temporal automáticamente.
- `valid_config_data()`: Es un "Fixture" de Pytest que devuelve un diccionario que representa una configuración perfecta. Todos los tests parten de esta base para luego "romper" alguna parte específica.

## Escenarios de Prueba Implementados

### 1. El Caso Feliz (Happy Path)
- **Test:** `test_valid_config`
- **Descripción:** Toma el YAML perfecto, lo pasa por `AppConfig.from_yaml()` y verifica que se estructure correctamente. Confirma que los atributos básicos existen y las listas tienen el tamaño adecuado.

### 2. Validar Campos Obligatorios Missing
- **Test:** `test_missing_required_field`
- **Descripción:** Elimina intencionalmente el campo `key_uri` (que es obligatorio). Verifica que Pydantic lance un `ValidationError` indicando que el campo es requerido, evitando que la aplicación inicie sin las llaves criptográficas.

### 3. Validar Integridad Referencial de Criptografía
- **Test:** `test_invalid_rule_crypto_reference`
- **Descripción:** Altera una regla de anonimización para que solicite usar un método llamado `metodo_fantasma`. Pydantic verifica que este método no haya sido definido previamente en la sección de métodos criptográficos y lanza un error semántico.

### 4. Validar Integridad Referencial de Detectores
- **Test:** `test_invalid_rule_recognizer_reference`
- **Descripción:** Verifica que las reglas de anonimización no referencien un detector (Recognizer) que no existe. Si una regla pide buscar "detector_super_avanzado", el validador estallará si no fue configurado.

### 5. Lógica de Atributos Condicionales
- **Test:** `test_regex_recognizer_requires_pattern`
- **Descripción:** Si el usuario configura un detector basado en expresiones regulares (`type: "regex"`), Pydantic exige que exista el campo `pattern`. El test quita el patrón y confirma el rechazo del YAML.

### 6. Validación de Límites Numéricos
- **Test:** `test_invalid_score_range`
- **Descripción:** Un detector asigna un nivel de confianza (score) entre 0.0 y 1.0. El test inyecta un valor imposible (ej. `1.5`) y valida que Pydantic lo atrape y lance una advertencia de límites numéricos cruzados.
