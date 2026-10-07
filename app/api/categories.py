from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.repositories.category import CategoryRepository
from app.schemas.category import CategoryNode

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=list[CategoryNode])
async def list_categories(
    kind: Literal["expense", "income", "transfer", "unknown"] | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Active categories as a tree: top-level categories with their children."""
    categories = await CategoryRepository(db).get_selectable_categories(kinds=(kind,) if kind else None)

    nodes = {c.id: CategoryNode(id=c.id, name=c.name, slug=c.slug, kind=c.kind) for c in categories}
    roots: list[CategoryNode] = []
    for c in categories:
        parent = nodes.get(c.parent_id) if c.parent_id else None
        (parent.children if parent else roots).append(nodes[c.id])
    return roots
