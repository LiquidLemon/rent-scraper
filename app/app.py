import os
from pathlib import Path
from fastapi import FastAPI, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

from database import get_db
from models import User
from auth import authenticate_user, get_current_user, get_password_hash

app = FastAPI(title="Rent Scraper")

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "your-secret-key-change-this"))

# Static files and templates
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": current_user})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})
    
    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=303)


@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)