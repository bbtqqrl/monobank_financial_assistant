from pydantic import BaseModel


class CategoryNode(BaseModel):
    id: int
    name: str
    slug: str
    kind: str
    children: list["CategoryNode"] = []
