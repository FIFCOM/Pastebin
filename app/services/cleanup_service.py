"""
清理任务服务层 - 处理过期数据清理
"""

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_attribute

from app.models.collab_room import CollabRoom, Member, RoomMember
from app.models.paste import FileUploadSession, Paste
from app.models.user import UsedRefreshToken, UserSession
from app.schemas.cleanup import CleanupResponse, CleanupTaskResult
from app.services.collab_room_realtime_service import (
    CleanupDisconnectTarget,
    CollabRoomRealtimeService,
)
from app.services.collab_room_service import CollabRoomService
from app.services.paste_service import PasteService
from config.config import settings


@dataclass(frozen=True)
class ExpiredMemberCleanupActions:
    closed_room_ids: list[str]
    disconnected_members: list[CleanupDisconnectTarget]


class CleanupService:
    """清理任务服务类"""

    @staticmethod
    def cleanup_expired_drafts(db: Session) -> CleanupTaskResult:
        """
        清理过期的草稿

        Args:
            db: 数据库会话

        Returns:
            清理结果
        """
        try:
            # 查找过期的草稿
            now = datetime.now(UTC)
            expired_drafts = (
                db.query(Paste)
                .filter(Paste.status == "draft", Paste.expire_at < now)
                .all()
            )

            deleted_count = 0
            for paste in expired_drafts:
                try:
                    PasteService.delete_paste_record(db, paste)
                    deleted_count += 1

                except Exception as e:
                    # 记录错误但继续处理其他记录
                    print(f"清理草稿 {paste.id} 时出错: {e}")

            db.commit()

            return CleanupTaskResult(
                task_name="expired_drafts",
                success=True,
                deleted_count=deleted_count,
                message=f"成功清理 {deleted_count} 个过期草稿",
                error=None,
            )

        except Exception as e:
            db.rollback()
            return CleanupTaskResult(
                task_name="expired_drafts",
                success=False,
                deleted_count=0,
                message="清理过期草稿失败",
                error=str(e),
            )

    @staticmethod
    def cleanup_expired_pastes(db: Session) -> CleanupTaskResult:
        """
        清理过期的已发布paste

        Args:
            db: 数据库会话

        Returns:
            清理结果
        """
        try:
            # 查找过期的已发布paste
            now = datetime.now(UTC)
            expired_pastes = (
                db.query(Paste)
                .filter(
                    Paste.status.in_(["published", "edited"]),
                    Paste.expire_at < now,
                    Paste.expire_at.isnot(None),  # 排除永不过期的paste
                )
                .all()
            )

            deleted_count = 0
            for paste in expired_pastes:
                try:
                    PasteService.delete_paste_record(db, paste)
                    deleted_count += 1

                except Exception as e:
                    print(f"清理paste {paste.id} 时出错: {e}")

            db.commit()

            return CleanupTaskResult(
                task_name="expired_pastes",
                success=True,
                deleted_count=deleted_count,
                message=f"成功清理 {deleted_count} 个过期paste",
                error=None,
            )

        except Exception as e:
            db.rollback()
            return CleanupTaskResult(
                task_name="expired_pastes",
                success=False,
                deleted_count=0,
                message="清理过期paste失败",
                error=str(e),
            )

    @staticmethod
    def cleanup_expired_members(db: Session) -> CleanupTaskResult:
        result, actions = CleanupService._cleanup_expired_members(db)
        if not result.success:
            return result

        try:
            CollabRoomRealtimeService.run_cleanup_disconnects(
                closed_room_ids=actions.closed_room_ids,
                disconnected_members=actions.disconnected_members,
            )
        except Exception as e:
            return CleanupTaskResult(
                task_name="expired_members",
                success=False,
                deleted_count=result.deleted_count,
                message="过期成员已清理，但实时断连失败",
                error=str(e),
            )

        return result

    @staticmethod
    async def cleanup_expired_members_async(db: Session) -> CleanupTaskResult:
        result, actions = CleanupService._cleanup_expired_members(db)
        if not result.success:
            return result

        try:
            await CollabRoomRealtimeService.dispatch_cleanup_disconnects(
                closed_room_ids=actions.closed_room_ids,
                disconnected_members=actions.disconnected_members,
            )
        except Exception as e:
            return CleanupTaskResult(
                task_name="expired_members",
                success=False,
                deleted_count=result.deleted_count,
                message="过期成员已清理，但实时断连失败",
                error=str(e),
            )

        return result

    @staticmethod
    def _cleanup_expired_members(
        db: Session,
    ) -> tuple[CleanupTaskResult, ExpiredMemberCleanupActions]:
        """
        清理过期的临时成员

        Args:
            db: 数据库会话

        Returns:
            清理结果
        """
        try:
            # 查找过期的成员
            now = datetime.now(UTC)
            expired_members = db.query(Member).filter(Member.expire_at < now).all()
            expired_member_ids = {str(member.id) for member in expired_members}

            deleted_count = 0
            affected_room_ids: set[str] = set()
            closed_room_ids: set[str] = set()
            disconnected_members: dict[tuple[str, str], CleanupDisconnectTarget] = {}
            for member in expired_members:
                try:
                    member_id = str(member.id)  # type: ignore
                    display_name = str(member.display_name)  # type: ignore

                    owned_rooms = (
                        db.query(CollabRoom)
                        .filter(CollabRoom.creator_member_id == member_id)
                        .all()
                    )
                    for room in owned_rooms:
                        successor = CollabRoomService._get_next_owner_membership(
                            db,
                            str(room.id),  # type: ignore
                            excluded_member_ids=expired_member_ids,
                        )
                        if successor is None:
                            closed_room_ids.add(str(room.id))  # type: ignore
                            db.delete(room)
                            continue

                        set_attribute(
                            room, "creator_member_id", str(successor.member_id)
                        )
                        affected_room_ids.add(str(room.id))  # type: ignore

                    # 记录该成员参与的房间，用于后续同步 member_count
                    room_ids = (
                        db.query(RoomMember.room_id)
                        .filter(RoomMember.member_id == member_id)
                        .all()
                    )
                    member_room_ids = [str(rid) for (rid,) in room_ids]
                    affected_room_ids.update(member_room_ids)
                    for room_id in member_room_ids:
                        if room_id in closed_room_ids:
                            continue
                        disconnected_members[(room_id, member_id)] = (
                            CleanupDisconnectTarget(
                                room_id=room_id,
                                member_id=member_id,
                                display_name=display_name,
                            )
                        )

                    db.delete(member)
                    deleted_count += 1

                except Exception as e:
                    print(f"清理成员 {member.id} 时出错: {e}")

            # 先 flush 删除，再按真实 room_members 同步 collab_rooms.member_count
            db.flush()
            for room_id in affected_room_ids:
                room = db.query(CollabRoom).filter(CollabRoom.id == room_id).first()
                if not room:
                    continue
                set_attribute(
                    room,
                    "member_count",
                    db.query(RoomMember).filter(RoomMember.room_id == room_id).count(),
                )

            db.commit()
            return (
                CleanupTaskResult(
                    task_name="expired_members",
                    success=True,
                    deleted_count=deleted_count,
                    message=f"成功清理 {deleted_count} 个过期成员及其关联数据",
                    error=None,
                ),
                ExpiredMemberCleanupActions(
                    closed_room_ids=sorted(closed_room_ids),
                    disconnected_members=sorted(
                        disconnected_members.values(),
                        key=lambda target: (target.room_id, target.member_id),
                    ),
                ),
            )

        except Exception as e:
            db.rollback()
            return (
                CleanupTaskResult(
                    task_name="expired_members",
                    success=False,
                    deleted_count=0,
                    message="清理过期成员失败",
                    error=str(e),
                ),
                ExpiredMemberCleanupActions(
                    closed_room_ids=[],
                    disconnected_members=[],
                ),
            )

    @staticmethod
    async def execute_cleanup_tasks_async(
        db: Session, task_names: list[str]
    ) -> CleanupResponse:
        task_results = []
        total_deleted = 0
        overall_success = True

        for task_name in task_names:
            if task_name == "expired_members":
                result = await CleanupService.cleanup_expired_members_async(db)
            else:
                task_handlers = {
                    "expired_drafts": CleanupService.cleanup_expired_drafts,
                    "expired_pastes": CleanupService.cleanup_expired_pastes,
                    "expired_uploads": CleanupService.cleanup_expired_uploads,
                    "expired_user_sessions": CleanupService.cleanup_expired_user_sessions,
                    "expired_used_refresh_tokens": CleanupService.cleanup_expired_used_refresh_tokens,
                }
                if task_name not in task_handlers:
                    result = CleanupTaskResult(
                        task_name=task_name,
                        success=False,
                        deleted_count=0,
                        message="未知的清理任务",
                        error=f"不支持的任务类型: {task_name}",
                    )
                else:
                    result = task_handlers[task_name](db)

            task_results.append(result)
            if result.success:
                total_deleted += result.deleted_count
            else:
                overall_success = False

        if overall_success:
            message = f"所有清理任务执行成功，共删除 {total_deleted} 条记录"
        else:
            success_count = sum(1 for r in task_results if r.success)
            message = f"{success_count}/{len(task_results)} 个任务执行成功，共删除 {total_deleted} 条记录"

        return CleanupResponse(
            success=overall_success,
            total_deleted=total_deleted,
            task_results=task_results,
            message=message,
        )

    @staticmethod
    def cleanup_expired_uploads(db: Session) -> CleanupTaskResult:
        """
        清理过期的分片上传会话及其临时文件
        """
        try:
            now = datetime.now(UTC)
            expired_sessions = (
                db.query(FileUploadSession)
                .filter(FileUploadSession.expire_at < now)
                .all()
            )

            deleted_count = 0
            for sess in expired_sessions:
                try:
                    paste_id = str(sess.paste_id)  # type: ignore
                    upload_id = str(sess.id)  # type: ignore
                    # 删除临时目录：data/uploads/files/{paste_id}/{upload_id}
                    upload_dir = os.path.join(
                        settings.data_dir, "uploads", "files", paste_id, upload_id
                    )
                    if os.path.exists(upload_dir):
                        for root, dirs, files in os.walk(upload_dir, topdown=False):
                            for name in files:
                                try:
                                    os.remove(os.path.join(root, name))
                                except Exception:
                                    pass
                            for name in dirs:
                                try:
                                    os.rmdir(os.path.join(root, name))
                                except Exception:
                                    pass
                        try:
                            os.rmdir(upload_dir)
                        except Exception:
                            pass

                    db.delete(sess)
                    deleted_count += 1
                except Exception as e:
                    print(f"清理上传会话 {sess.id} 时出错: {e}")

            db.commit()
            return CleanupTaskResult(
                task_name="expired_uploads",
                success=True,
                deleted_count=deleted_count,
                message=f"成功清理 {deleted_count} 个过期上传会话",
                error=None,
            )
        except Exception as e:
            db.rollback()
            return CleanupTaskResult(
                task_name="expired_uploads",
                success=False,
                deleted_count=0,
                message="清理过期上传会话失败",
                error=str(e),
            )

    @staticmethod
    def cleanup_expired_user_sessions(db: Session) -> CleanupTaskResult:
        """清理过期用户会话（refresh token 过期后）"""
        try:
            now = datetime.now(UTC)
            q = db.query(UserSession).filter(UserSession.expires_at < now)
            deleted_count = q.count()
            q.delete(synchronize_session=False)
            db.commit()
            return CleanupTaskResult(
                task_name="expired_user_sessions",
                success=True,
                deleted_count=deleted_count,
                message=f"成功清理 {deleted_count} 个过期用户会话",
                error=None,
            )
        except Exception as e:
            db.rollback()
            return CleanupTaskResult(
                task_name="expired_user_sessions",
                success=False,
                deleted_count=0,
                message="清理过期用户会话失败",
                error=str(e),
            )

    @staticmethod
    def cleanup_expired_used_refresh_tokens(db: Session) -> CleanupTaskResult:
        """清理过期 refresh token 使用记录（避免 UsedRefreshToken 表无限增长）"""
        try:
            cutoff = datetime.now(UTC) - timedelta(
                days=settings.refresh_token_expire_days
            )
            q = db.query(UsedRefreshToken).filter(UsedRefreshToken.used_at < cutoff)
            deleted_count = q.count()
            q.delete(synchronize_session=False)
            db.commit()
            return CleanupTaskResult(
                task_name="expired_used_refresh_tokens",
                success=True,
                deleted_count=deleted_count,
                message=f"成功清理 {deleted_count} 条 refresh token 记录",
                error=None,
            )
        except Exception as e:
            db.rollback()
            return CleanupTaskResult(
                task_name="expired_used_refresh_tokens",
                success=False,
                deleted_count=0,
                message="清理 refresh token 记录失败",
                error=str(e),
            )

    @staticmethod
    def execute_cleanup_tasks(db: Session, task_names: list[str]) -> CleanupResponse:
        """
        执行清理任务

        Args:
            db: 数据库会话
            task_names: 要执行的任务名称列表

        Returns:
            清理响应
        """
        # 任务映射
        task_handlers = {
            "expired_drafts": CleanupService.cleanup_expired_drafts,
            "expired_pastes": CleanupService.cleanup_expired_pastes,
            "expired_members": CleanupService.cleanup_expired_members,
            "expired_uploads": CleanupService.cleanup_expired_uploads,
            "expired_user_sessions": CleanupService.cleanup_expired_user_sessions,
            "expired_used_refresh_tokens": CleanupService.cleanup_expired_used_refresh_tokens,
        }

        task_results = []
        total_deleted = 0
        overall_success = True

        # 执行每个任务
        for task_name in task_names:
            if task_name not in task_handlers:
                # 未知任务
                result = CleanupTaskResult(
                    task_name=task_name,
                    success=False,
                    deleted_count=0,
                    message="未知的清理任务",
                    error=f"不支持的任务类型: {task_name}",
                )
            else:
                # 执行任务
                result = task_handlers[task_name](db)

            task_results.append(result)
            if result.success:
                total_deleted += result.deleted_count
            else:
                overall_success = False

        # 生成总体消息
        if overall_success:
            message = f"所有清理任务执行成功，共删除 {total_deleted} 条记录"
        else:
            success_count = sum(1 for r in task_results if r.success)
            message = f"{success_count}/{len(task_results)} 个任务执行成功，共删除 {total_deleted} 条记录"

        return CleanupResponse(
            success=overall_success,
            total_deleted=total_deleted,
            task_results=task_results,
            message=message,
        )
