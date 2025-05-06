from pydantic import BaseModel  # type:ignore

class ArticleInput(BaseModel):
    title: str
    content: str
