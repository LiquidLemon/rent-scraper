import os
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

from database import get_db
from models import User, SearchQuery, NotificationSetting
from auth import authenticate_user, get_current_user, get_password_hash
from scraper import test_query

app = FastAPI(title="Rent Scraper")

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "your-secret-key-change-this"))

# Static files and templates
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time (e.g., '5m ago') with local timezone."""
    if dt is None:
        return "Never"
    
    # Convert to local timezone
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = dt.replace(tzinfo=timezone.utc)
    
    local_dt = dt.astimezone()
    now = datetime.now(timezone.utc).astimezone()
    
    diff = now - local_dt
    total_seconds = int(diff.total_seconds())
    
    if total_seconds < 60:
        return f"{total_seconds}s ago"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        return f"{minutes}m ago"
    elif total_seconds < 86400:
        hours = total_seconds // 3600
        return f"{hours}h ago"
    else:
        days = total_seconds // 86400
        return f"{days}d ago"


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
    
    # Add formatted time information to each query
    for query in queries:
        if query.last_scraped_at:
            query.formatted_time = format_relative_time(query.last_scraped_at)
            # Also keep the absolute time in local timezone for display
            local_dt = query.last_scraped_at.replace(tzinfo=timezone.utc).astimezone()
            query.absolute_time = local_dt.strftime('%m/%d %H:%M')
        else:
            query.formatted_time = "Never"
            query.absolute_time = "Never"
        
        # Convert created_at to local timezone
        if query.created_at:
            created_local = query.created_at.replace(tzinfo=timezone.utc).astimezone()
            query.created_at_local = created_local.strftime('%Y-%m-%d %H:%M')
        else:
            query.created_at_local = "Unknown"
    
    return templates.TemplateResponse("queries.html", {"request": request, "user": current_user, "queries": queries})


@app.get("/queries/add", response_class=HTMLResponse)
async def add_query_form(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("query_form.html", {"request": request, "user": current_user, "mode": "add"})


@app.post("/queries/add")
async def add_query(request: Request, name: str = Form(...), url: str = Form(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = SearchQuery(name=name.strip(), url=url.strip(), user_id=current_user.id)
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
    
    query.name = name.strip()
    query.url = url.strip()
    db.commit()
    return RedirectResponse(url="/queries", status_code=303)


@app.post("/queries/{query_id}/delete")
async def delete_query(request: Request, query_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(SearchQuery).filter(SearchQuery.id == query_id, SearchQuery.user_id == current_user.id).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
    
    # First delete all offers related to this query
    from models import Offer
    offers_deleted = db.query(Offer).filter(Offer.query_id == query_id).delete()
    print(f"Deleted {offers_deleted} offers for query {query_id}")
    
    # Then delete the query itself
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
    # Create a temporary query object for testing (strip whitespace)
    clean_name = name.strip()
    clean_url = url.strip()
    test_query_obj = type('Query', (), {'name': clean_name, 'url': clean_url})()
    
    try:
        offers = test_query(clean_url, limit=5)
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


@app.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notifications = db.query(NotificationSetting).filter(NotificationSetting.user_id == current_user.id).all()
    return templates.TemplateResponse("notifications.html", {"request": request, "user": current_user, "notifications": notifications})


@app.get("/notifications/add", response_class=HTMLResponse)
async def add_notification_form(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("notification_form.html", {"request": request, "user": current_user, "mode": "add"})


@app.post("/notifications/add")
async def add_notification(request: Request, discord_webhook_url: str = Form(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notification = NotificationSetting(discord_webhook_url=discord_webhook_url.strip(), user_id=current_user.id)
    db.add(notification)
    db.commit()
    return RedirectResponse(url="/notifications", status_code=303)


@app.get("/notifications/{notification_id}/edit", response_class=HTMLResponse)
async def edit_notification_form(request: Request, notification_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notification = db.query(NotificationSetting).filter(NotificationSetting.id == notification_id, NotificationSetting.user_id == current_user.id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification setting not found")
    
    return templates.TemplateResponse("notification_form.html", {"request": request, "user": current_user, "mode": "edit", "notification": notification})


@app.post("/notifications/{notification_id}/edit")
async def update_notification(request: Request, notification_id: int, discord_webhook_url: str = Form(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notification = db.query(NotificationSetting).filter(NotificationSetting.id == notification_id, NotificationSetting.user_id == current_user.id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification setting not found")
    
    notification.discord_webhook_url = discord_webhook_url.strip()
    db.commit()
    return RedirectResponse(url="/notifications", status_code=303)


@app.post("/notifications/{notification_id}/delete")
async def delete_notification(request: Request, notification_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notification = db.query(NotificationSetting).filter(NotificationSetting.id == notification_id, NotificationSetting.user_id == current_user.id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification setting not found")
    
    db.delete(notification)
    db.commit()
    return RedirectResponse(url="/notifications", status_code=303)


@app.post("/notifications/{notification_id}/toggle")
async def toggle_notification(request: Request, notification_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notification = db.query(NotificationSetting).filter(NotificationSetting.id == notification_id, NotificationSetting.user_id == current_user.id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification setting not found")
    
    notification.is_active = not notification.is_active
    db.commit()
    return RedirectResponse(url="/notifications", status_code=303)


@app.post("/notifications/test", response_class=HTMLResponse)
async def test_notification_endpoint(request: Request, discord_webhook_url: str = Form(...), current_user: User = Depends(get_current_user)):
    import requests
    import json
    
    # Strip whitespace from webhook URL
    clean_webhook_url = discord_webhook_url.strip()
    
    try:
        # Send a test message to Discord
        payload = {
            "content": f"🏠 Test notification from Rent Scraper for user: {current_user.username}",
            "embeds": [{
                "title": "Test Notification",
                "description": "This is a test message to verify your Discord webhook is working correctly.",
                "color": 0x00ff00,  # Green color
                "footer": {"text": "Rent Scraper Test"}
            }]
        }
        
        response = requests.post(clean_webhook_url, 
                               json=payload, 
                               headers={'Content-Type': 'application/json'},
                               timeout=10)
        
        if response.status_code == 204:
            return templates.TemplateResponse("notification_test_results.html", {
                "request": request,
                "success": True,
                "message": "Test notification sent successfully! Check your Discord channel."
            })
        else:
            raise Exception(f"Discord returned status {response.status_code}: {response.text}")
            
    except requests.exceptions.Timeout:
        return templates.TemplateResponse("notification_test_results.html", {
            "request": request,
            "success": False,
            "error": "Request timed out. Please check your webhook URL."
        })
    except requests.exceptions.RequestException as e:
        return templates.TemplateResponse("notification_test_results.html", {
            "request": request,
            "success": False,
            "error": f"Network error: {str(e)}"
        })
    except Exception as e:
        return templates.TemplateResponse("notification_test_results.html", {
            "request": request,
            "success": False,
            "error": str(e)
        })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)