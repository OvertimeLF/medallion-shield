![Medallion Shield Banner](docs/img/banner.png)

# Anonymizer Engine (Medallion Shield)

Documentación técnica y guía de inicio.

## Documentación del Proyecto

El proyecto sigue una arquitectura limpia (*Clean Architecture*). Para entender a fondo la separación de responsabilidades y la función de cada archivo, por favor revisa la **[Guía de Estructura del Proyecto](docs/project_structure.md)**.

- `core/`: Lógica matemática pura de Python (Agnóstica de Spark).
- `engine/`: Capa de Infraestructura y orquestación distribuida (PySpark).
- `config/`: Archivos YAML con reglas de negocio.
- `docs/`: Manuales de uso y guías de arquitectura (incluye guía de despliegue local).
- `tests/`: Batería de pruebas unitarias.
