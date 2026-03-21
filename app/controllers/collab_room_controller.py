"""
协作房间控制器 - REST API路由
"""

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Path,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_optional_user
from app.schemas.collab_room import (
    MemberTokenResponse,
    PasteShareRequest,
    RoomCreateRequest,
    RoomCreateResponse,
    RoomInfoResponse,
    RoomJoinRequest,
    RoomJoinResponse,
    RoomMembersResponse,
    RoomPastesResponse,
)
from app.schemas.common import MessageResponse
from app.services.collab_room_realtime_service import CollabRoomRealtimeService
from app.services.collab_room_service import CollabRoomService

# 创建路由器
router = APIRouter(prefix="/api", tags=["协作房间"])


def _get_member_token_from_header(authorization: str | None) -> str:
    """从Authorization头中提取member_token"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少Authorization头",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的Authorization格式",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return authorization[7:]  # 去掉 "Bearer " 前缀


@router.post("/rooms/member-token", response_model=MemberTokenResponse)
async def get_member_token(
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    """
    获取成员令牌（不必登录）

    - 如果提供了有效的session_token，使用用户名
    - 否则生成Guest_xxxxx
    - 生成24小时有效的JWT
    """
    try:
        user_id = current_user.id if current_user else None
        return CollabRoomService.get_member_token(db, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None


@router.post("/rooms", response_model=RoomCreateResponse)
async def create_room(
    room_data: RoomCreateRequest,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """
    创建协作房间

    需要在Authorization头中提供member_token: Bearer {member_token}

    当前创建临时公共房间时不接受自定义房间参数：

    - 房间名称固定为“临时公共房间”
    - 最大成员数由后端配置控制
    """
    member_token = _get_member_token_from_header(authorization)

    try:
        return CollabRoomService.create_room(db, member_token, room_data)
    except ValueError as e:
        if "令牌" in str(e) or "成员不存在" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None


@router.get("/join/{pin_code}", response_model=RoomInfoResponse)
async def get_room_info_by_pin(
    pin_code: str = Path(..., min_length=6, max_length=6, regex="^[A-Za-z0-9]{6}$"),
    db: Session = Depends(get_db),
):
    """
    通过PIN码获取房间信息

    - **pin_code**: 6位PIN码
    """
    try:
        return CollabRoomService.get_room_info_by_pin(db, pin_code)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from None


@router.post("/rooms/{room_id}/join", response_model=RoomJoinResponse)
async def join_room(
    room_id: str,
    join_data: RoomJoinRequest,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """
    加入房间

    需要在Authorization头中提供member_token: Bearer {member_token}

    - **pin_code**: 6位PIN码
    """
    member_token = _get_member_token_from_header(authorization)

    try:
        return CollabRoomService.join_room(db, member_token, room_id, join_data)
    except ValueError as e:
        if "令牌" in str(e) or "成员不存在" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
            ) from None
        elif "不存在" in str(e) or "错误" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from None
        elif "已满" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None


@router.get("/rooms/{room_id}/members", response_model=RoomMembersResponse)
async def get_room_members(
    room_id: str,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """
    获取成员列表

    需要在Authorization头中提供member_token: Bearer {member_token}
    """
    member_token = _get_member_token_from_header(authorization)

    try:
        return CollabRoomService.get_room_members(
            db,
            member_token,
            room_id,
            active_member_ids=CollabRoomRealtimeService.get_active_member_ids(room_id),
        )
    except ValueError as e:
        if "令牌" in str(e) or "不在此房间中" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None


@router.post("/rooms/{room_id}/pastes", response_model=MessageResponse)
async def share_paste_to_room(
    room_id: str,
    share_data: PasteShareRequest,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """
    分享Paste到房间

    需要在Authorization头中提供member_token: Bearer {member_token}

    - **paste_id**: Paste ID
    - **encrypted_paste_key**: 用room_key加密的paste密钥
    - **target_member_id**: 目标接收者ID，不提供则发送给所有人
    """
    member_token = _get_member_token_from_header(authorization)

    try:
        shared_paste = CollabRoomService.share_paste_to_room(
            db,
            member_token,
            room_id,
            share_data,
        )
        await CollabRoomRealtimeService.broadcast_shared_paste(room_id, shared_paste)
        return MessageResponse(message="Paste分享成功")
    except ValueError as e:
        if "令牌" in str(e) or "不在此房间中" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
            ) from None
        elif "不存在" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None


@router.get("/rooms/{room_id}/pastes", response_model=RoomPastesResponse)
async def get_room_pastes(
    room_id: str,
    type: str = Query(
        "received", regex="^(received|sent|all)$", description="接收的|发送的|全部"
    ),
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """
    获取房间内的Paste（只返回发送给当前用户或所有人的）

    需要在Authorization头中提供member_token: Bearer {member_token}

    - **type**: received（接收的）|sent（发送的）|all（全部），默认为received
    """
    member_token = _get_member_token_from_header(authorization)

    try:
        return CollabRoomService.get_room_pastes(db, member_token, room_id, type)
    except ValueError as e:
        if "令牌" in str(e) or "不在此房间中" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None


@router.delete("/rooms/{room_id}/leave", response_model=MessageResponse)
async def leave_room(
    room_id: str,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """
    离开房间

    需要在Authorization头中提供member_token: Bearer {member_token}
    """
    member_token = _get_member_token_from_header(authorization)

    try:
        leave_result = CollabRoomService.leave_room(db, member_token, room_id)
        if leave_result.room_deleted:
            await CollabRoomRealtimeService.close_room(room_id)
        else:
            await CollabRoomRealtimeService.disconnect_member(
                room_id,
                leave_result.member_id,
                leave_result.display_name,
            )
        return MessageResponse(message="已离开房间")
    except ValueError as e:
        if "令牌" in str(e) or "不在此房间中" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from None


@router.websocket("/rooms/{room_id}/ws")
async def room_websocket(websocket: WebSocket, room_id: str):
    connection = await CollabRoomRealtimeService.authenticate_connection(
        websocket,
        room_id,
    )
    if connection is None:
        return

    try:
        while True:
            try:
                payload = await websocket.receive_json()
            except WebSocketDisconnect:
                break
            except Exception:
                await websocket.send_json(
                    {"type": "error", "message": "消息必须是合法的JSON对象"}
                )
                await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
                break

            if not isinstance(payload, dict):
                await websocket.send_json(
                    {"type": "error", "message": "消息必须是JSON对象"}
                )
                await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
                break
            payload_dict: dict[str, object] = payload

            try:
                await CollabRoomRealtimeService.handle_client_message(
                    connection, payload_dict
                )
            except ValueError as exc:
                await websocket.send_json({"type": "error", "message": str(exc)})
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                break
            except WebSocketDisconnect:
                break
            except Exception:
                await websocket.send_json(
                    {"type": "error", "message": "处理消息时发生服务器错误"}
                )
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
                break
    finally:
        await CollabRoomRealtimeService.disconnect(websocket)
