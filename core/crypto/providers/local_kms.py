"""
Implementación Local del KMS Provider para desarrollo y testing.
"""
from core.crypto.kms_base import KMSProvider
from cryptography.fernet import Fernet

class LocalKMSProvider(KMSProvider):
    def __init__(self, master_key: bytes):
        """
        Inicializa el provider local con una llave maestra (KEK) en texto plano (o base64).
        """
        self.fernet = Fernet(master_key)

    def unwrap_key(self, wrapped_key_blob: str) -> bytes:
        """
        En modo local, desencriptamos el blob usando la llave maestra local.
        """
        return self.fernet.decrypt(wrapped_key_blob.encode())

    def get_status(self) -> bool:
        """
        En modo local siempre retornamos True si pudimos inicializar la clase.
        """
        return True
