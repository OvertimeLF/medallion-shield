from setuptools import setup, find_packages

setup(
    name="medallion-shield",
    version="0.1.0",
    description="Motor de Anonimización de Datos para Arquitecturas Medallion.",
    author="Tu Nombre / Organización",
    packages=find_packages(include=["core", "core.*", "engine", "engine.*"]),
    install_requires=[
        "pyspark>=3.5.0",
        "pyyaml>=6.0",
        "pydantic>=2.0.0",
        "presidio-analyzer>=2.2.33",
        "spacy>=3.7.2",
    ],
    extras_require={
        "enterprise": [
            "azure-identity>=1.15.0",
            "azure-keyvault-secrets>=4.7.0",
            # "pyff3>=1.0.1" # A futuro en Hito 2
        ]
    },
    python_requires=">=3.9",
)
