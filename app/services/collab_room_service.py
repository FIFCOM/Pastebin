"""
协作房间服务层 - 业务逻辑处理
"""

import secrets
import string
from datetime import datetime, timedelta

import jwt
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.security import (
    bytes_to_str,
    generate_encryption_key,
)
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
    build_join_url,
    build_ws_url,
    calculate_is_online,
)
from config.config import settings


class CollabRoomService:
    """协作房间服务类"""

    # JWT密钥（应该从配置中获取）
    JWT_SECRET = settings.secret_key
    JWT_ALGORITHM = "HS256"

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
        exp = int((datetime.utcnow() + timedelta(hours=24)).timestamp())

        payload = MemberTokenPayload(
            member_id=str(member.id),  # type: ignore
            display_name=str(member.display_name),  # type: ignore
            user_id=member.user_id,  # type: ignore
            exp=exp,
        )

        return jwt.encode(
            payload.dict(),
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
        except jwt.InvalidTokenError as e:
            raise ValueError(f"无效的成员令牌: {e}") from None

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
        expire_at = datetime.utcnow() + timedelta(hours=24)

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

        # 生成唯一的PIN码
        max_attempts = 10
        for _ in range(max_attempts):
            pin_code = CollabRoomService._generate_pin_code()
            if not db.query(CollabRoom).filter(CollabRoom.pin_code == pin_code).first():
                break
        else:
            raise ValueError("无法生成唯一的PIN码")

        # 生成房间密钥
        room_key = CollabRoomService._generate_room_key()

        # 创建房间
        room = CollabRoom(
            creator_member_id=str(member.id),  # type: ignore
            room_name=room_data.room_name,
            pin_code=pin_code,
            room_key=room_key,
            max_members=room_data.max_members,
            member_count=1,
        )

        db.add(room)
        db.flush()  # 获取room.id

        # 将创建者加入房间
        room_member = RoomMember(
            room_id=str(room.id),  # type: ignore
            member_id=str(member.id),  # type: ignore
        )
        db.add(room_member)

        db.commit()
        db.refresh(room)

        return RoomCreateResponse(
            room_id=str(room.id),  # type: ignore
            pin_code=pin_code,
            join_url=build_join_url(pin_code),
        )

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

        return RoomInfoResponse(
            room_id=str(room.id),  # type: ignore
            room_name=str(room.room_name),  # type: ignore
            member_count=int(room.member_count or 0),  # type: ignore
            max_members=int(room.max_members or 10),  # type: ignore
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
        # 验证成员令牌
        token_payload = CollabRoomService._verify_member_token(member_token)

        # 获取成员记录
        member = db.query(Member).filter(Member.id == token_payload.member_id).first()
        if not member:
            raise ValueError("成员不存在")

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
            # 更新最后活跃时间
            existing_membership.last_seen = datetime.utcnow()  # type: ignore
        else:
            # 检查房间是否已满
            current_count = int(room.member_count or 0)  # type: ignore
            max_count = int(room.max_members or 10)  # type: ignore

            if current_count >= max_count:
                raise ValueError("房间已满")

            # 创建新的成员关系
            room_member = RoomMember(
                room_id=room_id,
                member_id=str(member.id),  # type: ignore
            )
            db.add(room_member)

            # 更新房间成员数
            room.member_count = current_count + 1  # type: ignore

        db.commit()

        # 获取房间成员列表
        room_members = (
            db.query(RoomMember, Member)
            .join(Member, RoomMember.member_id == Member.id)
            .filter(RoomMember.room_id == room_id)
            .all()
        )

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
        db: Session, member_token: str, room_id: str
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
        # 验证成员令牌
        token_payload = CollabRoomService._verify_member_token(member_token)

        # 验证成员是否在房间中
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

        # 获取房间成员列表
        room_members = (
            db.query(RoomMember, Member)
            .join(Member, RoomMember.member_id == Member.id)
            .filter(RoomMember.room_id == room_id)
            .all()
        )

        member_infos = []
        for room_member_record, member_record in room_members:
            last_seen = room_member_record.last_seen  # type: ignore
            is_online = calculate_is_online(last_seen)

            member_infos.append(
                OnlineMemberInfo(
                    member_id=str(member_record.id),  # type: ignore
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
    ) -> None:
        """
        分享Paste到房间

        Args:
            db: 数据库会话
            member_token: 成员令牌
            room_id: 房间ID
            share_data: 分享数据
        """
        # 验证成员令牌
        token_payload = CollabRoomService._verify_member_token(member_token)

        # 验证成员是否在房间中
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

        # 验证Paste是否存在
        paste = db.query(Paste).filter(Paste.id == share_data.paste_id).first()
        if not paste:
            raise ValueError("Paste不存在")

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
            shared_by_member_id=token_payload.member_id,
            target_member_id=share_data.target_member_id,
            encrypted_paste_key=share_data.encrypted_paste_key,
        )

        db.add(room_paste)
        db.commit()

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
        # 验证成员令牌
        token_payload = CollabRoomService._verify_member_token(member_token)

        # 验证成员是否在房间中
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

        # 构建查询条件
        query = (
            db.query(RoomPaste, Paste)
            .join(Paste, RoomPaste.paste_id == Paste.id)
            .filter(RoomPaste.room_id == room_id)
        )

        if paste_type == "received":
            # 只返回发送给当前用户或所有人的
            query = query.filter(
                or_(
                    RoomPaste.target_member_id == token_payload.member_id,
                    RoomPaste.target_member_id.is_(None),
                )
            )
        elif paste_type == "sent":
            # 只返回当前用户发送的
            query = query.filter(
                RoomPaste.shared_by_member_id == token_payload.member_id
            )
        # paste_type == "all" 不需要额外过滤

        room_pastes = query.order_by(RoomPaste.shared_at.desc()).all()

        paste_infos = []
        for room_paste_record, paste_record in room_pastes:
            paste_infos.append(
                SharedPasteInfo(
                    paste_id=str(room_paste_record.paste_id),  # type: ignore
                    title=str(paste_record.title) if paste_record.title else None,  # type: ignore
                    encrypted_paste_key=str(room_paste_record.encrypted_paste_key),  # type: ignore
                    shared_by=str(room_paste_record.shared_by_member_id),  # type: ignore
                    target_member=str(room_paste_record.target_member_id)
                    if room_paste_record.target_member_id
                    else None,  # type: ignore
                    shared_at=room_paste_record.shared_at,  # type: ignore
                )
            )

        return RoomPastesResponse(pastes=paste_infos)

    @staticmethod
    def leave_room(db: Session, member_token: str, room_id: str) -> None:
        """
        离开房间

        Args:
            db: 数据库会话
            member_token: 成员令牌
            room_id: 房间ID
        """
        # 验证成员令牌
        token_payload = CollabRoomService._verify_member_token(member_token)

        # 获取成员关系
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

        # 删除成员关系
        db.delete(membership)

        # 更新房间成员数
        room = db.query(CollabRoom).filter(CollabRoom.id == room_id).first()
        if room:
            current_count = int(room.member_count or 1)  # type: ignore
            room.member_count = max(0, current_count - 1)  # type: ignore

        db.commit()

    @staticmethod
    def update_member_last_seen(db: Session, member_token: str, room_id: str) -> None:
        """
        更新成员最后活跃时间

        Args:
            db: 数据库会话
            member_token: 成员令牌
            room_id: 房间ID
        """
        # 验证成员令牌
        token_payload = CollabRoomService._verify_member_token(member_token)

        # 获取成员关系
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

        if membership:
            membership.last_seen = datetime.utcnow()  # type: ignore
            db.commit()
