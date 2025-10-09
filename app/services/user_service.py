"""
用户服务层 - 业务逻辑处理
"""

from datetime import datetime, timedelta

from sqlalchemy import Column, and_
from sqlalchemy.orm import Session

from app.core.security import (
    bytes_to_str,
    create_access_token,
    encrypt_with_key,
    generate_session_key,
    generate_session_token,
    generate_username,
    hash_password,
    prepare_user_keys,
    recover_user_key,
    str_to_bytes,
    verify_password,
)
from app.models.user import User, UserSession
from app.schemas.user import (
    LoginResponse,
    SessionResponse,
    UserCreateRequest,
    UserListResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)
from config.config import settings


class UserService:
    """用户服务类"""

    @staticmethod
    def register_user(db: Session, user_data: UserRegisterRequest) -> UserResponse:
        """
        用户注册

        Args:
            db: 数据库会话
            user_data: 用户注册数据

        Returns:
            创建的用户信息

        Raises:
            ValueError: 当邮箱已存在时
        """
        # 检查邮箱是否已存在
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise ValueError("邮箱已存在")

        # 生成用户名
        while True:
            username = generate_username()
            if not db.query(User).filter(User.username == username).first():
                break

        # 准备用户密钥
        salt, encryption_key, encrypted_user_key = prepare_user_keys(user_data.password)

        # 使用bcrypt哈希密码
        password_hash = hash_password(user_data.password)

        # 创建用户
        user = User(
            username=username,
            email=user_data.email,
            password_hash=password_hash,
            salt=bytes_to_str(salt),
            encrypted_user_key=bytes_to_str(encrypted_user_key),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return UserResponse.model_validate(user)

    @staticmethod
    def authenticate_user(db: Session, login_data: UserLoginRequest) -> User | None:
        """
        用户认证

        Args:
            db: 数据库会话
            login_data: 登录数据

        Returns:
            认证成功的用户或None
        """
        user = db.query(User).filter(User.username == login_data.username).first()
        if not user:
            return None

        if not verify_password(login_data.password, str(user.password_hash)):
            return None

        return user

    @staticmethod
    def login_user(db: Session, login_data: UserLoginRequest) -> LoginResponse:
        """
        用户登录

        Args:
            db: 数据库会话
            login_data: 登录数据

        Returns:
            登录响应（包含token和用户信息）

        Raises:
            ValueError: 当用户名或密码错误时
        """
        user = UserService.authenticate_user(db, login_data)
        if not user:
            raise ValueError("用户名或密码错误")

        # 恢复用户密钥
        try:
            salt = str_to_bytes(str(user.salt))
            encrypted_user_key = str_to_bytes(str(user.encrypted_user_key))
            user_key = recover_user_key(login_data.password, salt, encrypted_user_key)
        except Exception as e:
            raise ValueError(f"密钥恢复失败: {str(e)}") from e

        # 生成会话
        session_token = generate_session_token()
        session_key = generate_session_key()

        # 使用用户密钥加密会话密钥
        encrypted_session_key = encrypt_with_key(session_key, user_key)

        # 创建会话记录
        expires_at = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )
        session = UserSession(
            user_id=user.id,
            session_token=session_token,
            encrypted_session_key=bytes_to_str(encrypted_session_key),
            expires_at=expires_at,
        )

        db.add(session)
        db.commit()

        # 创建JWT token
        access_token = create_access_token(
            data={"sub": user.username, "session_id": session.id}
        )

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> UserResponse | None:
        """根据ID获取用户"""
        user = db.query(User).filter(User.id == user_id).first()
        return UserResponse.model_validate(user) if user else None

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> UserResponse | None:
        """根据用户名获取用户"""
        user = db.query(User).filter(User.username == username).first()
        return UserResponse.model_validate(user) if user else None

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> UserResponse | None:
        """根据邮箱获取用户"""
        user = db.query(User).filter(User.email == email).first()
        return UserResponse.model_validate(user) if user else None

    @staticmethod
    def update_user(
        db: Session, user_id: int, user_data: UserUpdateRequest
    ) -> UserResponse:
        """
        更新用户信息

        Args:
            db: 数据库会话
            user_id: 用户ID
            user_data: 更新数据

        Returns:
            更新后的用户信息

        Raises:
            ValueError: 当用户不存在或邮箱已被占用时
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("用户不存在")

        # 检查邮箱冲突
        if user_data.email and user_data.email != str(user.email):
            existing_user = (
                db.query(User)
                .filter(and_(User.email == user_data.email, User.id != user_id))
                .first()
            )
            if existing_user:
                raise ValueError("邮箱已被其他用户使用")
            user.email = Column(user_data.email)

        # 更新密码
        if user_data.password:
            # 重新生成密钥
            salt, encryption_key, encrypted_user_key = prepare_user_keys(
                user_data.password
            )
            password_hash = hash_password(user_data.password)

            user.password_hash = Column(password_hash)
            user.salt = Column(bytes_to_str(salt))
            user.encrypted_user_key = Column(bytes_to_str(encrypted_user_key))

        db.commit()
        db.refresh(user)

        return UserResponse.model_validate(user)

    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        """
        删除用户

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            是否删除成功
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        db.delete(user)
        db.commit()
        return True

    @staticmethod
    def list_users(db: Session, page: int = 1, size: int = 10) -> UserListResponse:
        """
        分页获取用户列表

        Args:
            db: 数据库会话
            page: 页码
            size: 每页大小

        Returns:
            用户列表响应
        """
        offset = (page - 1) * size

        # 获取用户列表
        users_query = db.query(User).offset(offset).limit(size)
        users = users_query.all()

        # 获取总数
        total = db.query(User).count()

        return UserListResponse(
            users=[UserResponse.model_validate(user) for user in users],
            total=total,
            page=page,
            size=size,
        )

    @staticmethod
    def create_user(db: Session, user_data: UserCreateRequest) -> UserResponse:
        """
        管理员创建用户

        Args:
            db: 数据库会话
            user_data: 用户创建数据

        Returns:
            创建的用户信息

        Raises:
            ValueError: 当用户名或邮箱已存在时
        """
        # 生成或验证用户名
        if user_data.username:
            existing_user = (
                db.query(User).filter(User.username == user_data.username).first()
            )
            if existing_user:
                raise ValueError("用户名已存在")
            username = user_data.username
        else:
            # 自动生成用户名
            while True:
                username = generate_username()
                if not db.query(User).filter(User.username == username).first():
                    break

        # 检查邮箱
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise ValueError("邮箱已存在")

        # 准备用户密钥
        salt, encryption_key, encrypted_user_key = prepare_user_keys(user_data.password)
        password_hash = hash_password(user_data.password)

        # 创建用户
        user = User(
            username=username,
            email=user_data.email,
            password_hash=password_hash,
            salt=bytes_to_str(salt),
            encrypted_user_key=bytes_to_str(encrypted_user_key),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return UserResponse.model_validate(user)

    @staticmethod
    def get_user_sessions(db: Session, user_id: int) -> list[SessionResponse]:
        """获取用户的所有会话"""
        sessions = db.query(UserSession).filter(UserSession.user_id == user_id).all()
        return [SessionResponse.model_validate(session) for session in sessions]

    @staticmethod
    def revoke_session(
        db: Session, session_id: str, user_id: int | None = None
    ) -> bool:
        """
        撤销会话

        Args:
            db: 数据库会话
            session_id: 会话ID
            user_id: 用户ID（可选，用于权限检查）

        Returns:
            是否撤销成功
        """
        query = db.query(UserSession).filter(UserSession.id == session_id)
        if user_id:
            query = query.filter(UserSession.user_id == user_id)

        session = query.first()
        if not session:
            return False

        db.delete(session)
        db.commit()
        return True

    @staticmethod
    def cleanup_expired_sessions(db: Session) -> int:
        """清理过期会话"""
        expired_sessions = db.query(UserSession).filter(
            UserSession.expires_at < datetime.utcnow()
        )
        count = expired_sessions.count()
        expired_sessions.delete()
        db.commit()
        return count
