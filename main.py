import argparse
import os
from datetime import datetime
import sqlite3
from typing import List
from urllib.parse import urlsplit

import requests

from sources import Offer, HANDLERS


def init_database(db: sqlite3.Connection):
    cur = db.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS offers (id INTEGER NOT NULL PRIMARY KEY, title TEXT, url TEXT, scraped_at TEXT)")
    cur.close()


def filter_missing_offers(db: sqlite3.Connection, offers: List[Offer]) -> List[Offer]:
    missing_offers = []

    cur = db.cursor()

    for offer in offers:
        cur.execute("SELECT * FROM offers WHERE url = ?", (offer.url,))
        result = cur.fetchall()
        if not result:
            missing_offers.append(offer)

    cur.close()

    return missing_offers


def save_offers(db: sqlite3.Connection, offers: List[Offer]):
    cur = db.cursor()

    scraped_at = datetime.now().isoformat()
    rows = [(offer.title, offer.url, scraped_at) for offer in offers]
    cur.executemany("INSERT INTO offers (title, url, scraped_at) VALUES (?, ?, ?)", rows)

    cur.close()
    db.commit()


def pushbullet_send(offer: Offer):
    payload = {
        "type": "link",
        "title": "Nowa oferta",
        "body": offer.title,
        "url": offer.url,
    }

    headers = {"Access-Token": os.getenv("PUSHBULLET_TOKEN")}

    response = requests.post("https://api.pushbullet.com/v2/pushes", json=payload, headers=headers)
    assert response.ok


def gather_offers(url: str) -> List[Offer]:
    split = urlsplit(url)
    handler = HANDLERS[split.netloc]
    return handler(url)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--notify", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    db = sqlite3.connect("offers.sqlite")
    init_database(db)

    queries = [
        "https://www.olx.pl/nieruchomosci/mieszkania/wynajem/gdansk/?search%5Bdistrict_id%5D=99",
        "https://www.otodom.pl/pl/oferty/wynajem/mieszkanie/gdansk/wrzeszcz?distanceRadius=0&page=1&limit=36&market=ALL&locations=%5Bdistricts_6-30%5D&roomsNumber=%5BONE%2CTWO%5D&viewType=listing&lang=pl&searchingCriteria=wynajem&searchingCriteria=mieszkanie&searchingCriteria=cala-polska",
        "https://ogloszenia.trojmiasto.pl/nieruchomosci-mam-do-wynajecia/mieszkanie/gdansk/wrzeszcz/ri,1_2.html",
    ]

    offers = set()
    for query in queries:
        offers.update(gather_offers(query))

    missing = filter_missing_offers(db, list(offers))
    save_offers(db, missing)

    print(f"New offers: {len(missing)}")

    for offer in missing:
        if args.notify:
            pushbullet_send(offer)
        else:
            print(f"Would notify: {offer.url}")


if __name__ == "__main__":
    main()
