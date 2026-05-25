"""测试 auth.py — 密码哈希和验证"""
from auth import hash_password, verify_password, needs_rehash


class TestHashPassword:
    def test_format_contains_dollar(self):
        result = hash_password("mypassword")
        assert "$" in result

    def test_salt_is_32_hex_chars(self):
        result = hash_password("mypassword")
        salt = result.split("$")[0]
        assert len(salt) == 32

    def test_hash_is_64_hex_chars(self):
        result = hash_password("mypassword")
        h = result.split("$")[1]
        assert len(h) == 64

    def test_different_calls_produce_different_hashes(self):
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2

    def test_empty_password(self):
        result = hash_password("")
        assert "$" in result
        assert len(result.split("$")[1]) == 64

    def test_unicode_password(self):
        result = hash_password("中文密码🎉")
        assert "$" in result

    def test_password_with_dollar_sign(self):
        result = hash_password("pass$word")
        assert result.count("$") >= 1


class TestVerifyPassword:
    def test_correct_password(self):
        h = hash_password("correct")
        assert verify_password("correct", h) is True

    def test_wrong_password(self):
        h = hash_password("correct")
        assert verify_password("wrong", h) is False

    def test_legacy_plaintext_match(self):
        assert verify_password("plain", "plain") is True

    def test_legacy_plaintext_mismatch(self):
        assert verify_password("plain", "different") is False

    def test_tampered_salt(self):
        h = hash_password("correct")
        salt, hash_part = h.split("$", 1)
        tampered = salt + "x" + "$" + hash_part
        assert verify_password("correct", tampered) is False

    def test_tampered_hash(self):
        h = hash_password("correct")
        salt, _ = h.split("$", 1)
        tampered = salt + "$" + "0" * 64
        assert verify_password("correct", tampered) is False

    def test_empty_password_vs_stored(self):
        h = hash_password("")
        assert verify_password("", h) is True


class TestNeedsRehash:
    def test_plaintext_needs_rehash(self):
        assert needs_rehash("plaintext") is True

    def test_hashed_does_not_need_rehash(self):
        h = hash_password("test")
        assert needs_rehash(h) is False

    def test_empty_string_needs_rehash(self):
        assert needs_rehash("") is True
