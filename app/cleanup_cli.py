import argparse
import logging
import sys

from app.core.database import SessionLocal
from app.services.cleanup_service import CleanupService

SUPPORTED_TASKS = [
    "expired_drafts",
    "expired_pastes",
    "expired_members",
    "expired_uploads",
    "expired_user_sessions",
    "expired_used_refresh_tokens",
]

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Material Bin cleanup tasks.")
    parser.add_argument(
        "tasks",
        nargs="*",
        choices=SUPPORTED_TASKS,
        help="Cleanup tasks to execute. Defaults to all tasks when omitted.",
    )
    parser.add_argument(
        "--list-tasks",
        action="store_true",
        help="Print supported cleanup task names and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_tasks:
        for task_name in SUPPORTED_TASKS:
            print(task_name)
        return 0

    selected_tasks = list(args.tasks) if args.tasks else SUPPORTED_TASKS

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    try:
        with SessionLocal() as db:
            result = CleanupService.execute_cleanup_tasks(db, selected_tasks)
    except Exception:
        logger.exception("cleanup execution failed")
        return 1

    for task_result in result.task_results:
        level = logging.INFO if task_result.success else logging.ERROR
        logger.log(
            level,
            "%s success=%s deleted=%s message=%s error=%s",
            task_result.task_name,
            task_result.success,
            task_result.deleted_count,
            task_result.message,
            task_result.error,
        )

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
