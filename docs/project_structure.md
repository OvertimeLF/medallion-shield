# Estructura del Proyecto y Archivos (Deep Dive)

El **Anonymizer Engine (Medallion Shield)** está construido bajo los principios de *Clean Architecture*. Esto significa que la lógica matemática del negocio está completamente aislada de la infraestructura que la ejecuta (PySpark).

A continuación, se detalla la estructura física del repositorio, definiendo el contenido y propósito de cada archivo.

```text
anonymizer-engine/
├── core/
│   ├── crypto/
│   │   ├── providers/
│   │   │   ├── .gitkeep
│   │   │   └── (Futuro) aws_kms.py, azure_kv.py
│   │   └── kms_base.py
│   ├── recognizers/
│   │   ├── .gitkeep
│   │   └── analyzer_builder.py
│   └── config_parser.py
│
├── engine/
│   ├── pipeline.py
│   └── udfs.py
│
├── config/
│   └── sample_config.yaml
│
├── docs/
│   ├── img/
│   │   └── banner.png
│   ├── architecture_guide.md
│   ├── configuration_manual.md
│   ├── presidio_chilean_manual.md
│   ├── project_structure.md (Este archivo)
│   └── usage_guide.md
│
├── tests/
│   └── test_config_parser.py
│
├── README.md
└── requirements.txt
```

---

## 1. Módulo `core/` (Lógica Pura de Aplicación)
Aquí vive el código en Python estándar. No tiene dependencias de Spark. Esto permite que el motor criptográfico pueda ser testeado rápidamente de forma local o incluso importado en otros frameworks (como Pandas o FastApi) en el futuro.

- **`crypto/kms_base.py`**: Es el **Contrato Abstracto**. Define una clase `KMSProvider` con métodos vacíos (`encrypt`, `decrypt`). Obliga a que cualquier integrador futuro que quiera conectar esto a AWS KMS o Azure Key Vault, respete las mismas firmas de funciones.
- **`crypto/providers/`**: Carpeta destinada a guardar las implementaciones concretas del contrato anterior (Ej: un script que use la SDK `boto3` para hablar con AWS).
- **`config_parser.py`**: El escudo validador de la aplicación. Usa la librería Pydantic para leer el YAML y asegurarse tempranamente ("Fail-Fast") de que los parámetros obligatorios existan y sean del tipo correcto antes de iniciar procesos pesados.
- **`recognizers/analyzer_builder.py`**: Contiene la clase constructora que inicializa `Microsoft Presidio`. Toma las reglas de expresiones regulares definidas en el YAML (ej. formato del RUT) e inyecta dinámicamente este conocimiento en el motor de Inteligencia Artificial (SpaCy/Presidio).

---

## 2. Módulo `engine/` (Capa de Infraestructura y Spark)
Aquí vive todo el código que sabe cómo distribuir el trabajo en clústeres de Big Data. Todo lo que está aquí importa y consume los módulos creados en `core/`.

- **`pipeline.py`**: El **Gran Orquestador**. Es el punto de entrada de la aplicación (`Main`). Su trabajo es:
  1. Recibir los parámetros de la terminal (`argparse`).
  2. Pedirle al `config_parser` que valide el YAML.
  3. Cargar la Llave KEK desde las variables de entorno del servidor.
  4. Leer el CSV o Parquet usando Spark.
  5. Ejecutar la transformación aplicando los UDFs.
  6. Guardar el archivo final.
- **`udfs.py`**: Declaración de Spark User Defined Functions. Toma las funciones matemáticas puras de criptografía y las envuelve en un decorador (`@udf`) permitiendo que Spark las envíe serializadas a la memoria RAM de los cientos de nodos _Workers_ disponibles en el clúster.

---

## 3. Módulo `config/` (Reglas de Negocio)
Separamos el CÓDIGO de las REGLAS. Un Ingeniero de Datos o Data Steward no debería necesitar saber programar en Python para decirle al motor qué columnas debe anonimizar.

- **`sample_config.yaml`**: Archivo de texto plano legible por humanos. Contiene 4 bloques: `engine` (configuraciones de chispa), `crypto` (qué algoritmos FPE/Hash usar), `recognizers` (expresiones regulares como RUT) y `rules` (reglas cruzadas: "aplica este recognizer a la columna X usando esta criptografía").

---

## 4. Directorio `docs/` (Documentación Técnica)
- **`architecture_guide.md`**: Explica el flujo matemático y criptográfico del Motor (FPE + Wrappers + Tweaks).
- **`configuration_manual.md`**: Referencia técnica de todos los parámetros aceptados dentro de un YAML.
- **`presidio_chilean_manual.md`**: Diccionario de expresiones regulares locales para Chile (RUT, PPU).
- **`usage_guide.md`**: Tutorial Step-by-Step para correr el software en tu máquina.
- **`project_structure.md`**: La guía que estás leyendo actualmente.

---

## 5. Directorio `tests/`
- **`test_config_parser.py`**: Pruebas unitarias hechas con `pytest`. Simula leer YAMLs malos (sin proveedor de KMS, o con reglas sin nombre) y afirma que el código arroje correctamente las excepciones `ValidationError` de Pydantic.
