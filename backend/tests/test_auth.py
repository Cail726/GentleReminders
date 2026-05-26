"""测试 auth.py — 密码哈希和验证 (pbkdf2)"""
from auth import hash_password, verify_password, needs_rehash


class TestHashPassword:
    def test_format_contains_dollar(self):
        result = hash_password("mypassword")
        assert result.count("$") == 2  # salt$iterations$hash (3 parts)

    def test_salt_is_32_hex_chars(self):
        result = hash_password("mypassword")
        salt = result.split("$")[0]
        assert len(salt) == 32

    def test_hash_is_64_hex_chars(self):
        result = hash_password("mypassword")
        h = result.split("$")[2]  # 3-part format
        assert len(h) == 64

    def test_different_calls_produce_different_hashes(self):
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2

    def test_empty_password(self):
        result = hash_password("")
        assert result.count("$") == 2
        assert len(result.split("$")[2]) == 64

    def test_unicode_password(self):
        result = hash_password("中文密码🎉")
        assert result.count("$") == 2

    def test_password_with_dollar_sign(self):
        result = hash_password("pass$word")
        assert result.count("$") >= 2


class TestVerifyPassword:
    def test_correct_password(self):
        h = hash_password("correct")
        assert verify_password("correct", h) is True

    def test_wrong_password(self):
        h = hash_password("correct")
        assert verify_password("wrong", h) is False

    def test_legacy_sha256_still_works(self):
        """旧版 SHA256 格式 (salt$hash) 仍然可验证"""
        import hashlib
        import secrets
        salt = secrets.token_hex(16)
        h = hashlib.sha256((salt + "legacy").encode()).hexdigest()
        stored = f"{salt}${h}"
        assert verify_password("legacy", stored) is True
        assert verify_password("wrong", stored) is False

    def test_legacy_plaintext_rejected(self):
        """明文密码不再被接受"""
        assert verify_password("plain", "plain") is False

    def test_tampered_salt(self):
        h = hash_password("correct")
        salt, iterations, hash_part = h.split("$", 2)
        tampered = salt + "x" + "$" + iterations + "$" + hash_part
        assert verify_password("correct", tampered) is False

    def test_tampered_hash(self):
        h = hash_password("correct")
        salt, iterations, _ = h.split("$", 2)
        tampered = salt + "$" + iterations + "$" + "0" * 64
        assert verify_password("correct", tampered) is False

    def test_empty_password_vs_stored(self):
        h = hash_password("")
        assert verify_password("", h) is True


class TestNeedsRehash:
    def test_sha256_needs_rehash(self):
        """旧版 SHA256 格式需要重哈希"""
        import hashlib
        import secrets
        salt = secrets.token_hex(16)
        h = hashlib.sha256((salt + "old").encode()).hexdigest()
        assert needs_rehash(f"{salt}${h}") is True

    def test_pbkdf2_does_not_need_rehash(self):
        h = hash_password("test")
        assert needs_rehash(h) is False

    def test_plaintext_needs_rehash(self):
        assert needs_rehash("anything") is True

    def test_empty_string_needs_rehash(self):
        assert needs_rehash("") is True
