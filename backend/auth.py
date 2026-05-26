"""密码哈希和验证 — PBKDF2-SHA256 + 随机盐，纯标准库实现"""
import hashlib
import secrets
import hmac

_ITERATIONS = 600_000  # OWASP 2025 recommended minimum for PBKDF2-SHA256


def hash_password(password: str) -> str:
    """生成 salted hash: 'salt$iterations$hash'"""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITERATIONS)
    return f"{salt}${_ITERATIONS}${key.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """验证密码。自动检测旧版 SHA256 hash 并触发重哈希。"""
    parts = stored.split("$")
    if len(parts) == 3:
        salt, iterations, h = parts
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations))
        return hmac.compare_digest(key.hex(), h)
    # 兼容旧版 SHA256: 'salt$hash' (2 parts)
    if len(parts) == 2:
        salt, h = parts
        result = hashlib.sha256((salt + password).encode()).hexdigest() == h
        return result
    return False


def needs_rehash(stored: str) -> bool:
    """是否需要重新哈希（非 pbkdf2 格式）"""
    parts = stored.split("$")
    return len(parts) != 3
