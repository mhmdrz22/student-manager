from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    role: str

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class CommentBase(BaseModel):
    content: str

class CommentCreate(CommentBase):
    pass

class Comment(CommentBase):
    id: int
    owner_id: int
    created_at: datetime
    owner: User

    class Config:
        orm_mode = True

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
    status: str
    created_at: datetime
    owner: "User"

    class Config:
        orm_mode = True


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
    status: str
    created_at: datetime
    owner: "User"

    class Config:
        orm_mode = True


class EventBase(BaseModel):
    title: str
    description: str
    start_time: datetime
    end_time: Optional[datetime] = None
    location: str
    category: str
    capacity: Optional[int] = None
    registration_deadline: Optional[datetime] = None

class EventCreate(EventBase):
    pass

class Event(EventBase):
    id: int
    owner_id: int
    status: str
    created_at: datetime
    owner: "User"

    class Config:
        orm_mode = True
