# Configuración de Casos Comunes en Chile (Microsoft Presidio)

Microsoft Presidio trae por default detectores globales en inglés y español (`EMAIL_ADDRESS`, `PHONE_NUMBER`, `CREDIT_CARD`, `CRYPTO`, etc). Sin embargo, para usarlo a nivel empresarial debemos adaptarlo a particularidades locales inyectando patrones (Regex) al motor desde nuestro archivo `config.yaml`.

Este manual ilustra cómo añadir las configuraciones para las entidades chilenas más comues.

## 1. RUT Chileno (Rol Único Tributario)

El RUT puede aparecer en tablas en varios formatos: con puntos ("12.345.678-5"), sin puntos ("12345678-5"), o incluso sin guion. El YAML acepta expresiones regulares ricas.

### Ejemplos en YAML:
**RUT Estándar sin puntos (recomendado para IDs en bases de datos):**
```yaml
recognizers:
  - name: "cl_rut_db"
    type: "regex"
    pattern: "^\\d{1,8}-[\\dkK]$"
    score: 0.95  # Score alto, la estructura es muy distintiva
```

**RUT en textos libres (Ej: Logs de Call Center, encuestas):**
```yaml
recognizers:
  - name: "cl_rut_free_text"
    type: "regex"
    pattern: "\\b\\d{1,2}\\.?\\d{3}\\.?\\d{3}-?[\\dkK]\\b"
    score: 0.85
```

---

## 2. Placas Patentes Chilenas (Vehículos)

En casos de aseguradoras o de flotas de vehículos, una patente PPU chilena (Placa Patente Única) es PII directo. Los formatos modernos son `AAAA-11` y los antiguos son `AA-1111`.

### Ejemplo en YAML:
```yaml
recognizers:
  - name: "cl_ppu_vehiculo"
    type: "regex"
    pattern: "\\b([A-Z]{4}-?\\d{2}|[A-Z]{2}-?\\d{4})\\b"
    score: 0.90
```

---

## 3. Cuentas Bancarias y Tarjetas (Locales)

Aunque Presidio detecta tarjetas de crédito multinacionales por defecto empleando el algoritmo de Luhn, si queremos ofuscar explícitamente "Cuenta RUT" del BancoEstado que es el RUT sin guión:

### Ejemplo en YAML:
```yaml
recognizers:
  - name: "cl_cuenta_rut"
    type: "regex"
    pattern: "\\b\\d{7,8}\\d[\\dkK]\\b"
    score: 0.75 # Score más bajo, podría confundirse con números de teléfono
```

---

## ¿Cómo se procesa en el Motor? (Prevención de Vibe Coding)

1. En tiempo de **Startup** del orquestador de Spark, el motor lee esta lista del YAML (valida que todo esté correcto mediante `Pydantic`).
2. La clase `PresidioBuilder` (ubicada en `core/recognizers/analyzer_builder.py`) inicializa la JVM o Driver convirtiendo cada bloque del YAML anterior en objetos `PatternRecognizer` reales de la librería Microsoft Presidio.
3. Esto inyecta soporte "Nativo" y distribuido al clúster, pero te permite mantener la infraestructura "Clean" mediante control de repositorios (Git) en archivos YAML puros, sin tocar nunca los `.py` de lógica central.
