# Manual de Configuración YAML

El archivo YAML interactúa directamente con los modelos de Pydantic de la carpeta `core/config_parser.py`. Si el YAML tiene un error tipográfico, la validación "Fail-Fast" detendrá el proceso de inmediato.

## Estructura Base

Un YAML de configuración se divide en 4 bloques: `engine`, `crypto`, `recognizers` y `rules`.

### 1. Engine
Define el modo de ejecución del orquestador. Permitidos: `spark` o `local`.

```yaml
engine:
  mode: "spark"
  log_level: "INFO"
```

### 2. Crypto
Configura con qué proveedor de llaves te vas a conectar y qué métodos estarán disponibles en este pipeline.

```yaml
crypto:
  kms:
    provider: "local"       # Proveedores permitidos: "local", "azure", "aws"
    key_uri: "local-dev-key" # URI para obtener la KEK.
  methods:
    - name: "mi_fpe"        # Nombre de libre elección para referenciar luego en 'rules'
      algorithm: "FF1"      # Opciones: "FF1", "FF3", "SHA-256"
      default_tweak: "global_tweak" # Opcional: Tweak base
```

### 3. Recognizers
Registra "Detectores" para localizar datos sensibles. Pueden ser basados en Expresiones Regulares o usar modelos del motor Inteligente (Microsoft Presidio).

```yaml
recognizers:
  - name: "chilean_rut"
    type: "regex"                      # Tipos: "regex" o "presidio_built_in"
    pattern: "^\\d{1,8}-[\\dkK]$"      # Obligatorio si el type es regex
    score: 0.8                         # Umbral de confianza (0.0 a 1.0)
```

### 4. Rules
Aquí es donde cruzas columnas, detectores y criptografía. Las reglas dicen: "Toma esta columna, analízala con este detector, y ofúscala con este método".

```yaml
rules:
  - column: "email"
    recognizer: "email"               # Debe existir en recognizers o ser un built-in
    anonymization: "mi_fpe"           # Debe existir en crypto -> methods
    domain_tweak: "exportacion_2026"  # Tweak específico para variar el output
```
