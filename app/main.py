from fastapi import Depends, FastAPI, APIRouter, Request, HTTPException, Form, File, UploadFile
import shutil
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
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# API Router for versioning
api_router = APIRouter(prefix="/api/v1")


# --- API Endpoints (Placeholders) ---

@api_router.post("/register", response_class=HTMLResponse)
def register_user(
    request: Request,
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
        return templates.TemplateResponse("register.html", {"request": request, "error": "Username already registered"})

    db_user_email = db.query(models.User).filter(models.User.email == email).first()
    if db_user_email:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Email already registered"})

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
    content: str = Form(None),
    image_url: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_role(["member", "manager"]))
):
    """
    Handles article submission from a logged-in user with member or manager role.
    """
    # Create uploads directory if it doesn't exist
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)

    # Save the file
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    db_article = models.Article(
        title=title,
        summary=summary,
        content=content,
        image_url=image_url,
        file_path=file_path,
        owner_id=current_user.id
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
        owner_id=current_user.id
    )
    db.add(db_news)
    db.commit()
    db.refresh(db_news)
    return RedirectResponse(url="/dashboard", status_code=302)

@api_router.post("/events", response_class=RedirectResponse)
async def create_event(
    title: str = Form(...),
    description: str = Form(...),
    date: str = Form(...),
    location: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_role(["manager"]))
):
    """Handles event creation from a form (Admin only)."""
    db_event = models.Event(
        title=title,
        description=description,
        date=date,
        location=location,
        owner_id=current_user.id
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return RedirectResponse(url="/dashboard", status_code=302)


app.include_router(api_router)

from sqlalchemy.orm import joinedload

# --- Frontend Serving ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db), user: models.User = Depends(security.get_current_user_from_cookie)):
    """Serves the main page and displays the latest news."""
    news_items = db.query(models.News).options(joinedload(models.News.owner)).filter(models.News.status == "approved").order_by(models.News.created_at.desc()).limit(3).all()
    return templates.TemplateResponse("index.html", {"request": request, "news_list": news_items, "user": user})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Serves the registration page."""
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serves the login page."""
    return templates.TemplateResponse("login.html", {"request": request})

from fastapi import Response

@app.get("/logout")
async def logout(response: Response):
    """Logs the user out by clearing the access token cookie."""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="access_token")
    return response

@app.get("/news", response_class=HTMLResponse)
async def news_list_page(request: Request, db: Session = Depends(get_db)):
    """Serves the page with a list of all news articles."""
    news_items = db.query(models.News).options(joinedload(models.News.owner)).filter(models.News.status == "approved").order_by(models.News.created_at.desc()).all()
    return templates.TemplateResponse("news_list.html", {"request": request, "news_list": news_items})

@app.get("/news/{news_id}", response_class=HTMLResponse)
async def news_detail_page(request: Request, news_id: int, db: Session = Depends(get_db)):
    """Serves the page for a single news article."""
    news_item = db.query(models.News).options(joinedload(models.News.owner)).filter(models.News.id == news_id, models.News.status == "approved").first()
    if not news_item:
        raise HTTPException(status_code=404, detail="News not found")
    return templates.TemplateResponse("news_detail.html", {"request": request, "news": news_item})

@app.get("/articles", response_class=HTMLResponse)
async def articles_list_page(request: Request, db: Session = Depends(get_db)):
    """Serves the page with a list of all articles."""
    articles = db.query(models.Article).options(joinedload(models.Article.owner)).filter(models.Article.status == "approved").order_by(models.Article.created_at.desc()).all()
    return templates.TemplateResponse("articles_list.html", {"request": request, "articles_list": articles})

@app.get("/articles/{article_id}", response_class=HTMLResponse)
async def article_detail_page(request: Request, article_id: int, db: Session = Depends(get_db)):
    """Serves the page for a single article."""
    article = db.query(models.Article).options(joinedload(models.Article.owner)).filter(models.Article.id == article_id, models.Article.status == "approved").first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return templates.TemplateResponse("article_detail.html", {"request": request, "article": article})

@app.get("/events", response_class=HTMLResponse)
async def events_list_page(request: Request, db: Session = Depends(get_db)):
    """Serves the page with a list of all events."""
    events = db.query(models.Event).order_by(models.Event.date.desc()).all()
    return templates.TemplateResponse("events_list.html", {"request": request, "events_list": events})

@app.get("/events/{event_id}", response_class=HTMLResponse)
async def event_detail_page(request: Request, event_id: int, db: Session = Depends(get_db)):
    """Serves the page for a single event."""
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return templates.TemplateResponse("event_detail.html", {"request": request, "event": event})

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

@app.post("/admin/articles/{article_id}/approve", response_class=RedirectResponse)
async def approve_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_role(["manager"]))
):
    article = db.query(models.Article).filter(models.Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    article.status = "approved"
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)

@app.post("/admin/articles/{article_id}/reject", response_class=RedirectResponse)
async def reject_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_role(["manager"]))
):
    article = db.query(models.Article).filter(models.Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    article.status = "rejected"
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)

@app.post("/admin/news/{news_id}/approve", response_class=RedirectResponse)
async def approve_news(
    news_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_role(["manager"]))
):
    news_item = db.query(models.News).filter(models.News.id == news_id).first()
    if not news_item:
        raise HTTPException(status_code=404, detail="News not found")
    news_item.status = "approved"
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)

@app.post("/admin/news/{news_id}/reject", response_class=RedirectResponse)
async def reject_news(
    news_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_role(["manager"]))
):
    news_item = db.query(models.News).filter(models.News.id == news_id).first()
    if not news_item:
        raise HTTPException(status_code=404, detail="News not found")
    news_item.status = "rejected"
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_active_user)
):
    """
    Serves the user dashboard page.
    This route is now protected.
    If the user is a manager, it also fetches the list of all users.
    """
    user_list = []
    pending_articles = []
    pending_news = []
    if user.token_role == 'manager':
        user_list = db.query(models.User).all()
        pending_articles = db.query(models.Article).filter(models.Article.status == 'pending').all()
        pending_news = db.query(models.News).filter(models.News.status == 'pending').all()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "user_list": user_list,
        "pending_articles": pending_articles,
        "pending_news": pending_news
    })


# The uvicorn command should be used to run the app, for example:
# uvicorn app.main:app --reload
