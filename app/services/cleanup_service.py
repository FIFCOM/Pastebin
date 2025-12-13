"""
清理任务服务层 - 处理过期数据清理
"""

import os
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.collab_room import Member
from app.models.paste import File, Paste
from app.schemas.cleanup import CleanupResponse, CleanupTaskResult
from config.config import settings


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
                    # 删除关联的文件（物理文件和数据库记录）
                    CleanupService._delete_paste_files(str(paste.id), db)

                    # 删除paste记录（会级联删除paste_keys和files记录）
                    db.delete(paste)
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
                    # 删除关联的文件（物理文件和数据库记录）
                    CleanupService._delete_paste_files(str(paste.id), db)

                    # 删除paste记录（会级联删除相关记录）
                    db.delete(paste)
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

            deleted_count = 0
            for member in expired_members:
                try:
                    # Member删除会级联删除：
                    # - 创建的房间 (CollabRoom)
                    # - 房间成员关系 (RoomMember)
                    # - 分享的paste记录 (RoomPaste)
                    db.delete(member)
                    deleted_count += 1

                except Exception as e:
                    print(f"清理成员 {member.id} 时出错: {e}")

            db.commit()

            return CleanupTaskResult(
                task_name="expired_members",
                success=True,
                deleted_count=deleted_count,
                message=f"成功清理 {deleted_count} 个过期成员及其关联数据",
                error=None,
            )

        except Exception as e:
            db.rollback()
            return CleanupTaskResult(
                task_name="expired_members",
                success=False,
                deleted_count=0,
                message="清理过期成员失败",
                error=str(e),
            )

    @staticmethod
    def _delete_paste_files(paste_id: str, db: Session) -> None:
        """
        删除paste关联的物理文件

        Args:
            paste_id: paste ID
            db: 数据库会话
        """
        # 获取paste的内容文件路径
        paste = db.query(Paste).filter(Paste.id == paste_id).first()
        if paste and paste.content_path:  # type: ignore
            try:
                content_file_path = os.path.join(
                    settings.data_dir, str(paste.content_path)
                )
                if os.path.exists(content_file_path):
                    os.remove(content_file_path)
            except Exception as e:
                print(f"删除内容文件 {paste.content_path} 时出错: {e}")

        # 获取并删除关联的文件
        files = db.query(File).filter(File.paste_id == paste_id).all()
        for file_record in files:
            try:
                file_path = os.path.join(
                    settings.data_dir, str(file_record.storage_path)
                )
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"删除文件 {file_record.storage_path} 时出错: {e}")

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
