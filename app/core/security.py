"""
安全和加密工具
"""

import base64
import os
import secrets
import string
from datetime import datetime, timedelta
from io import BytesIO

import bcrypt
import pyotp
import qrcode
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from jose import JWTError, jwt

from config.config import settings


def generate_username() -> str:
    """生成随机用户名: USER_RANDOMSTR"""
    random_str = "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8)
    )
    return f"USER_{random_str}"


def generate_salt() -> bytes:
    """生成随机盐值"""
    return os.urandom(settings.salt_length)


def generate_encryption_key() -> bytes:
    """生成随机加密密钥"""
    return os.urandom(settings.encryption_key_length)


def generate_session_key() -> bytes:
    """生成随机会话密钥"""
    return os.urandom(settings.session_key_length)


def derive_master_key(password: str, salt: bytes) -> bytes:
    """
    使用PBKDF2从密码和盐派生master_key

    Args:
        password: SHA256哈希后的密码
        salt: 盐值

    Returns:
        派生的master_key
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 32字节 = 256位
        salt=salt,
        iterations=settings.pbkdf2_iterations,
    )
    return kdf.derive(password.encode())


def encrypt_with_key(data: bytes, key: bytes) -> bytes:
    """
    使用AES-GCM加密数据（与前端Web Crypto API兼容）

    Args:
        data: 要加密的数据
        key: 加密密钥（32字节）

    Returns:
        加密后的数据（IV + 密文，12字节IV + 密文）
    """
    # 生成随机IV（12字节用于GCM）
    iv = os.urandom(12)
    
    # 使用AES-GCM加密
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(iv, data, None)
    
    # 返回 IV + 密文
    return iv + ciphertext


def decrypt_with_key(encrypted_data: bytes, key: bytes) -> bytes:
    """
    使用AES-GCM解密数据（与前端Web Crypto API兼容）

    Args:
        encrypted_data: 加密的数据（IV + 密文）
        key: 解密密钥（32字节）

    Returns:
        解密后的数据
    """
    try:
        # 提取IV和密文
        iv = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        
        # 使用AES-GCM解密
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(iv, ciphertext, None)
        
        return plaintext
    except Exception as e:
        raise ValueError(f"解密失败: {str(e)}") from e


def hash_password(password: str) -> str:
    """
    使用bcrypt哈希密码

    Args:
        password: SHA256哈希后的密码或明文密码

    Returns:
        bcrypt哈希后的密码
    """
    # 将密码转换为字节
    password_bytes = password.encode('utf-8')
    # 生成盐并哈希密码
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # 返回字符串形式
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码

    Args:
        plain_password: 明文密码（SHA256哈希或明文）
        hashed_password: bcrypt哈希后的密码

    Returns:
        密码是否正确
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    创建JWT访问令牌

    Args:
        data: 要编码的数据
        expires_delta: 过期时间差

    Returns:
        JWT令牌
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def verify_token(token: str) -> dict | None:
    """
    验证JWT令牌

    Args:
        token: JWT令牌

    Returns:
        解码后的数据或None
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        return None


def generate_session_token() -> str:
    """生成会话令牌"""
    return secrets.token_urlsafe(32)


def generate_api_key() -> str:
    """
    生成API密钥

    Returns:
        格式为 'pk_' + 32字符随机字符串的API密钥
    """
    random_part = secrets.token_urlsafe(24)  # 生成32个字符的随机部分
    return f"pk_{random_part}"


def hash_api_key(api_key: str) -> str:
    """
    哈希API密钥

    Args:
        api_key: API密钥明文

    Returns:
        哈希后的API密钥
    """
    return hash_password(api_key)


def verify_api_key(plain_api_key: str, hashed_api_key: str) -> bool:
    """
    验证API密钥

    Args:
        plain_api_key: 明文API密钥
        hashed_api_key: 哈希后的API密钥

    Returns:
        API密钥是否正确
    """
    return verify_password(plain_api_key, hashed_api_key)


def bytes_to_str(data: bytes) -> str:
    """将字节转换为base64字符串"""
    return base64.b64encode(data).decode()


def str_to_bytes(data: str) -> bytes:
    """将base64字符串转换为字节"""
    return base64.b64decode(data.encode())


def key_to_urlsafe_str(key: bytes) -> str:
    """
    将加密密钥转换为URL-safe base64字符串
    专门用于加密密钥的编码，使其可以安全地用于URL
    """
    base64_str = base64.b64encode(key).decode()
    return base64_str.replace('+', '-').replace('/', '_').replace('=', '')


def urlsafe_str_to_key(urlsafe_base64: str) -> bytes:
    """
    将URL-safe base64字符串转换为加密密钥
    专门用于加密密钥的解码
    """
    # 将URL-safe base64转换回标准base64
    base64_str = urlsafe_base64.replace('-', '+').replace('_', '/')
    # 补充padding
    padding = 4 - len(base64_str) % 4
    if padding != 4:
        base64_str += '=' * padding
    return base64.b64decode(base64_str.encode())


def prepare_user_keys(password: str) -> tuple[bytes, bytes, bytes]:
    """
    准备用户密钥（注册时使用）

    Args:
        password: SHA256哈希后的密码

    Returns:
        (salt, encryption_key, encrypted_user_key)
    """
    # 生成盐值和用户密钥
    salt = generate_salt()
    encryption_key = generate_encryption_key()

    # 派生master_key
    master_key = derive_master_key(password, salt)

    # 加密用户密钥
    encrypted_user_key = encrypt_with_key(encryption_key, master_key)

    return salt, encryption_key, encrypted_user_key


def recover_user_key(password: str, salt: bytes, encrypted_user_key: bytes) -> bytes:
    """
    恢复用户密钥（登录时使用）

    Args:
        password: SHA256哈希后的密码
        salt: 盐值
        encrypted_user_key: 加密的用户密钥

    Returns:
        解密后的用户密钥
    """
    # 派生master_key
    master_key = derive_master_key(password, salt)

    # 解密用户密钥
    user_key = decrypt_with_key(encrypted_user_key, master_key)

    return user_key


def generate_totp_secret() -> str:
    """
    生成TOTP密钥

    Returns:
        32个字符的Base32编码的TOTP密钥
    """
    return pyotp.random_base32()


def verify_totp_code(secret: str, token: str, window: int = 1) -> bool:
    """
    验证TOTP代码

    Args:
        secret: TOTP密钥
        token: 用户输入的6位数字代码
        window: 时间窗口容忍度，1表示允许前后各30秒的偏差

    Returns:
        验证是否成功
    """
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=window)
    except Exception:
        return False


def generate_totp_qr_code_url(
    secret: str, username: str, app_name: str = "MaterialBin"
) -> str:
    """
    生成TOTP二维码URL

    Args:
        secret: TOTP密钥
        username: 用户名
        app_name: 应用名称

    Returns:
        二维码图片的base64编码字符串
    """
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=username, issuer_name=app_name)

    # 生成二维码
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # 转换为base64字符串
    buffer = BytesIO()
    img.save(buffer, "PNG")
    buffer.seek(0)

    img_base64 = base64.b64encode(buffer.read()).decode()
    return f"data:image/png;base64,{img_base64}"
