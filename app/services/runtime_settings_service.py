"""
运行配置服务
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.runtime_setting import RuntimeSetting
from app.schemas.runtime_settings import RuntimeSettingItem, RuntimeSettingUpdate


@dataclass(frozen=True)
class RuntimeSettingDefinition:
    key: str
    default_value: int
    label: str
    group: str
    unit: str
    description: str
    allow_zero: bool
    min_value: int
    max_value: int | None = None


@dataclass(frozen=True)
class UploadRuntimeSettings:
    max_upload_file_size: int
    max_paste_total_upload_size: int
    max_chunk_size: int
    upload_expire_seconds: int
    max_concurrent_uploads: int


MAX_SAFE_INTEGER = 9_007_199_254_740_991
MAX_SIGNED_INT = 2_147_483_647

RUNTIME_SETTING_DEFINITIONS: tuple[RuntimeSettingDefinition, ...] = (
    RuntimeSettingDefinition(
        key="MAX_UPLOAD_FILE_SIZE",
        default_value=104_857_600,
        label="单文件大小上限",
        group="上传限制",
        unit="字节",
        description="限制单个文件的原始明文大小。",
        allow_zero=True,
        min_value=0,
        max_value=MAX_SAFE_INTEGER,
    ),
    RuntimeSettingDefinition(
        key="MAX_PASTE_TOTAL_UPLOAD_SIZE",
        default_value=1_073_741_824,
        label="单 Paste 文件总量",
        group="上传限制",
        unit="字节",
        description="限制每个 Paste 的已上传文件与未过期上传会话总大小。",
        allow_zero=True,
        min_value=0,
        max_value=MAX_SAFE_INTEGER,
    ),
    RuntimeSettingDefinition(
        key="MAX_CHUNK_SIZE",
        default_value=2_097_152,
        label="分片大小上限",
        group="上传限制",
        unit="字节",
        description="限制客户端请求的单个上传分片明文大小。",
        allow_zero=False,
        min_value=1,
        max_value=MAX_SIGNED_INT,
    ),
    RuntimeSettingDefinition(
        key="UPLOAD_EXPIRE_SECONDS",
        default_value=3_600,
        label="上传会话过期",
        group="上传限制",
        unit="秒",
        description="未完成的上传会话在该时长后过期。",
        allow_zero=False,
        min_value=1,
        max_value=MAX_SIGNED_INT,
    ),
    RuntimeSettingDefinition(
        key="MAX_CONCURRENT_UPLOADS",
        default_value=2_000,
        label="并发上传会话",
        group="上传限制",
        unit="个",
        description="限制全局未过期上传会话数量。",
        allow_zero=True,
        min_value=0,
        max_value=MAX_SIGNED_INT,
    ),
    RuntimeSettingDefinition(
        key="COLLAB_ROOM_MAX_MEMBERS",
        default_value=20,
        label="协作房间人数",
        group="协作房间",
        unit="人",
        description="新建协作房间的默认最大成员数。",
        allow_zero=False,
        min_value=2,
        max_value=100,
    ),
)

RUNTIME_SETTING_DEFINITION_BY_KEY = {
    definition.key: definition for definition in RUNTIME_SETTING_DEFINITIONS
}


class RuntimeSettingsService:
    """运行配置读取与更新。"""

    @staticmethod
    def ensure_defaults(db: Session, *, commit: bool = True) -> None:
        existing_keys = {
            str(key)
            for (key,) in db.query(RuntimeSetting.key)
            .filter(RuntimeSetting.key.in_(RUNTIME_SETTING_DEFINITION_BY_KEY.keys()))
            .all()
        }
        now = datetime.now(UTC)
        for definition in RUNTIME_SETTING_DEFINITIONS:
            if definition.key in existing_keys:
                continue
            db.add(
                RuntimeSetting(
                    key=definition.key,
                    value=str(definition.default_value),
                    updated_at=now,
                    updated_by=None,
                )
            )
        if commit:
            db.commit()

    @staticmethod
    def _validate_value(definition: RuntimeSettingDefinition, value: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{definition.label}必须是整数")
        if value == 0 and not definition.allow_zero:
            raise ValueError(f"{definition.label}必须大于等于 {definition.min_value}")
        if value < definition.min_value:
            raise ValueError(f"{definition.label}必须大于等于 {definition.min_value}")
        if definition.max_value is not None and value > definition.max_value:
            raise ValueError(f"{definition.label}必须小于等于 {definition.max_value}")
        return value

    @staticmethod
    def _row_value(definition: RuntimeSettingDefinition, row: RuntimeSetting | None) -> int:
        if row is None:
            return definition.default_value
        try:
            value = int(str(row.value).strip())
        except (TypeError, ValueError):
            return definition.default_value
        try:
            return RuntimeSettingsService._validate_value(definition, value)
        except ValueError:
            return definition.default_value

    @staticmethod
    def _rows_by_key(db: Session) -> dict[str, RuntimeSetting]:
        rows = (
            db.query(RuntimeSetting)
            .filter(RuntimeSetting.key.in_(RUNTIME_SETTING_DEFINITION_BY_KEY.keys()))
            .all()
        )
        return {str(row.key): row for row in rows}

    @staticmethod
    def list_settings(db: Session) -> list[RuntimeSettingItem]:
        rows_by_key = RuntimeSettingsService._rows_by_key(db)
        return [
            RuntimeSettingItem(
                key=definition.key,  # type: ignore[arg-type]
                value=RuntimeSettingsService._row_value(
                    definition, rows_by_key.get(definition.key)
                ),
                default_value=definition.default_value,
                label=definition.label,
                group=definition.group,
                unit=definition.unit,
                description=definition.description,
                allow_zero=definition.allow_zero,
                min_value=definition.min_value,
                max_value=definition.max_value,
            )
            for definition in RUNTIME_SETTING_DEFINITIONS
        ]

    @staticmethod
    def values(db: Session) -> dict[str, int]:
        rows_by_key = RuntimeSettingsService._rows_by_key(db)
        return {
            definition.key: RuntimeSettingsService._row_value(
                definition, rows_by_key.get(definition.key)
            )
            for definition in RUNTIME_SETTING_DEFINITIONS
        }

    @staticmethod
    def upload_settings(db: Session) -> UploadRuntimeSettings:
        values = RuntimeSettingsService.values(db)
        return UploadRuntimeSettings(
            max_upload_file_size=values["MAX_UPLOAD_FILE_SIZE"],
            max_paste_total_upload_size=values["MAX_PASTE_TOTAL_UPLOAD_SIZE"],
            max_chunk_size=values["MAX_CHUNK_SIZE"],
            upload_expire_seconds=values["UPLOAD_EXPIRE_SECONDS"],
            max_concurrent_uploads=values["MAX_CONCURRENT_UPLOADS"],
        )

    @staticmethod
    def collab_room_max_members(db: Session) -> int:
        return RuntimeSettingsService.values(db)["COLLAB_ROOM_MAX_MEMBERS"]

    @staticmethod
    def update_settings(
        db: Session,
        updates: list[RuntimeSettingUpdate],
        *,
        updated_by: int | None,
    ) -> list[RuntimeSettingItem]:
        if not updates:
            raise ValueError("请至少提交一个配置项")

        seen_keys: set[str] = set()
        normalized_updates: dict[str, int] = {}
        for update in updates:
            key = str(update.key)
            if key in seen_keys:
                raise ValueError(f"重复的配置项: {key}")
            seen_keys.add(key)

            definition = RUNTIME_SETTING_DEFINITION_BY_KEY.get(key)
            if definition is None:
                raise ValueError(f"不支持的配置项: {key}")

            normalized_updates[key] = RuntimeSettingsService._validate_value(
                definition, update.value
            )

        RuntimeSettingsService.ensure_defaults(db, commit=False)
        rows_by_key = RuntimeSettingsService._rows_by_key(db)
        now = datetime.now(UTC)
        for key, value in normalized_updates.items():
            row = rows_by_key.get(key)
            if row is None:
                row = RuntimeSetting(key=key)
                db.add(row)
            row.value = str(value)
            row.updated_at = now
            row.updated_by = updated_by

        db.commit()
        return RuntimeSettingsService.list_settings(db)
