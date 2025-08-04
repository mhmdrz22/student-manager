from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class User(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

class ArticleBase(BaseModel):
    title: str
    summary: str | None = None
    content: str
    image_url: str | None = None

class ArticleCreate(ArticleBase):
    pass

class Article(ArticleBase):
    id: int
    owner_id: int
    published: bool
    created_at: datetime
    owner: "User"

    class Config:
        from_attributes = True


class NewsBase(BaseModel):
    title: str
    summary: str | None = None
    content: str
    image_url: str | None = None
    category: str | None = None

class NewsCreate(NewsBase):
    pass

class News(NewsBase):
    id: int
    owner_id: int
    published: bool
    created_at: datetime
    owner: "User"

    class Config:
        from_attributes = True
