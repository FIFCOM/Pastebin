import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock

from fastapi import WebSocket, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.schemas.collab_room import (
    SharedPasteInfo,
    WSAuthMessage,
    WSAuthOkMessage,
    WSChatMessage,
    WSErrorMessage,
    WSMemberJoinedMessage,
    WSMemberLeftMessage,
    WSPasteSharedMessage,
    WSPongMessage,
)
from app.services.collab_room_service import CollabRoomService
from app.services.install_state_service import InstallStateService


@dataclass(frozen=True)
class RealtimeConnection:
    room_id: str
    member_id: str
    display_name: str
    websocket: WebSocket


@dataclass(frozen=True)
class DisconnectEvent:
    room_id: str
    member_id: str
    display_name: str
    member_went_offline: bool


@dataclass(frozen=True)
class CleanupDisconnectTarget:
    room_id: str
    member_id: str
    display_name: str


class CollabRoomRealtimeService:
    _lock: RLock = RLock()
    _room_connections: dict[str, dict[str, set[WebSocket]]] = {}
    _socket_index: dict[int, RealtimeConnection] = {}
    MAX_ENCRYPTED_MESSAGE_LENGTH: int = 64 * 1024

    @classmethod
    async def authenticate_connection(
        cls, websocket: WebSocket, room_id: str
    ) -> RealtimeConnection | None:
        await websocket.accept()

        try:
            raw_message: object = await asyncio.wait_for(
                websocket.receive_json(), timeout=10
            )
            auth_message = WSAuthMessage.model_validate(raw_message)
        except (TimeoutError, ValidationError, ValueError):
            await cls._send_error(websocket, "请先发送合法的认证消息")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        try:
            with SessionLocal() as db:
                state = InstallStateService.get_state(db)
                if state.needs_install:
                    await cls._send_error(websocket, "安装未完成")
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return None

                context = CollabRoomService.get_room_member_context(
                    db, auth_message.token, room_id
                )
                member_id = str(context.member.id)  # type: ignore[arg-type]
                _ = CollabRoomService.touch_room_presence(db, room_id, member_id)
                connection = RealtimeConnection(
                    room_id=room_id,
                    member_id=member_id,
                    display_name=str(context.member.display_name),  # type: ignore[arg-type]
                    websocket=websocket,
                )
        except ValueError as exc:
            await cls._send_error(websocket, str(exc))
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        became_online = cls._register_connection(connection)
        await websocket.send_json(
            WSAuthOkMessage(
                type="auth_ok",
                room_id=room_id,
                member_id=connection.member_id,
                display_name=connection.display_name,
                timestamp=datetime.now(UTC),
            ).model_dump(mode="json")
        )
        if became_online:
            await cls.broadcast_member_joined(
                room_id,
                connection.member_id,
                connection.display_name,
                exclude_member_id=connection.member_id,
            )
        return connection

    @classmethod
    async def handle_client_message(
        cls, connection: RealtimeConnection, payload: dict[str, object]
    ) -> None:
        message_type = payload.get("type")
        with SessionLocal() as db:
            if not cls._refresh_connection_membership(db, connection):
                raise ValueError("您已不在此房间中")

        if message_type == "ping":
            await connection.websocket.send_json(
                WSPongMessage(
                    type="pong",
                    timestamp=datetime.now(UTC),
                ).model_dump(mode="json")
            )
            return

        if message_type != "message":
            await cls._send_error(connection.websocket, "不支持的消息类型")
            return

        encrypted_data = payload.get("encrypted_data")
        if not isinstance(encrypted_data, str) or not encrypted_data.strip():
            await cls._send_error(connection.websocket, "消息内容不能为空")
            return
        if len(encrypted_data) > cls.MAX_ENCRYPTED_MESSAGE_LENGTH:
            await cls._send_error(connection.websocket, "消息内容过长")
            return

        message = WSChatMessage(
            type="message",
            encrypted_data=encrypted_data,
            sender_id=connection.member_id,
            timestamp=datetime.now(UTC),
        )
        await cls.broadcast_json(connection.room_id, message.model_dump(mode="json"))

    @classmethod
    async def disconnect(cls, websocket: WebSocket) -> None:
        event = cls._remove_socket(websocket)
        if event and event.member_went_offline:
            await cls.broadcast_member_left(
                event.room_id,
                event.member_id,
                event.display_name,
            )

    @classmethod
    async def disconnect_member(
        cls,
        room_id: str,
        member_id: str,
        display_name: str,
        *,
        code: int = status.WS_1008_POLICY_VIOLATION,
        reason: str = "您已离开房间",
    ) -> None:
        sockets = cls._remove_member_sockets(room_id, member_id)
        for websocket in sockets:
            await websocket.close(code=code, reason=reason)
        if sockets:
            await cls.broadcast_member_left(room_id, member_id, display_name)

    @classmethod
    async def dispatch_cleanup_disconnects(
        cls,
        closed_room_ids: list[str],
        disconnected_members: list[CleanupDisconnectTarget],
    ) -> None:
        if not closed_room_ids and not disconnected_members:
            return

        for room_id in closed_room_ids:
            await cls.close_room(room_id, reason="房间已因成员过期而关闭")
        for target in disconnected_members:
            await cls.disconnect_member(
                target.room_id,
                target.member_id,
                target.display_name,
                reason="您已过期并被移出房间",
            )

    @classmethod
    def run_cleanup_disconnects(
        cls,
        closed_room_ids: list[str],
        disconnected_members: list[CleanupDisconnectTarget],
    ) -> None:
        if not closed_room_ids and not disconnected_members:
            return

        async def runner() -> None:
            await cls.dispatch_cleanup_disconnects(
                closed_room_ids,
                disconnected_members,
            )

        try:
            _ = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(runner())
            return
        raise RuntimeError(
            "run_cleanup_disconnects cannot be used inside an active event loop"
        )

    @classmethod
    async def close_room(
        cls,
        room_id: str,
        *,
        code: int = status.WS_1001_GOING_AWAY,
        reason: str = "房间已关闭",
    ) -> None:
        sockets = cls._remove_room_sockets(room_id)
        for websocket in sockets:
            await websocket.close(code=code, reason=reason)

    @classmethod
    async def broadcast_shared_paste(
        cls, room_id: str, shared_paste: SharedPasteInfo
    ) -> None:
        target_member_ids = {str(shared_paste.shared_by)}
        if shared_paste.target_member:
            target_member_ids.add(str(shared_paste.target_member))
        else:
            target_member_ids = None

        await cls.broadcast_json(
            room_id,
            WSPasteSharedMessage(
                type="paste_shared",
                paste_id=str(shared_paste.paste_id),
                shared_by=str(shared_paste.shared_by),
                target_member=(
                    str(shared_paste.target_member)
                    if shared_paste.target_member
                    else None
                ),
                timestamp=shared_paste.shared_at,
            ).model_dump(mode="json"),
            target_member_ids=target_member_ids,
        )

    @classmethod
    async def broadcast_member_joined(
        cls,
        room_id: str,
        member_id: str,
        display_name: str,
        *,
        exclude_member_id: str | None = None,
    ) -> None:
        await cls.broadcast_json(
            room_id,
            WSMemberJoinedMessage(
                type="member_joined",
                member_id=member_id,
                display_name=display_name,
                timestamp=datetime.now(UTC),
            ).model_dump(mode="json"),
            exclude_member_id=exclude_member_id,
        )

    @classmethod
    async def broadcast_member_left(
        cls, room_id: str, member_id: str, display_name: str
    ) -> None:
        await cls.broadcast_json(
            room_id,
            WSMemberLeftMessage(
                type="member_left",
                member_id=member_id,
                display_name=display_name,
                timestamp=datetime.now(UTC),
            ).model_dump(mode="json"),
        )

    @classmethod
    async def broadcast_json(
        cls,
        room_id: str,
        payload: dict[str, object],
        *,
        target_member_ids: set[str] | None = None,
        exclude_member_id: str | None = None,
    ) -> None:
        sockets, stale_connections = cls._collect_sockets(
            room_id, target_member_ids, exclude_member_id
        )
        failed_sockets: list[WebSocket] = []
        for websocket in sockets:
            try:
                await websocket.send_json(payload)
            except Exception:
                failed_sockets.append(websocket)

        for connection in stale_connections:
            await cls.disconnect_member(
                connection.room_id,
                connection.member_id,
                connection.display_name,
                reason="您已不在房间中",
            )

        for websocket in failed_sockets:
            await cls.disconnect(websocket)

    @classmethod
    def get_active_member_ids(cls, room_id: str) -> set[str]:
        with cls._lock:
            return set(cls._room_connections.get(room_id, {}).keys())

    @classmethod
    def _register_connection(cls, connection: RealtimeConnection) -> bool:
        with cls._lock:
            room_connections = cls._room_connections.setdefault(connection.room_id, {})
            member_connections = room_connections.setdefault(
                connection.member_id, set()
            )
            became_online = not member_connections
            member_connections.add(connection.websocket)
            cls._socket_index[id(connection.websocket)] = connection
            return became_online

    @classmethod
    def _remove_socket(cls, websocket: WebSocket) -> DisconnectEvent | None:
        with cls._lock:
            connection = cls._socket_index.pop(id(websocket), None)
            if connection is None:
                return None

            room_connections = cls._room_connections.get(connection.room_id)
            if room_connections is None:
                return None

            member_connections = room_connections.get(connection.member_id)
            if member_connections is None:
                return None

            member_connections.discard(websocket)
            member_went_offline = not member_connections
            if member_went_offline:
                _ = room_connections.pop(connection.member_id, None)
            if not room_connections:
                _ = cls._room_connections.pop(connection.room_id, None)

            return DisconnectEvent(
                room_id=connection.room_id,
                member_id=connection.member_id,
                display_name=connection.display_name,
                member_went_offline=member_went_offline,
            )

    @classmethod
    def _remove_member_sockets(cls, room_id: str, member_id: str) -> list[WebSocket]:
        with cls._lock:
            room_connections = cls._room_connections.get(room_id)
            if room_connections is None:
                return []

            member_connections = list(room_connections.pop(member_id, set()))
            for websocket in member_connections:
                _ = cls._socket_index.pop(id(websocket), None)

            if not room_connections:
                _ = cls._room_connections.pop(room_id, None)
            return member_connections

    @classmethod
    def _remove_room_sockets(cls, room_id: str) -> list[WebSocket]:
        with cls._lock:
            room_connections = cls._room_connections.pop(room_id, {})
            sockets: list[WebSocket] = []
            for member_connections in room_connections.values():
                for websocket in member_connections:
                    _ = cls._socket_index.pop(id(websocket), None)
                    sockets.append(websocket)
            return sockets

    @classmethod
    def _collect_sockets(
        cls,
        room_id: str,
        target_member_ids: set[str] | None,
        exclude_member_id: str | None,
    ) -> tuple[list[WebSocket], list[RealtimeConnection]]:
        with cls._lock:
            room_connections = cls._room_connections.get(room_id, {})
            selected_connections: list[RealtimeConnection] = []
            for member_id, member_connections in room_connections.items():
                if exclude_member_id is not None and member_id == exclude_member_id:
                    continue
                if target_member_ids is not None and member_id not in target_member_ids:
                    continue
                for websocket in member_connections:
                    connection = cls._socket_index.get(id(websocket))
                    if connection is not None:
                        selected_connections.append(connection)

        if not selected_connections:
            return [], []

        valid_member_ids = cls._get_valid_member_ids(room_id, selected_connections)
        sockets: list[WebSocket] = []
        stale_connections: list[RealtimeConnection] = []
        for connection in selected_connections:
            if connection.member_id in valid_member_ids:
                sockets.append(connection.websocket)
            else:
                stale_connections.append(connection)
        return sockets, stale_connections

    @classmethod
    def _refresh_connection_membership(
        cls, db: Session, connection: RealtimeConnection
    ) -> bool:
        if not CollabRoomService.has_active_room_membership(
            db,
            connection.room_id,
            connection.member_id,
        ):
            return False

        touched_at = CollabRoomService.touch_room_presence(
            db,
            connection.room_id,
            connection.member_id,
        )
        return touched_at is not None

    @classmethod
    def _get_valid_member_ids(
        cls, room_id: str, connections: list[RealtimeConnection]
    ) -> set[str]:
        member_ids = {connection.member_id for connection in connections}
        if not member_ids:
            return set()

        with SessionLocal() as db:
            return {
                member_id
                for member_id in member_ids
                if CollabRoomService.has_active_room_membership(db, room_id, member_id)
            }

    @staticmethod
    async def _send_error(websocket: WebSocket, message: str) -> None:
        try:
            await websocket.send_json(
                WSErrorMessage(type="error", message=message).model_dump(mode="json")
            )
        except Exception:
            return
