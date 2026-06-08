import base64
import hashlib
import os

from cryptography.fernet import Fernet

MASTER_KEY_ENV = 'SOIDIED_MASTER_KEY'


def _derive_fernet_key(master_key: str) -> bytes:
    digest = hashlib.sha256(master_key.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest)


def get_master_key() -> str:
    master_key = os.environ.get(MASTER_KEY_ENV, '').strip()
    if not master_key:
        raise RuntimeError(f'{MASTER_KEY_ENV} is required to encrypt message attachments')
    return master_key


def get_fernet(master_key: str | None = None) -> Fernet:
    return Fernet(_derive_fernet_key(master_key or get_master_key()))


def encrypt_bytes(data: bytes, master_key: str | None = None) -> bytes:
    return get_fernet(master_key).encrypt(data)


def decrypt_bytes(data: bytes, master_key: str | None = None) -> bytes:
    return get_fernet(master_key).decrypt(data)
