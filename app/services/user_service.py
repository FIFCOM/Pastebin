"""
用户服务层 - 业务逻辑处理
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, or_
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
    wrap_user_key_for_password,
)
from app.core.time_utils import coerce_utc, is_expired
from app.models.user import UsedRefreshToken, User, UserSession, UserSessionKey
from app.models.user_favorite import UserFavorite
from app.models.user_history import UserHistory
from app.schemas.user import (
    LoginResponse,
    PasswordResetRequest,
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
from app.services.email_settings_service import EmailSettingsService
from app.services.email_verification_service import EmailVerificationService
from config.config import settings


class UserService:
    """用户服务类"""

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def _find_user_by_email(db: Session, email: str) -> User | None:
        return (
            db.query(User)
            .filter(func.lower(User.email) == UserService._normalize_email(email))
            .first()
        )

    @staticmethod
    def _is_user_active(user: User) -> bool:
        return bool(user.is_active)

    @staticmethod
    def _create_login_session(
        db: Session,
        user: User,
        user_key: bytes,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, str]:
        refresh_token = generate_refresh_token()
        refresh_token_hash = hash_refresh_token(refresh_token)
        session_key = generate_session_key()

        encrypted_user_key_for_session = encrypt_with_key(user_key, session_key)
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=settings.refresh_token_expire_days)

        session = UserSession(
            user_id=user.id,  # type: ignore[arg-type]
            session_token=refresh_token_hash,
            encrypted_session_key=bytes_to_str(encrypted_user_key_for_session),
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
            last_active_at=now,
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
                "uid": user.id,
                "session_id": session.id,
                "type": "access",
            }
        )
        return access_token, refresh_token

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
        normalized_email = UserService._normalize_email(str(user_data.email))

        # 检查邮箱是否已存在
        existing_user = UserService._find_user_by_email(db, normalized_email)
        if existing_user:
            raise ValueError("邮箱已存在")

        now = datetime.now(UTC)
        email_verification_enabled = EmailSettingsService.is_enabled(db)
        if email_verification_enabled:
            if not user_data.verification_code:
                raise ValueError("请先验证邮箱")
            EmailVerificationService.consume_code(
                db,
                email=normalized_email,
                purpose="register",
                code=user_data.verification_code,
                user_id=None,
            )

        # 生成用户名
        while True:
            username = generate_username()
            if not db.query(User).filter(User.username == username).first():
                break

        # 准备用户密钥
        salt, _encryption_key, encrypted_user_key = prepare_user_keys(
            user_data.password
        )

        # 使用bcrypt哈希密码
        password_hash = hash_password(user_data.password)

        # 创建用户
        user = User(
            username=username,
            email=normalized_email,
            password_hash=password_hash,
            salt=bytes_to_str(salt),
            encrypted_user_key=bytes_to_str(encrypted_user_key),
            email_verified_at=now if email_verification_enabled else None,
            role="user",
            is_active=True,
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
        - 当前登录使用邮箱认证

        Args:
            db: 数据库会话
            login_data: 登录数据

        Returns:
            认证成功的用户或None
        """
        user = UserService._find_user_by_email(db, str(login_data.email))
        if not user:
            return None

        if not UserService._is_user_active(user):
            return None

        if not verify_password(login_data.password, user.password_hash):  # type: ignore
            return None

        return user

    @staticmethod
    def login_user(
        db: Session,
        login_data: UserLoginRequest,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[LoginResponse, str]:
        """
        用户登录

        Args:
            db: 数据库会话
            login_data: 登录数据

        Returns:
            登录响应（access token 和用户信息）以及 refresh token

        Raises:
            ValueError: 当用户名或密码错误，或需要TOTP验证时
        """
        user = UserService.authenticate_user(db, login_data)
        if not user:
            existing_user = (
                UserService._find_user_by_email(db, str(login_data.email))
            )
            if existing_user and not UserService._is_user_active(existing_user):
                raise ValueError("账户已被禁用")
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

        access_token, refresh_token = UserService._create_login_session(
            db,
            user,
            user_key,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        return (
            LoginResponse(
                access_token=access_token,
                token_type="bearer",
                user=UserResponse.model_validate(user),  # type: ignore
            ),
            refresh_token,
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
        user = UserService._find_user_by_email(db, email)
        return UserResponse.model_validate(user) if user else None  # type: ignore

    @staticmethod
    def update_user(
        db: Session,
        user_id: int,
        user_data: UserUpdateRequest,
        *,
        actor_user_id: int,
        actor_is_admin: bool = False,
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
            ValueError: 当用户不存在，或用户名/邮箱已被占用时
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("用户不存在")

        actor = db.query(User).filter(User.id == actor_user_id).first()
        if actor is None:
            raise ValueError("操作者不存在")

        is_self = actor_user_id == user_id
        if not is_self and not actor_is_admin:
            raise ValueError("无权限修改其他用户信息")

        if not actor_is_admin and (
            user_data.role is not None or user_data.is_active is not None
        ):
            raise ValueError("无权限修改角色或状态")

        if actor_is_admin and not is_self and user_data.password:
            raise ValueError("管理员不能重置用户密码")

        next_username: str | None = None
        if user_data.username is not None:
            next_username = user_data.username.strip()
            if not next_username:
                raise ValueError("用户名不能为空")

        email_was_provided = "email" in user_data.model_fields_set
        next_email: str | None = None
        if email_was_provided:
            if user_data.email is None:
                raise ValueError("邮箱不能为空")
            next_email = UserService._normalize_email(str(user_data.email))
            if not next_email:
                raise ValueError("邮箱不能为空")

        wants_email_or_password_change = (
            email_was_provided and next_email != user.email
        ) or bool(user_data.password)
        current_password_verified = False
        if is_self and wants_email_or_password_change:
            if not user_data.current_password:
                raise ValueError("修改邮箱或密码需要输入当前密码")
            if not verify_password(user_data.current_password, str(user.password_hash)):  # type: ignore[arg-type]
                raise ValueError("当前密码错误")
            current_password_verified = True

        if next_username is not None and next_username != user.username:
            existing_user = (
                db.query(User)
                .filter(and_(User.username == next_username, User.id != user_id))
                .first()
            )
            if existing_user:
                raise ValueError("用户名已存在")
            user.username = next_username  # type: ignore[assignment]

        if email_was_provided and next_email != user.email:
            existing_user = UserService._find_user_by_email(db, next_email)
            if existing_user:
                if int(existing_user.id) != user_id:  # type: ignore[arg-type]
                    raise ValueError("邮箱已被其他用户使用")
            email_verified = actor_is_admin
            if is_self and EmailSettingsService.is_enabled(db):
                if not user_data.email_verification_code:
                    raise ValueError("请先验证新邮箱")
                EmailVerificationService.consume_code(
                    db,
                    email=next_email,
                    purpose="change_email",
                    code=user_data.email_verification_code,
                    user_id=user_id,
                )
                email_verified = True
            user.email = next_email  # type: ignore[assignment]
            user.email_verified_at = (
                datetime.now(UTC) if email_verified else None
            )  # type: ignore[assignment]

        if user_data.password:
            if is_self and current_password_verified and user_data.current_password:
                try:
                    current_salt = str_to_bytes(str(user.salt))
                    current_encrypted_user_key = str_to_bytes(
                        str(user.encrypted_user_key)
                    )
                    user_key = recover_user_key(
                        user_data.current_password,
                        current_salt,
                        current_encrypted_user_key,
                    )
                    salt, encrypted_user_key = wrap_user_key_for_password(
                        user_data.password, user_key
                    )
                except Exception as e:
                    raise ValueError(f"用户密钥重加密失败: {str(e)}") from e
            else:
                salt, _encryption_key, encrypted_user_key = prepare_user_keys(
                    user_data.password
                )
            password_hash = hash_password(user_data.password)

            user.password_hash = password_hash  # type: ignore[assignment]
            user.salt = bytes_to_str(salt)  # type: ignore[assignment]
            user.encrypted_user_key = bytes_to_str(encrypted_user_key)  # type: ignore[assignment]

        if actor_is_admin and user_data.role is not None:
            if user.role == "admin" and user_data.role != "admin":
                other_admin = (
                    db.query(User)
                    .filter(User.role == "admin", User.id != user_id)
                    .first()
                )
                if other_admin is None:
                    raise ValueError("系统至少需要保留一个管理员")
            user.role = user_data.role  # type: ignore[assignment]

        if actor_is_admin and user_data.is_active is not None:
            if actor_user_id == user_id and not user_data.is_active:
                raise ValueError("不能禁用当前登录账户")
            user.is_active = user_data.is_active  # type: ignore[assignment]

        db.commit()
        db.refresh(user)

        return UserResponse.model_validate(user)  # type: ignore

    @staticmethod
    def delete_user(
        db: Session,
        user_id: int,
        *,
        actor_user_id: int,
        actor_is_admin: bool = False,
    ) -> bool:
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

        if not actor_is_admin and actor_user_id != user_id:
            raise ValueError("无权限删除其他用户")

        if user.role == "admin":
            other_admin = (
                db.query(User).filter(User.role == "admin", User.id != user_id).first()
            )
            if other_admin is None:
                raise ValueError("系统至少需要保留一个管理员")

        db.delete(user)
        db.commit()
        return True

    @staticmethod
    def list_users(
        db: Session,
        page: int = 1,
        size: int = 10,
        *,
        search: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> UserListResponse:
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

        users_query = db.query(User)
        search_text = (search or "").strip()
        if search_text:
            q = f"%{search_text}%"
            users_query = users_query.filter(
                or_(User.username.ilike(q), User.email.ilike(q))  # type: ignore[arg-type]
            )
        if role in {"admin", "user"}:
            users_query = users_query.filter(User.role == role)
        if is_active is not None:
            users_query = users_query.filter(User.is_active == is_active)

        total = users_query.count()
        users = (
            users_query.order_by(User.created_at.desc(), User.id.desc())
            .offset(offset)
            .limit(size)
            .all()
        )

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

        normalized_email = UserService._normalize_email(str(user_data.email))

        # 检查邮箱
        existing_user = UserService._find_user_by_email(db, normalized_email)
        if existing_user:
            raise ValueError("邮箱已存在")

        # 准备用户密钥
        salt, _encryption_key, encrypted_user_key = prepare_user_keys(
            user_data.password
        )
        password_hash = hash_password(user_data.password)

        # 创建用户
        user = User(
            username=username,
            email=normalized_email,
            password_hash=password_hash,  # type: ignore
            salt=bytes_to_str(salt),  # type: ignore
            encrypted_user_key=bytes_to_str(encrypted_user_key),  # type: ignore
            email_verified_at=datetime.now(UTC),
            role=user_data.role,
            is_active=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return UserResponse.model_validate(user)  # type: ignore

    @staticmethod
    def reset_password(
        db: Session, reset_data: PasswordResetRequest
    ) -> UserResponse:
        """
        通过邮箱验证码重置密码。

        忘记密码时无法恢复旧 user_key，因此重置会生成新的用户密钥，
        并清空依赖旧 user_key 的用户历史和收藏关联。
        """
        if not EmailSettingsService.is_enabled(db):
            raise ValueError("邮箱验证码功能未启用")

        normalized_email = UserService._normalize_email(str(reset_data.email))
        user = UserService._find_user_by_email(db, normalized_email)
        if not user:
            raise ValueError("验证码无效或已过期")
        if not UserService._is_user_active(user):
            raise ValueError("账户已被禁用")

        EmailVerificationService.consume_code(
            db,
            email=normalized_email,
            purpose="reset_password",
            code=reset_data.verification_code,
            user_id=None,
        )

        salt, _encryption_key, encrypted_user_key = prepare_user_keys(
            reset_data.password
        )
        user.password_hash = hash_password(reset_data.password)  # type: ignore[assignment]
        user.salt = bytes_to_str(salt)  # type: ignore[assignment]
        user.encrypted_user_key = bytes_to_str(encrypted_user_key)  # type: ignore[assignment]
        user.email_verified_at = datetime.now(UTC)  # type: ignore[assignment]

        db.query(UserHistory).filter(UserHistory.user_id == user.id).delete(
            synchronize_session=False
        )
        db.query(UserFavorite).filter(UserFavorite.user_id == user.id).delete(
            synchronize_session=False
        )
        db.query(UserSession).filter(UserSession.user_id == user.id).delete(
            synchronize_session=False
        )

        db.commit()
        db.refresh(user)
        return UserResponse.model_validate(user)  # type: ignore

    @staticmethod
    def get_user_sessions(
        db: Session, user_id: int, *, current_session_id: str | None = None
    ) -> list[SessionResponse]:
        """获取用户的所有会话"""
        sessions = (
            db.query(UserSession)
            .filter(UserSession.user_id == user_id)
            .order_by(UserSession.last_active_at.desc(), UserSession.created_at.desc())
            .all()
        )
        return [
            SessionResponse(
                id=str(session.id),
                user_id=int(session.user_id),  # type: ignore[arg-type]
                expires_at=session.expires_at,  # type: ignore[arg-type]
                created_at=session.created_at,  # type: ignore[arg-type]
                user_agent=session.user_agent,  # type: ignore[arg-type]
                ip_address=session.ip_address,  # type: ignore[arg-type]
                last_active_at=session.last_active_at,  # type: ignore[arg-type]
                is_current=current_session_id is not None
                and str(session.id) == current_session_id,
            )
            for session in sessions
        ]

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
    def revoke_other_sessions(
        db: Session, user_id: int, current_session_id: str
    ) -> int:
        sessions = db.query(UserSession).filter(
            UserSession.user_id == user_id, UserSession.id != current_session_id
        )
        count = sessions.count()
        sessions.delete(synchronize_session=False)
        db.commit()
        return count

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
            totp_secret,
            user.username,  # type: ignore[arg-type]
        )

        db.commit()

        return TotpSetupResponse(secret=totp_secret, provisioning_uri=provisioning_uri)  # type: ignore[assignment]

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
            user.totp_pending_secret,
            totp_data.totp_code,  # type: ignore[arg-type]
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
        user = UserService._find_user_by_email(db, str(login_data.email))
        if not user:
            return None

        if not UserService._is_user_active(user):
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
        db: Session,
        login_data: UserLoginWithTotpRequest,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[LoginResponse, str]:
        """
        用户登录（包含TOTP验证）

        Args:
            db: 数据库会话
            login_data: 登录数据（包含TOTP代码）

        Returns:
            登录响应（access token 和用户信息）以及 refresh token

        Raises:
            ValueError: 当用户名、密码或TOTP代码错误时
        """
        user = UserService.authenticate_user_with_totp(db, login_data)
        if not user:
            existing_user = UserService._find_user_by_email(db, str(login_data.email))
            if existing_user and not UserService._is_user_active(existing_user):
                raise ValueError("账户已被禁用")
            raise ValueError("邮箱、密码或TOTP代码错误")

        # 恢复用户密钥
        try:
            salt = str_to_bytes(user.salt)  # type: ignore
            encrypted_user_key = str_to_bytes(user.encrypted_user_key)  # type: ignore
            user_key = recover_user_key(login_data.password, salt, encrypted_user_key)
        except Exception as e:
            raise ValueError(f"密钥恢复失败: {str(e)}") from e

        access_token, refresh_token = UserService._create_login_session(
            db,
            user,
            user_key,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        return (
            LoginResponse(
                access_token=access_token,
                token_type="bearer",
                user=UserResponse.model_validate(user),
            ),
            refresh_token,
        )

    @staticmethod
    def refresh_access_token(
        db: Session,
        refresh_token: str,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, str]:
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
                    db.query(UserSession)
                    .filter(UserSession.id == reused.session_id)
                    .first()
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

        if not UserService._is_user_active(user):
            db.delete(session)
            db.commit()
            raise ValueError("账户已被禁用")

        now = datetime.now(UTC)
        new_refresh_token = generate_refresh_token()
        new_refresh_token_hash = hash_refresh_token(new_refresh_token)
        new_expires_at = now + timedelta(days=settings.refresh_token_expire_days)

        # 通过条件更新实现原子旋转，避免高并发下出现“两个新 refresh token 都返回但只有一个有效”的问题
        try:
            update_data = {
                UserSession.session_token: new_refresh_token_hash,
                UserSession.expires_at: new_expires_at,
                UserSession.last_active_at: now,
            }
            if user_agent is not None:
                update_data[UserSession.user_agent] = user_agent
            if ip_address is not None:
                update_data[UserSession.ip_address] = ip_address

            updated = (
                db.query(UserSession)
                .filter(
                    UserSession.id == session.id,
                    UserSession.session_token == old_refresh_token_hash,
                )
                .update(update_data, synchronize_session=False)
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
            raise ValueError(
                "检测到 refresh token 复用，已撤销会话，请重新登录"
            ) from None

        access_token = create_access_token(
            data={
                "uid": user.id,
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
            db.query(UserSession)
            .filter(UserSession.session_token == refresh_token_hash)
            .first()
        )
        if session is None:
            return False
        db.delete(session)
        db.commit()
        return True

    @staticmethod
    def logout_all_sessions(
        db: Session, user_id: int, *, exclude_session_id: str | None = None
    ) -> int:
        """撤销用户的全部会话（可选保留当前会话）"""
        sessions = db.query(UserSession).filter(UserSession.user_id == user_id)
        if exclude_session_id:
            sessions = sessions.filter(UserSession.id != exclude_session_id)
        count = sessions.count()
        sessions.delete(synchronize_session=False)
        db.commit()
        return count

    @staticmethod
    def touch_session_activity(
        db: Session,
        session_id: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
        min_update_interval_seconds: int = 60,
    ) -> None:
        session = db.query(UserSession).filter(UserSession.id == session_id).first()
        if session is None:
            return

        now = datetime.now(UTC)
        last_active = session.last_active_at or session.created_at  # type: ignore[arg-type]
        if last_active is not None:
            elapsed = (coerce_utc(now) - coerce_utc(last_active)).total_seconds()
            should_skip = (
                elapsed < min_update_interval_seconds
                and (ip_address is None or session.ip_address == ip_address)
                and (user_agent is None or session.user_agent == user_agent)
            )
            if should_skip:
                return

        session.last_active_at = now  # type: ignore[assignment]
        if ip_address is not None:
            session.ip_address = ip_address  # type: ignore[assignment]
        if user_agent is not None:
            session.user_agent = user_agent  # type: ignore[assignment]
        db.commit()

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
