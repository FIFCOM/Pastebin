"""协作房间服务层 - 业务逻辑处理"""

import secrets
import string
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    bytes_to_str,
    generate_encryption_key,
)
from app.core.time_utils import is_expired
from app.models.collab_room import CollabRoom, Member, RoomMember, RoomPaste
from app.models.paste import Paste
from app.models.user import User
from app.schemas.collab_room import (
    MemberInfo,
    MemberTokenPayload,
    MemberTokenResponse,
    OnlineMemberInfo,
    PasteShareRequest,
    RoomCreateRequest,
    RoomCreateResponse,
    RoomInfoResponse,
    RoomJoinRequest,
    RoomJoinResponse,
    RoomMembersResponse,
    RoomPastesResponse,
    SharedPasteInfo,
    calculate_is_online,
    build_join_url,
    build_ws_url,
)
from config.config import settings


@dataclass(frozen=True)
class AuthenticatedRoomMember:
    payload: MemberTokenPayload
    member: Member
    room: CollabRoom
    membership: RoomMember


@dataclass(frozen=True)
class RoomLeaveResult:
    room_id: str
    member_id: str
    display_name: str
    room_deleted: bool
    new_owner_member_id: str | None


class CollabRoomService:
    """协作房间服务类"""

    # JWT密钥（应该从配置中获取）
    JWT_SECRET: str = settings.member_token_secret_key
    JWT_ALGORITHM: str = "HS256"
    DEFAULT_ROOM_NAME: str = "临时公共房间"

    @staticmethod
    def _generate_display_name_for_guest() -> str:
        """为游客生成显示名称"""
        # 生成6位随机字符串
        random_str = "".join(
            secrets.choice(string.ascii_lowercase + string.digits) for _ in range(6)
        )
        return f"Guest_{random_str}"

    @staticmethod
    def _generate_pin_code() -> str:
        """生成6位PIN码"""
        chars = string.ascii_uppercase + string.digits
        return "".join(secrets.choice(chars) for _ in range(6))

    @staticmethod
    def _generate_room_key() -> str:
        """生成房间加密密钥"""
        return bytes_to_str(generate_encryption_key())

    @staticmethod
    def _create_member_token(member: Member) -> str:
        """创建成员JWT令牌"""
        # 设置24小时过期
        exp = int((datetime.now(UTC) + timedelta(hours=24)).timestamp())
        member_id = str(getattr(member, "id"))
        display_name = str(getattr(member, "display_name"))
        raw_user_id = getattr(member, "user_id", None)
        user_id = int(raw_user_id) if isinstance(raw_user_id, int) else None

        payload = MemberTokenPayload(
            member_id=member_id,
            display_name=display_name,
            user_id=user_id,
            exp=exp,
        )

        return jwt.encode(
            payload.model_dump(),
            CollabRoomService.JWT_SECRET,
            algorithm=CollabRoomService.JWT_ALGORITHM,
        )

    @staticmethod
    def _verify_member_token(token: str) -> MemberTokenPayload:
        """验证成员令牌并返回载荷"""
        try:
            payload_dict = jwt.decode(
                token,
                CollabRoomService.JWT_SECRET,
                algorithms=[CollabRoomService.JWT_ALGORITHM],
            )
            return MemberTokenPayload(**payload_dict)
        except (JWTError, ValidationError) as e:
            raise ValueError(f"无效的成员令牌: {e}") from None

    @staticmethod
    def validate_member_token(token: str) -> MemberTokenPayload:
        return CollabRoomService._verify_member_token(token)

    @staticmethod
    def _get_member_by_token(
        db: Session, member_token: str
    ) -> tuple[MemberTokenPayload, Member]:
        token_payload = CollabRoomService._verify_member_token(member_token)
        member = db.query(Member).filter(Member.id == token_payload.member_id).first()
        if not member:
            raise ValueError("成员不存在")
        return token_payload, member

    @staticmethod
    def _get_room(db: Session, room_id: str) -> CollabRoom:
        room = db.query(CollabRoom).filter(CollabRoom.id == room_id).first()
        if not room:
            raise ValueError("房间不存在")
        return room

    @staticmethod
    def _get_ordered_room_members(db: Session, room_id: str):
        return (
            db.query(RoomMember, Member)
            .join(Member, RoomMember.member_id == Member.id)
            .filter(RoomMember.room_id == room_id)
            .order_by(RoomMember.joined_at.asc(), RoomMember.id.asc())
        )

    @staticmethod
    def _get_next_owner_membership(
        db: Session, room_id: str, *, excluded_member_ids: set[str]
    ) -> RoomMember | None:
        query = db.query(RoomMember).filter(RoomMember.room_id == room_id)
        if excluded_member_ids:
            query = query.filter(~RoomMember.member_id.in_(excluded_member_ids))
        return query.order_by(RoomMember.joined_at.asc(), RoomMember.id.asc()).first()

    @staticmethod
    def get_room_member_context(
        db: Session, member_token: str, room_id: str
    ) -> AuthenticatedRoomMember:
        token_payload, member = CollabRoomService._get_member_by_token(db, member_token)
        room = CollabRoomService._get_room(db, room_id)
        membership = (
            db.query(RoomMember)
            .filter(
                and_(
                    RoomMember.room_id == room_id,
                    RoomMember.member_id == token_payload.member_id,
                )
            )
            .first()
        )
        if not membership:
            raise ValueError("您不在此房间中")
        return AuthenticatedRoomMember(
            payload=token_payload,
            member=member,
            room=room,
            membership=membership,
        )

    @staticmethod
    def touch_room_presence(
        db: Session, room_id: str, member_id: str
    ) -> datetime | None:
        membership = (
            db.query(RoomMember)
            .filter(
                and_(
                    RoomMember.room_id == room_id,
                    RoomMember.member_id == member_id,
                )
            )
            .first()
        )
        if not membership:
            return None

        now = datetime.now(UTC)
        setattr(membership, "last_seen", now)
        db.commit()
        return now

    @staticmethod
    def has_active_room_membership(db: Session, room_id: str, member_id: str) -> bool:
        now = datetime.now(UTC)
        membership = (
            db.query(RoomMember)
            .join(Member, RoomMember.member_id == Member.id)
            .filter(
                and_(
                    RoomMember.room_id == room_id,
                    RoomMember.member_id == member_id,
                    Member.expire_at >= now,
                )
            )
            .first()
        )
        return membership is not None

    @staticmethod
    def _sync_room_member_count(db: Session, room_id: str) -> int:
        """将 collab_rooms.member_count 同步为 room_members 的真实数量，并返回最新值。"""
        count = db.query(RoomMember).filter(RoomMember.room_id == room_id).count()
        room = db.query(CollabRoom).filter(CollabRoom.id == room_id).first()
        if room:
            setattr(room, "member_count", int(count))
        return int(count)

    @staticmethod
    def get_member_token(
        db: Session, user_id: int | None = None
    ) -> MemberTokenResponse:
        """
        获取成员令牌（不必登录）

        Args:
            db: 数据库会话
            user_id: 用户ID（可选，如果提供则为已登录用户）

        Returns:
            成员令牌响应
        """
        # 设置24小时过期
        expire_at = datetime.now(UTC) + timedelta(hours=24)

        if user_id:
            # 已登录用户
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("用户不存在")

            display_name = str(user.username)  # type: ignore

            # 创建成员记录
            member = Member(
                user_id=user_id,
                display_name=display_name,
                expire_at=expire_at,
            )
        else:
            # 游客用户
            display_name = CollabRoomService._generate_display_name_for_guest()

            # 创建成员记录
            member = Member(
                user_id=None,
                display_name=display_name,
                expire_at=expire_at,
            )

        db.add(member)
        db.commit()
        db.refresh(member)

        # 生成JWT令牌
        token = CollabRoomService._create_member_token(member)

        return MemberTokenResponse(
            member_token=token,
            display_name=display_name,
        )

    @staticmethod
    def create_room(
        db: Session, member_token: str, room_data: RoomCreateRequest
    ) -> RoomCreateResponse:
        """
        创建协作房间

        Args:
            db: 数据库会话
            member_token: 成员令牌
            room_data: 房间创建数据

        Returns:
            房间创建响应
        """
        # 验证成员令牌
        token_payload = CollabRoomService._verify_member_token(member_token)

        # 获取成员记录
        member = db.query(Member).filter(Member.id == token_payload.member_id).first()
        if not member:
            raise ValueError("成员不存在")

        # 生成唯一的PIN码（并处理并发下的唯一约束竞态）
        max_attempts = 10
        last_error: Exception | None = None
        for _ in range(max_attempts):
            pin_code = CollabRoomService._generate_pin_code()
            room_key = CollabRoomService._generate_room_key()

            room = CollabRoom(
                creator_member_id=str(member.id),  # type: ignore
                room_name=CollabRoomService.DEFAULT_ROOM_NAME,
                pin_code=pin_code,
                room_key=room_key,
                max_members=settings.collab_room_max_members,
                member_count=1,
            )
            db.add(room)

            try:
                db.flush()  # 获取room.id + 触发 pin_code 唯一性校验
            except IntegrityError as e:
                db.rollback()
                last_error = e
                continue

            room_member = RoomMember(
                room_id=str(room.id),  # type: ignore
                member_id=str(member.id),  # type: ignore
            )
            db.add(room_member)

            try:
                db.commit()
            except IntegrityError as e:
                db.rollback()
                last_error = e
                continue

            db.refresh(room)
            return RoomCreateResponse(
                room_id=str(room.id),  # type: ignore
                room_name=str(room.room_name),  # type: ignore
                pin_code=pin_code,
                join_url=build_join_url(pin_code),
                max_members=int(room.max_members),  # type: ignore[arg-type]
            )

        raise ValueError(f"无法生成唯一的PIN码: {last_error}")

    @staticmethod
    def get_room_info_by_pin(db: Session, pin_code: str) -> RoomInfoResponse:
        """
        通过PIN码获取房间信息

        Args:
            db: 数据库会话
            pin_code: PIN码

        Returns:
            房间信息响应
        """
        room = (
            db.query(CollabRoom).filter(CollabRoom.pin_code == pin_code.upper()).first()
        )
        if not room:
            raise ValueError("房间不存在")

        # 避免 member_count 漂移：按真实 room_members 数量返回
        member_count = (
            db.query(RoomMember).filter(RoomMember.room_id == str(room.id)).count()  # type: ignore
        )
        return RoomInfoResponse(
            room_id=str(room.id),  # type: ignore
            room_name=str(room.room_name),  # type: ignore
            member_count=int(member_count),
            max_members=int(
                getattr(room, "max_members", 10)
                if getattr(room, "max_members", 10) is not None
                else 10
            ),
        )

    @staticmethod
    def join_room(
        db: Session, member_token: str, room_id: str, join_data: RoomJoinRequest
    ) -> RoomJoinResponse:
        """
        加入房间

        Args:
            db: 数据库会话
            member_token: 成员令牌
            room_id: 房间ID
            join_data: 加入请求数据

        Returns:
            加入房间响应
        """
        _, member = CollabRoomService._get_member_by_token(db, member_token)

        # 获取房间
        room = (
            db.query(CollabRoom)
            .filter(
                and_(
                    CollabRoom.id == room_id,
                    CollabRoom.pin_code == join_data.pin_code.upper(),
                )
            )
            .first()
        )
        if not room:
            raise ValueError("房间不存在或PIN码错误")

        # 检查是否已经在房间中
        existing_membership = (
            db.query(RoomMember)
            .filter(
                and_(
                    RoomMember.room_id == room_id,
                    RoomMember.member_id == str(member.id),  # type: ignore
                )
            )
            .first()
        )

        if existing_membership:
            setattr(existing_membership, "last_seen", datetime.now(UTC))
            db.commit()
        else:
            reserved_slots = (
                db.query(CollabRoom)
                .filter(
                    and_(
                        CollabRoom.id == room_id,
                        CollabRoom.member_count < CollabRoom.max_members,
                    )
                )
                .update(
                    {CollabRoom.member_count: CollabRoom.member_count + 1},
                    synchronize_session=False,
                )
            )
            if reserved_slots == 0:
                raise ValueError("房间已满")

            room_member = RoomMember(
                room_id=room_id,
                member_id=str(member.id),  # type: ignore
            )
            db.add(room_member)

            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                # 可能并发重复加入：当作已在房间中
                existing_membership = (
                    db.query(RoomMember)
                    .filter(
                        and_(
                            RoomMember.room_id == room_id,
                            RoomMember.member_id == str(member.id),  # type: ignore
                        )
                    )
                    .first()
                )
                if not existing_membership:
                    raise
                setattr(existing_membership, "last_seen", datetime.now(UTC))
                db.commit()

        # 获取房间成员列表
        room_members = CollabRoomService._get_ordered_room_members(db, room_id).all()

        member_infos = [
            MemberInfo(
                id=str(member_record.id),  # type: ignore
                display_name=str(member_record.display_name),  # type: ignore
                joined_at=room_member_record.joined_at,  # type: ignore
            )
            for room_member_record, member_record in room_members
        ]

        return RoomJoinResponse(
            room_key=str(room.room_key),  # type: ignore
            members=member_infos,
            ws_url=build_ws_url(room_id),
        )

    @staticmethod
    def get_room_members(
        db: Session,
        member_token: str,
        room_id: str,
        active_member_ids: set[str] | None = None,
    ) -> RoomMembersResponse:
        """
        获取房间成员列表

        Args:
            db: 数据库会话
            member_token: 成员令牌
            room_id: 房间ID

        Returns:
            房间成员列表响应
        """
        CollabRoomService.get_room_member_context(db, member_token, room_id)
        room_members = CollabRoomService._get_ordered_room_members(db, room_id).all()
        active_ids = active_member_ids or set()

        member_infos = []
        for room_member_record, member_record in room_members:
            last_seen = room_member_record.last_seen  # type: ignore
            member_id = str(member_record.id)  # type: ignore
            is_online = member_id in active_ids or calculate_is_online(last_seen)

            member_infos.append(
                OnlineMemberInfo(
                    member_id=member_id,
                    display_name=str(member_record.display_name),  # type: ignore
                    last_seen=last_seen,
                    is_online=is_online,
                    joined_at=room_member_record.joined_at,  # type: ignore
                )
            )

        return RoomMembersResponse(members=member_infos)

    @staticmethod
    def share_paste_to_room(
        db: Session, member_token: str, room_id: str, share_data: PasteShareRequest
    ) -> SharedPasteInfo:
        """
        分享Paste到房间

        Args:
            db: 数据库会话
            member_token: 成员令牌
            room_id: 房间ID
            share_data: 分享数据
        """
        context = CollabRoomService.get_room_member_context(db, member_token, room_id)

        # 验证Paste是否存在
        paste = db.query(Paste).filter(Paste.id == share_data.paste_id).first()
        if not paste:
            raise ValueError("Paste不存在")
        if str(paste.status) == "draft":  # type: ignore
            raise ValueError("草稿状态的Paste不可分享")

        # 防止绕过 Paste 的 access_key 保护：设置了访问密钥的 Paste 不允许通过房间分享
        access_key_hash = getattr(paste, "access_key_hash", None)
        if access_key_hash is not None:
            raise ValueError("该Paste设置了访问密钥，不能通过协作房间分享")

        # 过期 Paste 不允许分享
        paste_expire_at = cast(datetime | None, getattr(paste, "expire_at", None))
        if is_expired(paste_expire_at):
            raise ValueError("Paste已过期，不能分享")

        # 如果指定了目标成员，验证目标成员是否在房间中
        if share_data.target_member_id:
            target_membership = (
                db.query(RoomMember)
                .filter(
                    and_(
                        RoomMember.room_id == room_id,
                        RoomMember.member_id == share_data.target_member_id,
                    )
                )
                .first()
            )

            if not target_membership:
                raise ValueError("目标成员不在此房间中")

        # 创建分享记录
        room_paste = RoomPaste(
            room_id=room_id,
            paste_id=share_data.paste_id,
            shared_by_member_id=context.payload.member_id,
            target_member_id=share_data.target_member_id,
            encrypted_paste_key=share_data.encrypted_paste_key,
        )

        db.add(room_paste)
        db.commit()
        db.refresh(room_paste)
        target_member_id = room_paste.target_member_id
        paste_title = getattr(paste, "title", None)
        shared_at = cast(datetime, getattr(room_paste, "shared_at"))

        return SharedPasteInfo(
            paste_id=str(room_paste.paste_id),  # type: ignore
            title=str(paste_title) if paste_title is not None else None,
            encrypted_paste_key=str(room_paste.encrypted_paste_key),  # type: ignore
            shared_by=str(room_paste.shared_by_member_id),  # type: ignore
            target_member=str(target_member_id)
            if target_member_id is not None
            else None,
            shared_at=shared_at,
            expire_at=paste_expire_at,
            is_expired=False,
        )

    @staticmethod
    def get_room_pastes(
        db: Session, member_token: str, room_id: str, paste_type: str = "received"
    ) -> RoomPastesResponse:
        """
        获取房间内的Paste

        Args:
            db: 数据库会话
            member_token: 成员令牌
            room_id: 房间ID
            paste_type: received|sent|all，默认received

        Returns:
            房间Paste列表响应
        """
        context = CollabRoomService.get_room_member_context(db, member_token, room_id)

        # 构建查询条件
        query = (
            db.query(RoomPaste, Paste)
            .join(Paste, RoomPaste.paste_id == Paste.id)
            .filter(RoomPaste.room_id == room_id)
        )

        if paste_type == "received":
            query = query.filter(
                or_(
                    RoomPaste.target_member_id == context.payload.member_id,
                    RoomPaste.target_member_id.is_(None),
                )
            )
        elif paste_type == "sent":
            query = query.filter(
                RoomPaste.shared_by_member_id == context.payload.member_id
            )
        elif paste_type == "all":
            # “all” 仅表示与当前成员相关（收到的 + 自己发出的），不包含他人之间的定向分享
            query = query.filter(
                or_(
                    RoomPaste.shared_by_member_id == context.payload.member_id,
                    RoomPaste.target_member_id == context.payload.member_id,
                    RoomPaste.target_member_id.is_(None),
                )
            )

        room_pastes = query.order_by(RoomPaste.shared_at.desc()).all()

        paste_infos = []
        for room_paste_record, paste_record in room_pastes:
            expire_at = cast(datetime | None, getattr(paste_record, "expire_at", None))
            paste_is_expired = is_expired(expire_at)
            target_member_id = room_paste_record.target_member_id
            paste_title = getattr(paste_record, "title", None)
            shared_at = cast(datetime, getattr(room_paste_record, "shared_at"))
            paste_infos.append(
                SharedPasteInfo(
                    paste_id=str(room_paste_record.paste_id),  # type: ignore
                    title=str(paste_title) if paste_title is not None else None,
                    encrypted_paste_key=str(room_paste_record.encrypted_paste_key),  # type: ignore
                    shared_by=str(room_paste_record.shared_by_member_id),  # type: ignore
                    target_member=(
                        str(target_member_id) if target_member_id is not None else None
                    ),
                    shared_at=shared_at,
                    expire_at=expire_at,
                    is_expired=paste_is_expired,
                )
            )

        return RoomPastesResponse(pastes=paste_infos)

    @staticmethod
    def leave_room(db: Session, member_token: str, room_id: str) -> RoomLeaveResult:
        """
        离开房间

        Args:
            db: 数据库会话
            member_token: 成员令牌
            room_id: 房间ID
        """
        context = CollabRoomService.get_room_member_context(db, member_token, room_id)
        room = context.room
        member = context.member
        membership = context.membership
        member_id = str(member.id)  # type: ignore
        room_owner_id = str(room.creator_member_id)  # type: ignore
        next_owner = None

        if room_owner_id == member_id:
            next_owner = CollabRoomService._get_next_owner_membership(
                db,
                room_id,
                excluded_member_ids={member_id},
            )
            if next_owner:
                setattr(room, "creator_member_id", str(next_owner.member_id))

        db.delete(membership)
        db.flush()

        remaining_members = CollabRoomService._sync_room_member_count(db, room_id)
        room_deleted = remaining_members == 0
        if room_deleted:
            db.delete(room)

        db.commit()
        return RoomLeaveResult(
            room_id=room_id,
            member_id=member_id,
            display_name=str(member.display_name),  # type: ignore
            room_deleted=room_deleted,
            new_owner_member_id=(
                str(next_owner.member_id) if next_owner and not room_deleted else None
            ),
        )

    @staticmethod
    def update_member_last_seen(db: Session, member_token: str, room_id: str) -> None:
        """
        更新成员最后活跃时间

        Args:
            db: 数据库会话
            member_token: 成员令牌
            room_id: 房间ID
        """
        token_payload = CollabRoomService._verify_member_token(member_token)
        CollabRoomService.touch_room_presence(db, room_id, token_payload.member_id)
