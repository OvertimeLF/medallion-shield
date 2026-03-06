"""
Envoltorios distribuidos (UDFs de PySpark)

Aquí creamos las User Defined Functions que Spark distribuirá en el clúster.
"""
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType
from core.crypto.engine import CryptoEngine

def get_hashing_udf(crypto_engine: CryptoEngine, salt: str = None):
    """
    Retorna una UDF de Spark pre-configurada para realizar Hashing con la PIK.
    """
    def _hash_func(val) -> str:
        if val is None:
            return None
        return crypto_engine.hash_sha256(str(val), salt)
        
    return udf(_hash_func, StringType())

def get_fpe_udf(crypto_engine: CryptoEngine, tweak: str):
    """
    Retorna una UDF de Spark pre-configurada para realizar FPE con su Tweak.
    """
    def _fpe_func(val) -> str:
        if val is None:
            return None
        return crypto_engine.pseudo_fpe(str(val), tweak)
        
    return udf(_fpe_func, StringType())
