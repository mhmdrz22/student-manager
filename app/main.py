from fastapi import Depends, FastAPI, APIRouter, Request, HTTPException, Form, File, UploadFile
import shutil
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from pathlib import Path
from datetime import datetime

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

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return RedirectResponse(url="/login", status_code=302)
    # Default behavior for other HTTPExceptions
    return RedirectResponse(url="/", status_code=302)


# This is needed to serve HTML templates
templates = Jinja2Templates(directory="templates")

# The seed_database function is no longer called on startup
# from create_admin import seed_database

from .database import Base

@app.on_event("startup")
async def startup_event():
    # Create required directories
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("static", exist_ok=True) # Ensure static directory exists

    # Create DB and tables if they don't exist
    create_db_and_tables()

    # Seeding should be done via a separate script, not on startup.
    # The `create_admin.py` script can be used for initial setup.

    # Mount static files
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

from . import utils

@api_router.post("/articles", response_class=HTMLResponse)
async def submit_article(
    title: str = Form(...),
    summary: str = Form(...),
    content: str = Form(None),
    image_url: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_active_user)
):
    """
    Handles article submission from any logged-in user.
    """
    upload_dir = "uploads"

    # Save the file with a secure filename
    file_path = utils.save_upload_file(file, destination=upload_dir)

    db_article = models.Article(
        title=title,
        summary=summary,
        content=content,
        image_url=image_url,

        file_path=file_path, # Store the relative path
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
    image_url: str = Form(None),
    image_upload: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_role(["member", "manager"]))
):
    """Handles news submission from a logged-in user with member or manager role."""
    final_image_url = image_url

    if image_upload and image_upload.filename:
        upload_dir = "uploads/images"
        os.makedirs(upload_dir, exist_ok=True)
        saved_path = utils.save_upload_file(image_upload, destination=upload_dir)
        # The path should be relative to the static mount point
        final_image_url = "/" + saved_path.replace("\\", "/")

    db_news = models.News(
        title=title,
        summary=summary,
        content=content,
        category=category,
        image_url=final_image_url,
        owner_id=current_user.id
    )
    db.add(db_news)
    db.commit()
    db.refresh(db_news)
    return RedirectResponse(url="/dashboard", status_code=302)


@api_router.post("/news/{news_id}/delete", response_class=HTMLResponse)
async def delete_news(
    news_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_role(["member", "manager"]))
):
    """Deletes a news item."""
    news_to_delete = db.query(models.News).filter(models.News.id == news_id).first()
    if not news_to_delete:
        raise HTTPException(status_code=404, detail="News not found")

    # Optional: Check if the user is the owner or a manager
    if news_to_delete.owner_id != current_user.id and current_user.role != 'manager':
        raise HTTPException(status_code=403, detail="Not authorized to delete this news")

    db.delete(news_to_delete)
    db.commit()
    return RedirectResponse(url="/news", status_code=302)

@api_router.post("/news/{news_id}/edit", response_class=HTMLResponse)
async def handle_edit_news(
    news_id: int,
    title: str = Form(...),
    summary: str = Form(...),
    content: str = Form(...),
    category: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_role(["member", "manager"]))
):
    """Handles the submission of the news edit form."""
    news_to_edit = db.query(models.News).filter(models.News.id == news_id).first()
    if not news_to_edit:
        raise HTTPException(status_code=404, detail="News not found")

    if news_to_edit.owner_id != current_user.id and current_user.role != 'manager':
        raise HTTPException(status_code=403, detail="Not authorized to edit this news")

    news_to_edit.title = title
    news_to_edit.summary = summary
    news_to_edit.content = content
    news_to_edit.category = category
    db.commit()

    return RedirectResponse(url=f"/news/{news_id}", status_code=302)

@api_router.post("/events", response_class=HTMLResponse)
async def create_event(
    title: str = Form(...),
    summary: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    location: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(None),
    image_url: str = Form(None),
    capacity: int = Form(None),
    registration_deadline: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_role(["member", "manager"]))
):
    """Handles event creation from a logged-in user with member or manager role."""
    try:
        start_time_obj = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
        end_time_obj = datetime.strptime(end_time, "%Y-%m-%dT%H:%M") if end_time else None
        registration_deadline_obj = datetime.strptime(registration_deadline, "%Y-%m-%dT%H:%M") if registration_deadline else None
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid date format. Please use YYYY-MM-DDTHH:MM.")

    db_event = models.Event(
        title=title,
        summary=summary,
        description=description,
        category=category,
        location=location,
        start_time=start_time_obj,
        end_time=end_time_obj,
        image_url=image_url,
        capacity=capacity,
        registration_deadline=registration_deadline_obj,
        owner_id=current_user.id
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return RedirectResponse(url="/events", status_code=302)


@api_router.post("/events/{event_id}/edit", response_class=HTMLResponse)
async def handle_edit_event(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_active_user),
    title: str = Form(...),
    summary: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    location: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(None),
    image_url: str = Form(None),
    capacity: int = Form(None),
    registration_deadline: str = Form(None)
):
    """Handles the submission of the event edit form."""
    event_to_edit = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event_to_edit:
        raise HTTPException(status_code=404, detail="Event not found")

    # Authorization check
    is_manager = current_user.role == 'manager'
    is_owner_member = current_user.role == 'member' and event_to_edit.owner_id == current_user.id

    if not (is_manager or is_owner_member):
        raise HTTPException(status_code=403, detail="You do not have permission to edit this event.")

    # Update the event fields
    try:
        event_to_edit.start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
        event_to_edit.end_time = datetime.strptime(end_time, "%Y-%m-%dT%H:%M") if end_time else None
        event_to_edit.registration_deadline = datetime.strptime(registration_deadline, "%Y-%m-%dT%H:%M") if registration_deadline else None
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid date format. Please use YYYY-MM-DDTHH:MM.")

    event_to_edit.title = title
    event_to_edit.summary = summary
    event_to_edit.description = description
    event_to_edit.category = category
    event_to_edit.location = location
    event_to_edit.image_url = image_url
    event_to_edit.capacity = capacity

    db.commit()

    return RedirectResponse(url=f"/events/{event_id}", status_code=302)


@api_router.post("/events/{event_id}/delete", response_class=HTMLResponse)
async def delete_event(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_active_user)
):
    """Handles the deletion of an event."""
    event_to_delete = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event_to_delete:
        raise HTTPException(status_code=404, detail="Event not found")

    # Authorization check
    is_manager = current_user.role == 'manager'
    is_owner_member = current_user.role == 'member' and event_to_delete.owner_id == current_user.id

    if not (is_manager or is_owner_member):
        raise HTTPException(status_code=403, detail="You do not have permission to delete this event.")

    db.delete(event_to_delete)
    db.commit()

    return RedirectResponse(url="/events", status_code=302)


@api_router.post("/news/{news_id}/approve", response_class=HTMLResponse)
def approve_news(news_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(security.require_role(["manager"]))):
    """Approves a news item, setting its 'status' to 'approved'."""
    news_to_approve = db.query(models.News).filter(models.News.id == news_id).first()
    if not news_to_approve:
        raise HTTPException(status_code=404, detail="News not found")

    news_to_approve.status = "approved"
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)


@api_router.post("/news/{news_id}/reject", response_class=HTMLResponse)
def reject_news(news_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(security.require_role(["manager"]))):
    """Rejects a news item by deleting it."""
    news_to_reject = db.query(models.News).filter(models.News.id == news_id).first()
    if not news_to_reject:
        raise HTTPException(status_code=404, detail="News not found")

    db.delete(news_to_reject)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)


@api_router.post("/articles/{article_id}/approve", response_class=HTMLResponse)
def approve_article(article_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(security.require_role(["manager"]))):
    """Approves an article, setting its 'status' to 'approved'."""
    article_to_approve = db.query(models.Article).filter(models.Article.id == article_id).first()
    if not article_to_approve:
        raise HTTPException(status_code=404, detail="Article not found")

    article_to_approve.status = "approved"
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)


@api_router.post("/articles/{article_id}/reject", response_class=HTMLResponse)
def reject_article(article_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(security.require_role(["manager"]))):
    """Rejects an article by deleting it."""
    article_to_reject = db.query(models.Article).filter(models.Article.id == article_id).first()
    if not article_to_reject:
        raise HTTPException(status_code=404, detail="Article not found")

    db.delete(article_to_reject)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)


@api_router.post("/events/{event_id}/approve", response_class=HTMLResponse)
def approve_event(event_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(security.require_role(["manager"]))):
    """Approves an event, setting its 'status' to 'approved'."""
    event_to_approve = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event_to_approve:
        raise HTTPException(status_code=404, detail="Event not found")

    event_to_approve.status = "approved"
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)


@api_router.post("/events/{event_id}/reject", response_class=HTMLResponse)
def reject_event(event_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(security.require_role(["manager"]))):
    """Rejects an event by deleting it."""
    event_to_reject = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event_to_reject:
        raise HTTPException(status_code=404, detail="Event not found")

    db.delete(event_to_reject)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)


@api_router.post("/events/{event_id}/register", response_class=HTMLResponse)
def register_for_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_active_user)
):
    """Registers the current user for an event."""
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.registration_deadline and datetime.now(event.registration_deadline.tzinfo) > event.registration_deadline:
        raise HTTPException(status_code=400, detail="Registration deadline has passed.")

    if event.capacity and len(event.registrants) >= event.capacity:
        raise HTTPException(status_code=400, detail="Event is full.")

    if current_user in event.registrants:
        raise HTTPException(status_code=400, detail="User is already registered for this event.")

    event.registrants.append(current_user)
    db.commit()

    return RedirectResponse(url=f"/events/{event_id}", status_code=302)


@api_router.post("/events/{event_id}/unregister", response_class=HTMLResponse)
def unregister_from_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_active_user)
):
    """Unregisters the current user from an event."""
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if current_user not in event.registrants:
        raise HTTPException(status_code=400, detail="User is not registered for this event.")

    event.registrants.remove(current_user)
    db.commit()

    return RedirectResponse(url=f"/events/{event_id}", status_code=302)


app.include_router(api_router)

from sqlalchemy.orm import joinedload

# --- Frontend Serving ---

@app.get("/", response_class=HTMLResponse)

async def read_root(request: Request, db: Session = Depends(get_db), user: models.User = Depends(security.try_get_current_active_user)):
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
async def news_detail_page(request: Request, news_id: int, db: Session = Depends(get_db), user: models.User = Depends(security.try_get_current_active_user)):
    """Serves the page for a single news article."""
    news_item = db.query(models.News).options(joinedload(models.News.owner)).filter(models.News.id == news_id, models.News.status == "approved").first()
    if not news_item:
        raise HTTPException(status_code=404, detail="News not found")
    return templates.TemplateResponse("news_detail.html", {"request": request, "news": news_item, "user": user})

@app.get("/news/{news_id}/edit", response_class=HTMLResponse)
async def edit_news_page(
    request: Request,
    news_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.require_role(["member", "manager"]))
):
    """Serves the page to edit a news article."""
    news_item = db.query(models.News).filter(models.News.id == news_id).first()
    if not news_item:
        raise HTTPException(status_code=404, detail="News not found")

    if news_item.owner_id != current_user.id and current_user.role != 'manager':
        raise HTTPException(status_code=403, detail="Not authorized to edit this news")

    return templates.TemplateResponse("edit_news.html", {"request": request, "news": news_item})

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

@app.get("/events/new", response_class=HTMLResponse)
async def create_event_form(
    request: Request,
    current_user: models.User = Depends(security.require_role(["member", "manager"]))
):
    """Serves the page with a form to create a new event."""
    return templates.TemplateResponse("create_event.html", {"request": request, "user": current_user})


@app.get("/events/{event_id}/edit", response_class=HTMLResponse)
async def edit_event_form(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_active_user)
):
    """Serves the page with a form to edit an existing event."""
    event = db.query(models.Event).options(joinedload(models.Event.owner)).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Authorization check
    is_manager = current_user.role == 'manager'
    # Members can only edit their own events
    is_owner_member = current_user.role == 'member' and event.owner_id == current_user.id

    if not (is_manager or is_owner_member):
        raise HTTPException(status_code=403, detail="You do not have permission to edit this event.")

    return templates.TemplateResponse("edit_event.html", {"request": request, "event": event, "user": current_user})


@app.get("/events", response_class=HTMLResponse)
async def events_list_page(request: Request, db: Session = Depends(get_db), user: models.User = Depends(security.try_get_current_active_user)):
    """Serves the page with a list of all events."""
    events = db.query(models.Event).options(joinedload(models.Event.owner)).filter(models.Event.status == "approved").order_by(models.Event.start_time.desc()).all()
    return templates.TemplateResponse("events_list.html", {"request": request, "events_list": events, "user": user})

@app.get("/events/{event_id}", response_class=HTMLResponse)
async def event_detail_page(request: Request, event_id: int, db: Session = Depends(get_db), user: models.User = Depends(security.try_get_current_active_user)):
    """Serves the page for a single event."""
    event = db.query(models.Event).options(joinedload(models.Event.owner), joinedload(models.Event.registrants)).filter(models.Event.id == event_id, models.Event.status == "approved").first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    deadline_passed = False
    if event.registration_deadline:
        # Make sure 'now' is timezone-aware if the deadline is
        deadline_passed = datetime.now(event.registration_deadline.tzinfo) > event.registration_deadline

    return templates.TemplateResponse("event_detail.html", {
        "request": request,
        "event": event,
        "user": user,
        "deadline_passed": deadline_passed
    })

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
async def dashboard_page(request: Request, db: Session = Depends(get_db), user: models.User = Depends(security.get_current_active_user)):

    """
    Serves the user dashboard page.
    This route is now protected by the get_current_active_user dependency.
    If the user is a manager, it also fetches the list of all users and pending articles.
    """
    user_list = []
    pending_articles = []
    pending_news = []
    pending_events = []

    if user.role == 'manager':
        user_list = db.query(models.User).all()
        pending_articles = db.query(models.Article).options(joinedload(models.Article.owner)).filter(models.Article.status == "pending").all()
        pending_news = db.query(models.News).options(joinedload(models.News.owner)).filter(models.News.status == "pending").all()
        pending_events = db.query(models.Event).options(joinedload(models.Event.owner)).filter(models.Event.status == "pending").all()


    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "user_list": user_list,
        "pending_articles": pending_articles,
        "pending_news": pending_news,
        "pending_events": pending_events
    })


# The uvicorn command should be used to run the app, for example:
# uvicorn app.main:app --reload
