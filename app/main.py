from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from pathlib import Path

from .database import create_db_and_tables

# Create the database and tables on startup
create_db_and_tables()

app = FastAPI(
    title="Scientific Association System",
    description="A system for managing articles, news, and scientific events.",
    version="0.1.0"
)

# Define the base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# This is needed to serve HTML templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@app.on_event("startup")
async def startup_event():
    # Mount the static files directory using an absolute path
    # This is done in a startup event to avoid issues with the reloader.
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# API Router for versioning
api_router = APIRouter(prefix="/api/v1")


# --- API Endpoints (Placeholders) ---

@api_router.post("/register")
async def register_user():
    """Placeholder for user registration logic."""
    return {"message": "User registration endpoint"}

@api_router.post("/login")
async def login_user():
    """Placeholder for user login logic."""
    return {"message": "User login endpoint"}

@api_router.post("/articles")
async def submit_article():
    """Placeholder for article submission logic."""
    return {"message": "Article submission endpoint"}

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
async def read_root(request: Request):
    """Serves the main page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Serves the registration page."""
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serves the login page."""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Serves the user dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


# The uvicorn command should be used to run the app, for example:
# uvicorn app.main:app --reload
