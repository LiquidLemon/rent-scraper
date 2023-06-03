from typing import Annotated, Optional
from urllib.parse import urlsplit

from fastapi import FastAPI, Form
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import RedirectResponse

from listing_spy.actions import ACTIONS, scrape_sources
from listing_spy.db import Db
from listing_spy.notifications import NotificationHandler
from listing_spy.sources import gather_offers

app = FastAPI()
templates = Jinja2Templates("templates")


@app.get("/")
async def root(request: Request):
    db = Db()
    sources = db.get_sources()
    notifications = db.get_notification_handlers()

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "sources": sources, "notifications": notifications},
    )


@app.post("/sources/{source_id}/delete")
async def delete_source(source_id):
    db = Db()

    db.delete_source(source_id)
    return RedirectResponse("/", 303)


@app.get("/sources/add")
async def sources_add(request: Request, url: Optional[str] = None):
    listings = None
    source_url = ""
    source_name = None

    if url:
        listings = gather_offers(url)
        source_url = url
        domain = urlsplit(url)
        source_name = domain.hostname

    return templates.TemplateResponse(
        "add_source.html",
        {
            "request": request,
            "listings": listings,
            "source_url": source_url,
            "source_name": source_name,
        },
    )


@app.post("/sources/add")
async def save_source(url: Annotated[str, Form()], source_name: Annotated[str, Form()]):
    db = Db()

    scrape_sources(db, [{"url": url}])
    db.add_source(url, source_name)
    return RedirectResponse("/", 303)


@app.get("/notifications/add")
async def notifications_add(request: Request, error: Optional[str] = None):
    message = None
    if error:
        message = "Sending test notification didn't work. Check your settings."

    return templates.TemplateResponse(
        "add_notification.html", {"request": request, "message": message}
    )


@app.post("/notifications/add")
async def save_notification(
    notification_type: Annotated[str, Form()],
    key: Annotated[str, Form()],
    notification_name: Annotated[str, Form()],
):
    db = Db()

    handler = NotificationHandler.get_handler(notification_type, key)
    try:
        handler.send(
            "You will now receive listing notifications.", "Listing notifications"
        )
    except:
        return RedirectResponse("/notifications/add?error=true", 303)

    db.add_notification_handler(notification_type, key, notification_name)
    return RedirectResponse("/", 303)


@app.post("/notifications/{notification_id}/delete")
async def delete_notification(notification_id):
    db = Db()

    db.delete_notification(notification_id)
    return RedirectResponse("/", 303)


class Event(BaseModel):
    id: str
    trigger: str


class Action(BaseModel):
    event: Event


@app.post("/__space/v0/actions")
def actions(action: Action):
    ACTIONS[action.event.id]()
