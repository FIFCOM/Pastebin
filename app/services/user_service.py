"""
用户服务层 - 业务逻辑处理
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    bytes_to_str,
    create_access_token,
    encrypt_session_key,
    encrypt_with_key,
    generate_refresh_token,
    generate_session_key,
    generate_totp_provisioning_uri,
    generate_totp_secret,
    generate_username,
    hash_password,
    hash_refresh_token,
    prepare_user_keys,
    recover_user_key,
    str_to_bytes,
    verify_password,
    verify_totp_code,
)
from app.core.time_utils import is_expired
from app.models.user import UsedRefreshToken, User, UserSession, UserSessionKey
from app.schemas.user import (
    LoginResponse,
    SessionResponse,
    TotpSetupResponse,
    TotpStatusResponse,
    TotpVerifyRequest,
    UserCreateRequest,
    UserListResponse,
    UserLoginRequest,
    UserLoginWithTotpRequest,
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

        return UserResponse.model_validate(user)  # type: ignore

    @staticmethod
    def authenticate_user(db: Session, login_data: UserLoginRequest) -> User | None:
        """
        用户认证

        说明：
        - login_data.username 字段可以填写「用户名」或「邮箱」
        - 为了兼容当前注册流程（只能输入邮箱），这里同时按 username 和 email 匹配

        Args:
            db: 数据库会话
            login_data: 登录数据

        Returns:
            认证成功的用户或None
        """
        user = db.query(User).filter(User.email == login_data.email).first()
        if not user:
            return None

        if not verify_password(login_data.password, user.password_hash):  # type: ignore
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
            ValueError: 当用户名或密码错误，或需要TOTP验证时
        """
        user = UserService.authenticate_user(db, login_data)
        if not user:
            raise ValueError("邮箱或密码错误")

        # 检查用户是否启用了TOTP
        if user.totp_secret:  # type: ignore
            raise ValueError("此账户启用了两步验证，请使用TOTP代码登录")

        # 恢复用户密钥
        try:
            salt = str_to_bytes(user.salt)  # type: ignore
            encrypted_user_key = str_to_bytes(user.encrypted_user_key)  # type: ignore
            user_key = recover_user_key(login_data.password, salt, encrypted_user_key)
        except Exception as e:
            raise ValueError(f"密钥恢复失败: {str(e)}") from e

        # 创建会话（refresh token + 服务端保存 session_key，用于后续续期）
        refresh_token = generate_refresh_token()
        refresh_token_hash = hash_refresh_token(refresh_token)
        session_key = generate_session_key()

        encrypted_user_key_for_session = encrypt_with_key(user_key, session_key)
        expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

        session = UserSession(
            user_id=user.id,  # type: ignore[arg-type]
            session_token=refresh_token_hash,
            encrypted_session_key=bytes_to_str(encrypted_user_key_for_session),
            expires_at=expires_at,
        )
        db.add(session)
        db.flush()

        session_key_record = UserSessionKey(
            session_id=session.id,
            encrypted_session_key=encrypt_session_key(session_key, str(session.id)),
        )
        db.add(session_key_record)
        db.commit()

        access_token = create_access_token(
            data={
                "sub": user.username,
                "session_id": session.id,
                "type": "access",
            }
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),  # type: ignore
        )

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> UserResponse | None:
        """根据ID获取用户"""
        user = db.query(User).filter(User.id == user_id).first()
        return UserResponse.model_validate(user) if user else None  # type: ignore

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> UserResponse | None:
        """根据用户名获取用户"""
        user = db.query(User).filter(User.username == username).first()
        return UserResponse.model_validate(user) if user else None  # type: ignore

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> UserResponse | None:
        """根据邮箱获取用户"""
        user = db.query(User).filter(User.email == email).first()
        return UserResponse.model_validate(user) if user else None  # type: ignore

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
        if user_data.email and user_data.email != user.email:
            existing_user = (
                db.query(User)
                .filter(and_(User.email == user_data.email, User.id != user_id))
                .first()
            )
            if existing_user:
                raise ValueError("邮箱已被其他用户使用")
            user.email = str(user_data.email)  # type: ignore[assignment]

        # 更新密码
        if user_data.password:
            # 重新生成密钥
            salt, _encryption_key, encrypted_user_key = prepare_user_keys(user_data.password)
            password_hash = hash_password(user_data.password)

            user.password_hash = password_hash  # type: ignore
            user.salt = bytes_to_str(salt)  # type: ignore
            user.encrypted_user_key = bytes_to_str(encrypted_user_key)  # type: ignore

        db.commit()
        db.refresh(user)

        return UserResponse.model_validate(user)  # type: ignore

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
            users=[UserResponse.model_validate(user) for user in users],  # type: ignore
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
            password_hash=password_hash,  # type: ignore
            salt=bytes_to_str(salt),  # type: ignore
            encrypted_user_key=bytes_to_str(encrypted_user_key),  # type: ignore
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return UserResponse.model_validate(user)  # type: ignore

    @staticmethod
    def get_user_sessions(db: Session, user_id: int) -> list[SessionResponse]:
        """获取用户的所有会话"""
        sessions = db.query(UserSession).filter(UserSession.user_id == user_id).all()
        return [SessionResponse.model_validate(session) for session in sessions]  # type: ignore

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
            UserSession.expires_at < datetime.now(UTC)
        )
        count = expired_sessions.count()
        expired_sessions.delete()
        db.commit()
        return count

    @staticmethod
    def get_totp_status(db: Session, user_id: int) -> TotpStatusResponse:
        """
        获取用户TOTP状态

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            TOTP状态信息

        Raises:
            ValueError: 当用户不存在时
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("用户不存在")

        enabled = bool(user.totp_secret)  # type: ignore
        return TotpStatusResponse(
            enabled=enabled,
            # setup_required 表示「是否需要重新发起 setup 获取二维码/密钥」
            # 若存在 pending_secret，则说明已经 setup 过但尚未 verify。
            setup_required=not bool(user.totp_pending_secret or user.totp_secret),  # type: ignore
        )

    @staticmethod
    def setup_totp(db: Session, user_id: int) -> TotpSetupResponse:
        """
        设置用户TOTP

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            TOTP设置信息（包含密钥与 provisioning URI，前端生成二维码展示）

        Raises:
            ValueError: 当用户不存在时
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("用户不存在")

        # 生成/复用待验证的 TOTP 密钥：
        # - 未启用时：若已有 pending，则复用，避免用户重复点击导致密钥变化
        # - 已启用时：视为「重新生成」，每次都生成新的 pending，verify 后替换现有密钥
        if user.totp_secret:  # type: ignore
            totp_secret = generate_totp_secret()
            user.totp_pending_secret = totp_secret  # type: ignore[assignment]
        elif user.totp_pending_secret:  # type: ignore
            totp_secret = user.totp_pending_secret  # type: ignore[assignment]
        else:
            totp_secret = generate_totp_secret()
            user.totp_pending_secret = totp_secret  # type: ignore[assignment]

        provisioning_uri = generate_totp_provisioning_uri(
            totp_secret, user.username  # type: ignore[arg-type]
        )

        db.commit()

        return TotpSetupResponse(secret=totp_secret, provisioning_uri=provisioning_uri) # type: ignore[assignment]

    @staticmethod
    def verify_and_enable_totp(
        db: Session, user_id: int, totp_data: TotpVerifyRequest
    ) -> bool:
        """
        验证并启用TOTP

        Args:
            db: 数据库会话
            user_id: 用户ID
            totp_data: TOTP验证数据

        Returns:
            是否验证成功

        Raises:
            ValueError: 当用户不存在或TOTP密钥未设置时
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("用户不存在")

        if not user.totp_pending_secret:  # type: ignore
            raise ValueError("没有待验证的TOTP密钥，请先生成二维码")

        # 验证TOTP代码
        is_valid = verify_totp_code(
            user.totp_pending_secret, totp_data.totp_code  # type: ignore[arg-type]
        )

        if is_valid:
            # 验证成功：启用（或替换）TOTP密钥
            user.totp_secret = user.totp_pending_secret  # type: ignore[assignment]
            user.totp_pending_secret = None  # type: ignore[assignment]
            db.commit()
            return True
        else:
            return False

    @staticmethod
    def disable_totp(db: Session, user_id: int) -> bool:
        """
        禁用用户TOTP

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            是否禁用成功

        Raises:
            ValueError: 当用户不存在时
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("用户不存在")

        # 清空 TOTP 密钥（包含待验证的）
        user.totp_secret = None  # type: ignore[assignment]
        user.totp_pending_secret = None  # type: ignore[assignment]
        db.commit()
        return True

    @staticmethod
    def authenticate_user_with_totp(
        db: Session, login_data: UserLoginWithTotpRequest
    ) -> User | None:
        """
        用户认证（包含TOTP验证）

        说明：
        - login_data.username 字段可以填写「用户名」或「邮箱」

        Args:
            db: 数据库会话
            login_data: 登录数据（包含TOTP代码）

        Returns:
            认证成功的用户或None
        """
        user = db.query(User).filter(User.email == login_data.email).first()
        if not user:
            return None

        # 验证密码
        if not verify_password(login_data.password, user.password_hash):  # type: ignore
            return None

        # 验证TOTP代码
        if user.totp_secret:  # type: ignore
            if not verify_totp_code(user.totp_secret, login_data.totp_code):  # type: ignore
                return None

        return user

    @staticmethod
    def login_user_with_totp(
        db: Session, login_data: UserLoginWithTotpRequest
    ) -> LoginResponse:
        """
        用户登录（包含TOTP验证）

        Args:
            db: 数据库会话
            login_data: 登录数据（包含TOTP代码）

        Returns:
            登录响应（包含token和用户信息）

        Raises:
            ValueError: 当用户名、密码或TOTP代码错误时
        """
        user = UserService.authenticate_user_with_totp(db, login_data)
        if not user:
            raise ValueError("邮箱、密码或TOTP代码错误")

        # 恢复用户密钥
        try:
            salt = str_to_bytes(user.salt)  # type: ignore
            encrypted_user_key = str_to_bytes(user.encrypted_user_key)  # type: ignore
            user_key = recover_user_key(login_data.password, salt, encrypted_user_key)
        except Exception as e:
            raise ValueError(f"密钥恢复失败: {str(e)}") from e

        refresh_token = generate_refresh_token()
        refresh_token_hash = hash_refresh_token(refresh_token)
        session_key = generate_session_key()

        encrypted_user_key_for_session = encrypt_with_key(user_key, session_key)
        expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

        session = UserSession(
            user_id=user.id,  # type: ignore[arg-type]
            session_token=refresh_token_hash,
            encrypted_session_key=bytes_to_str(encrypted_user_key_for_session),
            expires_at=expires_at,
        )
        db.add(session)
        db.flush()

        session_key_record = UserSessionKey(
            session_id=session.id,
            encrypted_session_key=encrypt_session_key(session_key, str(session.id)),
        )
        db.add(session_key_record)
        db.commit()

        access_token = create_access_token(
            data={
                "sub": user.username,
                "session_id": session.id,
                "type": "access",
            }
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )

    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> tuple[str, str]:
        """
        使用 refresh token 续期：返回 (access_token, new_refresh_token)。

        - 每次刷新都会旋转 refresh token：返回新的 refresh token，并让旧的立即失效
        - 旧 refresh token 被再次使用会被视为“复用”，并立即撤销整个会话
        """
        old_refresh_token_hash = hash_refresh_token(refresh_token)

        # 尝试锁定会话行（MySQL/Postgres 会生效；SQLite 会忽略但不影响正确性）
        session = (
            db.query(UserSession)
            .filter(UserSession.session_token == old_refresh_token_hash)
            .with_for_update()
            .first()
        )

        if session is None:
            reused = (
                db.query(UsedRefreshToken)
                .filter(UsedRefreshToken.token_hash == old_refresh_token_hash)
                .first()
            )
            if reused is not None:
                # 复用旧 refresh token：撤销整个会话
                session_to_revoke = (
                    db.query(UserSession).filter(UserSession.id == reused.session_id).first()
                )
                if session_to_revoke is not None:
                    db.delete(session_to_revoke)
                    db.commit()
                raise ValueError("检测到 refresh token 复用，已撤销会话，请重新登录")

            raise ValueError("无效的 refresh token")

        if is_expired(session.expires_at):  # type: ignore[arg-type]
            db.delete(session)
            db.commit()
            raise ValueError("refresh token 已过期，请重新登录")

        user = db.query(User).filter(User.id == session.user_id).first()
        if user is None:
            db.delete(session)
            db.commit()
            raise ValueError("用户不存在")

        new_refresh_token = generate_refresh_token()
        new_refresh_token_hash = hash_refresh_token(new_refresh_token)
        new_expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

        # 通过条件更新实现原子旋转，避免高并发下出现“两个新 refresh token 都返回但只有一个有效”的问题
        try:
            updated = (
                db.query(UserSession)
                .filter(
                    UserSession.id == session.id,
                    UserSession.session_token == old_refresh_token_hash,
                )
                .update(
                    {
                        UserSession.session_token: new_refresh_token_hash,
                        UserSession.expires_at: new_expires_at,
                    },
                    synchronize_session=False,
                )
            )

            if updated != 1:
                db.rollback()
                # 视为“旧 refresh token 被复用”，撤销会话
                session_to_revoke = (
                    db.query(UserSession).filter(UserSession.id == session.id).first()
                )
                if session_to_revoke is not None:
                    db.delete(session_to_revoke)
                    db.commit()
                raise ValueError("检测到 refresh token 复用，已撤销会话，请重新登录")

            db.add(
                UsedRefreshToken(
                    session_id=session.id,
                    token_hash=old_refresh_token_hash,
                    replaced_by_hash=new_refresh_token_hash,
                )
            )
            db.commit()
        except IntegrityError:
            db.rollback()
            session_to_revoke = (
                db.query(UserSession).filter(UserSession.id == session.id).first()
            )
            if session_to_revoke is not None:
                db.delete(session_to_revoke)
                db.commit()
            raise ValueError("检测到 refresh token 复用，已撤销会话，请重新登录") from None

        access_token = create_access_token(
            data={
                "sub": user.username,
                "session_id": session.id,
                "type": "access",
            }
        )
        return access_token, new_refresh_token

    @staticmethod
    def logout_by_refresh_token(db: Session, refresh_token: str) -> bool:
        """撤销当前会话（根据 refresh token 定位）"""
        refresh_token_hash = hash_refresh_token(refresh_token)
        session = (
            db.query(UserSession).filter(UserSession.session_token == refresh_token_hash).first()
        )
        if session is None:
            return False
        db.delete(session)
        db.commit()
        return True

    @staticmethod
    def logout_all_sessions(db: Session, user_id: int) -> int:
        """撤销用户的全部会话（所有设备登出）"""
        sessions = db.query(UserSession).filter(UserSession.user_id == user_id)
        count = sessions.count()
        sessions.delete()
        db.commit()
        return count

    @staticmethod
    def cleanup_expired_used_refresh_tokens(db: Session) -> int:
        """
        清理过期的 refresh token 使用记录（UsedRefreshToken）

        UsedRefreshToken 用于“旧 refresh token 复用检测”，为避免表无限增长，需要定期清理。
        默认保留时间与 refresh token 生命周期一致（settings.refresh_token_expire_days）。
        """
        cutoff = datetime.now(UTC) - timedelta(days=settings.refresh_token_expire_days)
        q = db.query(UsedRefreshToken).filter(UsedRefreshToken.used_at < cutoff)
        count = q.count()
        q.delete(synchronize_session=False)
        db.commit()
        return count
