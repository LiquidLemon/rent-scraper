from typing import List, Any, Dict

from deta import Deta, Base

from listing_spy.sources import Offer


def put_all(base: Base, objects: List[dict]):
    i = 0
    while i < len(objects):
        base.put_many(objects[i : i + 25])
        i += 25


class Db:
    listings: Base
    sources: Base
    notifications: Base

    def __init__(self):
        deta = Deta()
        self.listings = deta.Base("listings")
        self.sources = deta.Base("sources")
        self.notifications = deta.Base("notifications")

    def save_listings(self, listings: List[Offer]):
        objects = []
        for listing in listings:
            objects.append({"title": listing.title, "url": listing.url})

        put_all(self.listings, objects)

    def get_unknown_listings(self, listings: List[Offer]) -> List[Offer]:
        unknown = []

        for listing in listings:
            resp = self.listings.fetch({"url": listing.url})
            if resp.count == 0:
                unknown.append(listing)

        return unknown

    def save_new_listings(self, listings: List[Offer]) -> List[Offer]:
        new = self.get_unknown_listings(listings)
        self.save_listings(new)

        return new

    def add_source(self, url: str, name: str):
        self.sources.put({"url": url, "name": name})

    def get_sources(self) -> List[Dict[str, Any]]:
        return self.sources.fetch().items

    def delete_source(self, source_id: str):
        self.sources.delete(source_id)

    def add_notification_handler(self, handler_type: str, api_key: str, name: str):
        self.notifications.put({"type": handler_type, "api_key": api_key, "name": name})

    def get_notification_handlers(self) -> List[dict]:
        return self.notifications.fetch().items

    def delete_notification(self, notification_id: str):
        self.notifications.delete(notification_id)

    def mark_broken_source(self, source_id: str):
        source = self.sources.get(source_id)
        source["broken"] = True
        self.sources.put(source)
