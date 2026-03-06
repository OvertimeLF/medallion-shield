"""
Interfaz abstracta (KMSProvider)
"""
from abc import ABC, abstractmethod

class KMSProvider(ABC):
    """
    Contrato base para cualquier proveedor de gestión de llaves.
    Permite que el motor sea agnóstico a la nube.
    """
    
    @abstractmethod
    def unwrap_key(self, wrapped_key_blob: str) -> bytes:
        """
        Toma el blob encriptado (PIK) y lo devuelve 
        como bytes planos usando la llave maestra (KEK).
        """
        pass

    @abstractmethod
    def get_status(self) -> bool:
        """Verifica si hay conexión con el servicio de llaves."""
        pass
