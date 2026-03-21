"""
安装向导控制器
"""

import os
import re
import secrets
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Lock

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None  # type: ignore[assignment]

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.init_db import create_tables
from app.schemas.install import (
    InstallContextResponse,
    InstallEnvItem,
    InstallErrorResponse,
    InstallSetupRequest,
    InstallSetupResponse,
)
from app.schemas.user import UserCreateRequest
from app.services.install_state_service import (
    ENV_FILE,
    InstallState,
    InstallStateService,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/api/install", tags=["安装"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE_FILE = PROJECT_ROOT / ".env.example"
ENV_ASSIGNMENT_PATTERN = re.compile(r"^([A-Z][A-Z0-9_]*)\s*=\s*(.*)$")
SETUP_LOCK_FILE = PROJECT_ROOT / ".install.setup.lock"
REQUIRED_ENV_KEYS = {
    "DATABASE_URL",
    "SECRET_KEY",
    "MEMBER_TOKEN_SECRET_KEY",
    "INTERNAL_TOKEN",
}
ADVANCED_ENV_KEYS = {
    "SECRET_KEY",
    "MEMBER_TOKEN_SECRET_KEY",
    "INTERNAL_TOKEN",
    "DEBUG",
    "ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "REFRESH_TOKEN_EXPIRE_DAYS",
    "PBKDF2_ITERATIONS",
    "SALT_LENGTH",
    "ENCRYPTION_KEY_LENGTH",
    "SESSION_KEY_LENGTH",
    "MAX_UPLOAD_FILE_SIZE",
    "MAX_PASTE_TOTAL_UPLOAD_SIZE",
    "MAX_CHUNK_SIZE",
    "DATA_DIR",
    "VERSION",
    "UPLOAD_EXPIRE_SECONDS",
    "MAX_CONCURRENT_UPLOADS",
    "COLLAB_ROOM_MAX_MEMBERS",
}
PLACEHOLDER_SECRET_VALUES = {
    "SECRET_KEY": "your-secret-key-change-this-in-production",
    "MEMBER_TOKEN_SECRET_KEY": "change-this-member-token-secret-key-in-production",
    "INTERNAL_TOKEN": "change-this-internal-token-in-production",
}
_SETUP_THREAD_LOCK = Lock()
PROCESS_START_UNIX_TIMESTAMP = time.time()
RESTART_REQUIRED_DETAIL = "检测到 .env 已变更，请先重启后端服务后继续安装"
DATABASE_CONNECTION_TIMEOUT_SECONDS = 5
_RUNTIME_RESTART_REQUIRED = False


def _mark_restart_required() -> None:
    global _RUNTIME_RESTART_REQUIRED
    _RUNTIME_RESTART_REQUIRED = True


def _env_file_changed_after_process_start() -> bool:
    if not ENV_FILE.exists():
        return False
    try:
        return ENV_FILE.stat().st_mtime > PROCESS_START_UNIX_TIMESTAMP
    except OSError:
        return False


def _is_restart_required() -> bool:
    return _RUNTIME_RESTART_REQUIRED or _env_file_changed_after_process_start()


def _strip_quotes(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and (
        (v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")
    ):
        return v[1:-1]
    return v


def _to_env_item(
    key: str,
    value: str,
    *,
    group: str | None,
    comment_lines: list[str],
) -> InstallEnvItem:
    return InstallEnvItem(
        key=key,
        default_value=_strip_quotes(value),
        comment="\n".join(comment_lines) if comment_lines else None,
        required=key in REQUIRED_ENV_KEYS,
        advanced=key in ADVANCED_ENV_KEYS,
        group=group,
    )


def _split_value_and_inline_comment(raw_value: str) -> tuple[str, str | None]:
    in_single_quote = False
    in_double_quote = False
    escape_next = False

    for index, char in enumerate(raw_value):
        if escape_next:
            escape_next = False
            continue

        if char == "\\" and in_double_quote:
            escape_next = True
            continue

        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            continue

        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            continue

        if char != "#" or in_single_quote or in_double_quote:
            continue

        previous_char = raw_value[index - 1] if index > 0 else ""
        if index == 0 or previous_char.isspace():
            value = raw_value[:index].rstrip()
            inline_comment = raw_value[index + 1 :].strip()
            return value, inline_comment or None

    return raw_value.strip(), None


def _load_env_template() -> list[InstallEnvItem]:
    if not ENV_EXAMPLE_FILE.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="缺少 .env.example，无法完成安装",
        )

    items: list[InstallEnvItem] = []
    pending_comments: list[str] = []
    current_group: str | None = None
    can_update_group = True

    for raw_line in ENV_EXAMPLE_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            pending_comments = []
            can_update_group = True
            continue

        if line.startswith("#"):
            payload = line[1:].strip()
            match = ENV_ASSIGNMENT_PATTERN.match(payload)
            if match is None:
                if can_update_group and payload:
                    current_group = payload
                else:
                    pending_comments.append(payload)
                can_update_group = False
                continue

            key, raw_value = match.group(1), match.group(2)
            value, inline_comment = _split_value_and_inline_comment(raw_value)
            comment_lines = pending_comments.copy()
            if inline_comment:
                comment_lines.append(inline_comment)
            items.append(
                _to_env_item(
                    key,
                    value,
                    group=current_group,
                    comment_lines=comment_lines,
                )
            )
            pending_comments = []
            can_update_group = False
            continue

        match = ENV_ASSIGNMENT_PATTERN.match(line)
        if match is None:
            can_update_group = False
            continue

        key, raw_value = match.group(1), match.group(2)
        value, inline_comment = _split_value_and_inline_comment(raw_value)
        comment_lines = pending_comments.copy()
        if inline_comment:
            comment_lines.append(inline_comment)
        items.append(
            _to_env_item(
                key,
                value,
                group=current_group,
                comment_lines=comment_lines,
            )
        )
        pending_comments = []
        can_update_group = False

    return items


def _build_install_context(
    state: InstallState,
    *,
    fail_on_template_error: bool,
) -> InstallContextResponse:
    restart_required = _is_restart_required()
    env_template: list[InstallEnvItem] = []
    if not state.env_exists:
        if fail_on_template_error:
            env_template = _load_env_template()
        else:
            try:
                env_template = _load_env_template()
            except HTTPException:
                env_template = []

    return InstallContextResponse(
        needs_install=state.needs_install,
        env_exists=state.env_exists,
        admin_exists=state.admin_exists,
        env_template=env_template,
        restart_required=restart_required,
        restart_message=RESTART_REQUIRED_DETAIL if restart_required else None,
    )


def _format_env_value(value: str) -> str:
    v = value.strip()
    if v == "":
        return '""'

    if re.fullmatch(r"[A-Za-z0-9_./:@+\-]+", v):
        return v

    escaped = v.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _validate_env_values(
    template: list[InstallEnvItem], env_values: dict[str, str]
) -> None:
    template_keys = {item.key for item in template}
    unknown_keys = sorted(set(env_values.keys()) - template_keys)
    if unknown_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"存在未知环境变量键: {', '.join(unknown_keys)}",
        )

    missing_required_keys = []
    for item in template:
        value = env_values.get(item.key, item.default_value)
        if item.required and value.strip() == "":
            missing_required_keys.append(item.key)

    if missing_required_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"以下环境变量不能为空: {', '.join(missing_required_keys)}",
        )

    invalid_multiline_keys = []
    for item in template:
        value = env_values.get(item.key, item.default_value)
        if "\n" in value or "\r" in value:
            invalid_multiline_keys.append(item.key)

    if invalid_multiline_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"以下环境变量不允许包含换行: {', '.join(invalid_multiline_keys)}",
        )


def _resolve_database_url(
    template: list[InstallEnvItem],
    env_values: dict[str, str],
) -> str:
    for item in template:
        if item.key != "DATABASE_URL":
            continue
        return env_values.get(item.key, item.default_value).strip()
    return env_values.get("DATABASE_URL", "").strip()


def _compact_error_message(error: Exception) -> str:
    message = " ".join(str(error).split()).strip()
    if not message:
        return error.__class__.__name__
    if len(message) > 240:
        return f"{message[:240]}..."
    return message


def _validate_database_connection(
    template: list[InstallEnvItem],
    env_values: dict[str, str],
) -> None:
    database_url = _resolve_database_url(template, env_values)
    connect_args: dict[str, object] = {}

    try:
        backend_name = make_url(database_url).get_backend_name()
    except Exception:
        backend_name = ""

    if backend_name in {"mysql", "postgresql"}:
        connect_args["connect_timeout"] = DATABASE_CONNECTION_TIMEOUT_SECONDS

    engine_kwargs: dict[str, object] = {}
    if connect_args:
        engine_kwargs["connect_args"] = connect_args

    test_engine = create_engine(database_url, **engine_kwargs)
    try:
        with test_engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "DATABASE_URL 连通性检测失败，请检查地址、账号、密码和网络设置: "
                f"{_compact_error_message(e)}"
            ),
        ) from None
    finally:
        test_engine.dispose()


def _write_env_file(template: list[InstallEnvItem], env_values: dict[str, str]) -> None:
    output_lines: list[str] = []
    current_group: str | None = None

    for item in template:
        next_group = item.group.strip() if item.group else None
        if next_group != current_group:
            if output_lines and output_lines[-1] != "":
                output_lines.append("")
            if next_group:
                output_lines.append(f"# {next_group}")
            current_group = next_group

        if item.comment:
            for comment_line in item.comment.split("\n"):
                output_lines.append(f"# {comment_line}")

        raw_value = env_values.get(item.key, item.default_value)
        value = _replace_placeholder_secret(item.key, raw_value, item.default_value)
        output_lines.append(f"{item.key}={_format_env_value(value)}")

    _atomic_write_env_file("\n".join(output_lines).strip() + "\n")
    _mark_restart_required()


def _replace_placeholder_secret(key: str, value: str, default_value: str) -> str:
    if key not in PLACEHOLDER_SECRET_VALUES:
        return value

    normalized_value = value.strip()
    placeholder_value = PLACEHOLDER_SECRET_VALUES[key]
    if normalized_value in {placeholder_value, default_value.strip()}:
        return secrets.token_urlsafe(48)
    return value


def _atomic_write_env_file(content: str) -> None:
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=ENV_FILE.parent,
            prefix=f".{ENV_FILE.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_path = Path(temp_file.name)

        os.replace(temp_path, ENV_FILE)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


@contextmanager
def _setup_execution_lock() -> Iterator[None]:
    with _SETUP_THREAD_LOCK:
        lock_api = fcntl
        lock_file = None
        try:
            if lock_api is not None:
                SETUP_LOCK_FILE.touch(exist_ok=True)
                lock_file = SETUP_LOCK_FILE.open("r+", encoding="utf-8")
                lock_api.flock(lock_file.fileno(), lock_api.LOCK_EX)
            yield
        finally:
            if lock_file is not None:
                try:
                    if lock_api is not None:
                        lock_api.flock(lock_file.fileno(), lock_api.LOCK_UN)
                finally:
                    lock_file.close()
                    try:
                        SETUP_LOCK_FILE.unlink(missing_ok=True)
                    except OSError:
                        pass


def _install_already_done_response() -> JSONResponse:
    error_data = InstallErrorResponse(
        error="安装已完成",
        detail="安装已完成，不能重复执行 setup",
        status_code=status.HTTP_409_CONFLICT,
        code="INSTALL_ALREADY_DONE",
    )
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=error_data.model_dump(),
    )


def _install_restart_required_response() -> JSONResponse:
    error_data = InstallErrorResponse(
        error="请先重启服务",
        detail=RESTART_REQUIRED_DETAIL,
        status_code=status.HTTP_409_CONFLICT,
        code="INSTALL_RESTART_REQUIRED",
    )
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=error_data.model_dump(),
    )


@router.get("/context", response_model=InstallContextResponse)
async def get_install_context(db: Session = Depends(get_db)):
    state = InstallStateService.get_state(db)
    return _build_install_context(state, fail_on_template_error=False)


@router.post(
    "/setup",
    response_model=InstallSetupResponse,
    responses={status.HTTP_409_CONFLICT: {"model": InstallErrorResponse}},
)
async def run_install_setup(
    payload: InstallSetupRequest,
    db: Session = Depends(get_db),
) -> InstallSetupResponse | JSONResponse:
    with _setup_execution_lock():
        state = InstallStateService.get_state(db, force_refresh=True)
        if not state.needs_install:
            return _install_already_done_response()

        if _is_restart_required():
            return _install_restart_required_response()

        context_data = _build_install_context(state, fail_on_template_error=True)
        env_created = False
        admin_created = False

        if not state.env_exists:
            _validate_env_values(context_data.env_template, payload.env_values)
            _validate_database_connection(context_data.env_template, payload.env_values)
            _write_env_file(context_data.env_template, payload.env_values)
            env_created = True
            InstallStateService.refresh_state(db)
            return InstallSetupResponse(
                message="已生成 .env，请重启后继续安装",
                env_created=True,
                admin_created=False,
                restart_required=True,
            )

        if not state.admin_exists:
            if not payload.admin_email or not payload.admin_password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="请填写管理员邮箱和密码",
                )

            try:
                create_tables()
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"数据库表初始化失败: {e}",
                ) from None

            try:
                UserService.create_user(
                    db,
                    UserCreateRequest(
                        email=payload.admin_email,
                        password=payload.admin_password,
                        role="admin",
                    ),
                )
                admin_created = True
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                ) from None

        actions: list[str] = []
        if admin_created:
            actions.append("已创建管理员")

        InstallStateService.refresh_state(db)
        message = "，".join(actions) if actions else "安装步骤已跳过"
        return InstallSetupResponse(
            message=message,
            env_created=env_created,
            admin_created=admin_created,
            restart_required=False,
        )
