"""密码哈希和验证 — SHA256 + 随机盐，纯标准库实现"""
import hashlib
import secrets


def hash_password(password: str) -> str:
    """生成 salted hash: 'salt$hash'"""
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${h}"


def verify_password(password: str, stored: str) -> bool:
    """验证密码。兼容旧版明文密码（自动检测非 hash 格式）。"""
    if "$" not in stored:
        return password == stored
    salt, h = stored.split("$", 1)
    return hashlib.sha256((salt + password).encode()).hexdigest() == h


def needs_rehash(stored: str) -> bool:
    """是否需要重新哈希（旧版明文密码）"""
    return "$" not in stored
