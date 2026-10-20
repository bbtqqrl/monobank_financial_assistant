from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.category import CategoryRepository
from app.schemas.category import CategoryNode


class CategoryService:

    def __init__(self, db: AsyncSession):
        self.categories = CategoryRepository(db)

    async def tree(self, kind: str | None = None) -> list[CategoryNode]:
        categories = await self.categories.get_selectable_categories(kinds=(kind,) if kind else None)

        nodes = {c.id: CategoryNode(id=c.id, name=c.name, slug=c.slug, kind=c.kind) for c in categories}
        roots: list[CategoryNode] = []
        for c in categories:
            parent = nodes.get(c.parent_id) if c.parent_id else None
            (parent.children if parent else roots).append(nodes[c.id])
        return roots
