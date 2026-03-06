"""
Lógica criptográfica central: Hashing y FPE con Tweaks
"""
import hashlib
from typing import Optional

# NOTA: Para un FPE real certificado (FF1/FF3) en Python, típicamente se usa la librería `ff3` o bindings a C.
# Para este MVP, implementaremos un pseudo-FPE ilustrativo o usaremos hashlib para el hash.
# En un entorno de producción, aquí integraríamos pyff3.

class CryptoEngine:
    def __init__(self, decrypted_pik: bytes):
        """
        Inicializa el motor criptográfico con la PIK (Protected Input Key) ya en texto plano.
        """
        self.pik = decrypted_pik

    def hash_sha256(self, data: str, salt: Optional[str] = None) -> str:
        """
        Aplica un hash SHA-256 determinista usando la PIK como HMAC secreto o concatenación.
        El salt opcional actúa como Tweak para el hashing.
        """
        if not data:
            return data
            
        base_string = data.encode('utf-8') + self.pik
        if salt:
            base_string += salt.encode('utf-8')
            
        return hashlib.sha256(base_string).hexdigest()

    def pseudo_fpe(self, data: str, tweak: str) -> str:
        """
        Pseudo-FPE (Format-Preserving Encryption) para el MVP.
        Toma el dato, el tweak de dominio y la PIK, y devuelve un valor ofuscado 
        del mismo largo/formato (ilustrativo).
        
        TODO: Reemplazar con FF1 o FF3 real usando la librería `ff3`.
        """
        if not data:
            return data
            
        # Generar un hash determinista basado en el dato original, PIK y el tweak
        hash_digest = self.hash_sha256(data, salt=tweak)
        
        # Para mantener el "formato" (ej: si es numérico, devolver número del mismo largo, etc.)
        # Aquí hacemos una simplificación: devolvemos los primeros N caracteres del hash
        # que coincidan con la longitud del dato original, mapeado a mayúsculas.
        length = len(data)
        
        # Una forma ingenua de mantener formato:
        # si el orginal es "12345678-K", devolvemos algo como "AB8F2E1D-X"
        result = []
        hash_idx = 0
        
        for char in data:
            if char.isdigit():
                # Tomar un dígito del hash
                while hash_idx < len(hash_digest) and not hash_digest[hash_idx].isdigit():
                    hash_idx += 1
                if hash_idx < len(hash_digest):
                    result.append(hash_digest[hash_idx])
                    hash_idx += 1
                else:
                    result.append('0') # fallback
            elif char.isalpha():
                # Tomar una letra del hash
                while hash_idx < len(hash_digest) and not hash_digest[hash_idx].isalpha():
                    hash_idx += 1
                if hash_idx < len(hash_digest):
                    result.append(hash_digest[hash_idx].upper())
                    hash_idx += 1
                else:
                    result.append('X') # fallback
            else:
                # Mantener guiones u otros caracteres
                result.append(char)
                
        return "".join(result)
