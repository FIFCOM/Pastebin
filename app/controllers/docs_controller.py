"""
API 文档控制器 - 返回前端渲染所需的 Markdown 原文
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/api/docs", tags=["API 文档"])

DOCS_ROOT = Path(__file__).resolve().parents[1] / "docs" / "api"
DEFAULT_DOC_SLUG = "overview"
DOC_SLUGS = {
    "overview",
    "authentication",
    "paste-creation",
    "pastes-files",
    "account-security",
    "api-keys",
    "collaboration",
}


def _read_doc_markdown(slug: str) -> str:
    if slug not in DOC_SLUGS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在",
        )

    path = DOCS_ROOT / f"{slug}.md"
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在",
        )
    return path.read_text(encoding="utf-8")


@router.get("", response_class=PlainTextResponse)
async def get_default_doc() -> PlainTextResponse:
    """返回默认文档（overview）的 Markdown 原文。"""
    return PlainTextResponse(
        _read_doc_markdown(DEFAULT_DOC_SLUG), media_type="text/markdown"
    )


@router.get("/{slug}", response_class=PlainTextResponse)
async def get_doc_by_slug(slug: str) -> PlainTextResponse:
    """按 slug 返回对应文档的 Markdown 原文。"""
    return PlainTextResponse(_read_doc_markdown(slug), media_type="text/markdown")
