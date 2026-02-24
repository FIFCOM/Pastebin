"""
Schema validators
"""


def normalize_sha256_hex(value: str | None, *, field_label: str = "密码") -> str | None:
    if value is None:
        return None

    if len(value) != 64 or not all(c in "0123456789abcdefABCDEF" for c in value):
        raise ValueError(f"{field_label}必须是有效的SHA256哈希(64位十六进制字符串)")
    return value.lower()
