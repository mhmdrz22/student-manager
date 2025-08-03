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

@app.on_event("startup")
async def startup_event():
    # Create DB and tables first
    create_db_and_tables()
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
    access_token = security.create_access_token(
        data={"sub": user.username}
    )

    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@api_router.post("/articles", response_class=HTMLResponse)
async def submit_article(
    title: str = Form(...),
    content: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_active_user)
):
    """
    Handles article submission from a logged-in user.
    """
    db_article = models.Article(
        title=title,
        content=content,
        owner_id=current_user.id
    )
    db.add(db_article)
    db.commit()
    db.refresh(db_article)

    # Redirecting to the dashboard, perhaps with a success message in the future
    return RedirectResponse(url="/dashboard", status_code=302)

@api_router.post("/news")
async def submit_news():
    """Placeholder for news submission logic."""
    return {"message": "News submission endpoint"}

@api_router.post("/events")
async def create_event():
    """Placeholder for event creation logic (Admin only)."""
    return {"message": "Event creation endpoint"}


app.include_router(api_router)


# --- Frontend Serving ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    """Serves the main page and displays the latest news."""
    news_items = db.query(models.News).filter(models.News.published == True).order_by(models.News.id.desc()).limit(3).all()
    return templates.TemplateResponse("index.html", {"request": request, "news_list": news_items})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Serves the registration page."""
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serves the login page."""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/news/{news_id}", response_class=HTMLResponse)
async def news_detail_page(request: Request, news_id: int, db: Session = Depends(get_db)):
    """Serves the page for a single news article."""
    news_item = db.query(models.News).filter(models.News.id == news_id, models.News.published == True).first()
    if not news_item:
        raise HTTPException(status_code=404, detail="News not found")
    return templates.TemplateResponse("news_detail.html", {"request": request, "news": news_item})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: Session = Depends(get_db)):
    """
    Serves the user dashboard page.
    This route is now protected.
    """
    try:
        token = request.cookies.get("access_token")
        # The token is expected to be in the format "Bearer <token>"
        token_value = token.split(" ")[1] if token else None

        if not token_value:
            # Redirect to login if no token
            return RedirectResponse(url="/login", status_code=302)

        user = security.get_current_user(token=token_value, db=db)

        return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})
    except Exception:
        # If token is invalid or expired, or any other error occurs, redirect to login
        return RedirectResponse(url="/login", status_code=302)


# The uvicorn command should be used to run the app, for example:
# uvicorn app.main:app --reload
