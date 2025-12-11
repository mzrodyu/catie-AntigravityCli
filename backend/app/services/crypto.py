from cryptography.fernet import Fernet
import base64
import hashlib

from app.config import settings


def get_fernet_key():
    """从 secret_key 生成 Fernet 密钥"""
    key = hashlib.sha256(settings.secret_key.encode()).digest()
    return base64.urlsafe_b64encode(key)


def encrypt_token(token: str) -> str:
    """加密 token"""
    f = Fernet(get_fernet_key())
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """解密 token"""
    f = Fernet(get_fernet_key())
    return f.decrypt(encrypted_token.encode()).decode()
