from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.settings import Settings
from .auth import UserMaybe

router = APIRouter(tags=["admin"])
settings = Settings()
templates = Jinja2Templates(directory=str(settings.templates_directory))

@router.get("/admin", response_class=HTMLResponse)
async def admin_ui(user: UserMaybe, request: Request):
    """Return a simple HTML admin UI shell."""
    return templates.TemplateResponse("admin.html", {"request": request})

