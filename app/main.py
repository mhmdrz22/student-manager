from fastapi import Depends, FastAPI, APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from pathlib import Path

import os
from sqlalchemy.orm import Session
from . import models, schemas, security
from .database import SessionLocal, engine, create_db_and_tables, get_db

# This was moved to the startup event
# models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Scientific Association System",
    description="A system for managing articles, news, and scientific events.",
    version="0.1.0"
)


# This is needed to serve HTML templates
templates = Jinja2Templates(directory="templates")

from create_admin import seed_database

@app.on_event("startup")
async def startup_event():
    # Create DB and tables first
    create_db_and_tables()
    # Seed the database with admin user and sample data
    seed_database()
    # Then mount static files
    app.mount("/static", StaticFiles(directory="static"), name="static")

# API Router for versioning
api_router = APIRouter(prefix="/api/v1")


# --- API Endpoints (Placeholders) ---

@api_router.post("/register", response_class=HTMLResponse)
def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Handles user registration from a form.
    Hashes the password and saves the new user to the database.
    """
    db_user = db.query(models.User).filter(models.User.username == username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    db_user_email = db.query(models.User).filter(models.User.email == email).first()
    if db_user_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = security.get_password_hash(password)
    db_user = models.User(
        username=username,
        email=email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    # Redirect to login page after successful registration
    return RedirectResponse(url="/login", status_code=302)

@api_router.post("/login/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Handles user login and returns a JWT access token.
    """
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = security.create_access_token(user=user)

    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@api_router.post("/articles", response_class=HTMLResponse)
async def submit_article(
    title: str = Form(...),
    summary: str = Form(...),
    content: str = Form(...),
    image_url: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_role(["member", "manager"]))
):
    """
    Handles article submission from a logged-in user with member or manager role.
    """
    db_article = models.Article(
        title=title,
        summary=summary,
        content=content,
        image_url=image_url,
        owner_id=current_user.id,
        published=True # Or based on admin approval
    )
    db.add(db_article)
    db.commit()
    db.refresh(db_article)

    # Redirecting to the dashboard, perhaps with a success message in the future
    return RedirectResponse(url="/dashboard", status_code=302)

@api_router.post("/news")
async def submit_news(
    title: str = Form(...),
    summary: str = Form(...),
    content: str = Form(...),
    category: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_role(["member", "manager"]))
):
    """Handles news submission from a logged-in user with member or manager role."""
    db_news = models.News(
        title=title,
        summary=summary,
        content=content,
        category=category,
        owner_id=current_user.id,
        published=True # Or based on admin approval
    )
    db.add(db_news)
    db.commit()
    db.refresh(db_news)
    return RedirectResponse(url="/dashboard", status_code=302)

@api_router.post("/events")
async def create_event():
    """Placeholder for event creation logic (Admin only)."""
    return {"message": "Event creation endpoint"}


app.include_router(api_router)

from sqlalchemy.orm import joinedload

# --- Frontend Serving ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    """Serves the main page and displays the latest news."""
    user = None
    try:
        token = request.cookies.get("access_token")
        if token:
            token_value = token.split(" ")[1]
            user = security.get_current_user(token=token_value, db=db)
    except Exception:
        user = None # Fail silently if token is invalid

    news_items = db.query(models.News).options(joinedload(models.News.owner)).filter(models.News.published == True).order_by(models.News.created_at.desc()).limit(3).all()
    return templates.TemplateResponse("index.html", {"request": request, "news_list": news_items, "user": user})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Serves the registration page."""
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serves the login page."""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/logout")
async def logout(response: HTMLResponse):
    """Logs the user out by clearing the access token cookie."""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="access_token")
    return response

@app.get("/news", response_class=HTMLResponse)
async def news_list_page(request: Request, db: Session = Depends(get_db)):
    """Serves the page with a list of all news articles."""
    news_items = db.query(models.News).options(joinedload(models.News.owner)).filter(models.News.published == True).order_by(models.News.created_at.desc()).all()
    return templates.TemplateResponse("news_list.html", {"request": request, "news_list": news_items})

@app.get("/news/{news_id}", response_class=HTMLResponse)
async def news_detail_page(request: Request, news_id: int, db: Session = Depends(get_db)):
    """Serves the page for a single news article."""
    news_item = db.query(models.News).options(joinedload(models.News.owner)).filter(models.News.id == news_id, models.News.published == True).first()
    if not news_item:
        raise HTTPException(status_code=404, detail="News not found")
    return templates.TemplateResponse("news_detail.html", {"request": request, "news": news_item})

@app.get("/articles", response_class=HTMLResponse)
async def articles_list_page(request: Request, db: Session = Depends(get_db)):
    """Serves the page with a list of all articles."""
    articles = db.query(models.Article).options(joinedload(models.Article.owner)).filter(models.Article.published == True).order_by(models.Article.created_at.desc()).all()
    return templates.TemplateResponse("articles_list.html", {"request": request, "articles_list": articles})

@app.get("/articles/{article_id}", response_class=HTMLResponse)
async def article_detail_page(request: Request, article_id: int, db: Session = Depends(get_db)):
    """Serves the page for a single article."""
    article = db.query(models.Article).options(joinedload(models.Article.owner)).filter(models.Article.id == article_id, models.Article.published == True).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return templates.TemplateResponse("article_detail.html", {"request": request, "article": article})

# --- Admin/Manager Specific Endpoints ---

@app.get("/admin/users", response_model=list[schemas.User])
def list_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_role(["manager"]))
):
    """Lists all users. For managers only."""
    users = db.query(models.User).all()
    return users

@app.post("/admin/users/{user_id}/role")
def update_user_role(
    user_id: int,
    new_role: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_role(["manager"]))
):
    """Updates a user's role. For managers only."""
    if new_role not in ["user", "member", "manager"]:
        raise HTTPException(status_code=400, detail="Invalid role specified.")

    user_to_update = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found.")

    user_to_update.role = new_role
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: Session = Depends(get_db)):
    """
    Serves the user dashboard page.
    This route is now protected.
    If the user is a manager, it also fetches the list of all users.
    """
    try:
        token = request.cookies.get("access_token")
        token_value = token.split(" ")[1] if token else None
        if not token_value:
            return RedirectResponse(url="/login", status_code=302)

        user = security.get_current_user(token=token_value, db=db)

        user_list = []
        if user.token_role == 'manager':
            user_list = db.query(models.User).all()

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": user,
            "user_list": user_list
        })
    except Exception:
        return RedirectResponse(url="/login", status_code=302)


# The uvicorn command should be used to run the app, for example:
# uvicorn app.main:app --reload
