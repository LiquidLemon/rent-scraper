import logging
from typing import List, Any, Dict

from listing_spy.db import Db
from listing_spy.notifications import NotificationHandler
from listing_spy.sources import gather_offers, Offer


def scrape():
    db = Db()

    sources = db.get_sources()

    logger = logging.getLogger("listing.spy.actions.scrape")

    new_listings = scrape_sources(db, sources)
    if new_listings:
        logger.info(f"Found ({len(new_listings)}) new listings: ")
        for listing in new_listings:
            logger.info(listing.url)

    send_notifications(db, new_listings)


def scrape_sources(db, sources: List[Dict[str, Any]]):
    all_listings = []
    for source in sources:
        listings = None
        tries = 0
        while tries < 5:
            try:
                listings = gather_offers(source["url"])
                break
            except Exception:
                pass
            tries += 1

        if listings is None and (key := source.get("key")):
            db.mark_broken_source(key)
            continue

        all_listings += listings

    new_listings = db.save_new_listings(list(set(all_listings)))
    return new_listings


def send_notifications(db: Db, new_listings: List[Offer]):
    handlers = db.get_notification_handlers()
    for handler_config in handlers:
        handler = NotificationHandler.get_handler(
            handler_config["type"], handler_config["api_key"]
        )

        for listing in new_listings:
            handler.send(listing.title, "New listing", listing.url)


ACTIONS = {
    "scrape": scrape,
}
