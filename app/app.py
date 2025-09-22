import os
from pathlib import Path
from fastapi import FastAPI, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

from database import get_db
from models import User, SearchQuery
from auth import authenticate_user, get_current_user, get_password_hash
from scraper import test_query

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


@app.get("/queries", response_class=HTMLResponse)
async def queries_page(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    queries = db.query(SearchQuery).filter(SearchQuery.user_id == current_user.id).all()
    return templates.TemplateResponse("queries.html", {"request": request, "user": current_user, "queries": queries})


@app.get("/queries/add", response_class=HTMLResponse)
async def add_query_form(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("query_form.html", {"request": request, "user": current_user, "mode": "add"})


@app.post("/queries/add")
async def add_query(request: Request, name: str = Form(...), url: str = Form(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = SearchQuery(name=name, url=url, user_id=current_user.id)
    db.add(query)
    db.commit()
    return RedirectResponse(url="/queries", status_code=303)


@app.get("/queries/{query_id}/edit", response_class=HTMLResponse)
async def edit_query_form(request: Request, query_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(SearchQuery).filter(SearchQuery.id == query_id, SearchQuery.user_id == current_user.id).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
    
    return templates.TemplateResponse("query_form.html", {"request": request, "user": current_user, "mode": "edit", "query": query})


@app.post("/queries/{query_id}/edit")
async def update_query(request: Request, query_id: int, name: str = Form(...), url: str = Form(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(SearchQuery).filter(SearchQuery.id == query_id, SearchQuery.user_id == current_user.id).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
    
    query.name = name
    query.url = url
    db.commit()
    return RedirectResponse(url="/queries", status_code=303)


@app.post("/queries/{query_id}/delete")
async def delete_query(request: Request, query_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(SearchQuery).filter(SearchQuery.id == query_id, SearchQuery.user_id == current_user.id).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
    
    db.delete(query)
    db.commit()
    return RedirectResponse(url="/queries", status_code=303)


@app.post("/queries/{query_id}/toggle")
async def toggle_query(request: Request, query_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(SearchQuery).filter(SearchQuery.id == query_id, SearchQuery.user_id == current_user.id).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
    
    query.is_active = not query.is_active
    db.commit()
    return RedirectResponse(url="/queries", status_code=303)


@app.post("/queries/test", response_class=HTMLResponse)
async def test_query_endpoint(request: Request, name: str = Form(...), url: str = Form(...), current_user: User = Depends(get_current_user)):
    # Create a temporary query object for testing
    test_query_obj = type('Query', (), {'name': name, 'url': url})()
    
    try:
        offers = test_query(url, limit=5)
        return templates.TemplateResponse("test_results.html", {
            "request": request, 
            "query": test_query_obj, 
            "offers": offers,
            "success": True
        })
    except Exception as e:
        return templates.TemplateResponse("test_results.html", {
            "request": request, 
            "query": test_query_obj, 
            "error": str(e),
            "success": False
        })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)