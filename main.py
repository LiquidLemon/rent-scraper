import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime
import sqlite3
from typing import List, Dict, Callable, Optional
from urllib.parse import urlsplit, urlunsplit, urljoin, parse_qs, urlencode

import requests
from bs4 import BeautifulSoup


@dataclass(frozen=True, eq=True)
class Offer:
    title: str
    url: str


def normalize_url(url: str) -> str:
    split = urlsplit(url)
    return urlunsplit((split.scheme, split.netloc, split.path, split.query, None))


def get_olx_offers(url: str) -> List[Offer]:
    links = set()

    current_url = url

    while True:
        response = requests.get(current_url)
        assert response.ok
        page = BeautifulSoup(response.text, features="html.parser")
        offers = page.find_all("td", class_="offer")

        for offer in offers:
            link = offer.find("a", class_="link")["href"]
            title = offer.find("strong").get_text()
            links.add(Offer(title=title, url=normalize_url(link)))

        # check next page
        next_button = page.find("span", class_="next")
        if not next_button:
            break

        next_link = next_button.find("a")
        if not next_link:
            break

        current_url = next_link["href"]

    return list(links)


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


def get_otodom_offers(url: str) -> List[Offer]:
    offers = set()

    current_url = url

    while True:
        response = requests.get(current_url)
        assert response.ok
        page = BeautifulSoup(response.text, features="html.parser")

        listings = page.find_all("a", {"data-cy": "listing-item-link"})

        for listing in listings:
            title = listing.find("h3").get_text()
            url = normalize_url(urljoin("https://www.otodom.pl", listing["href"]))
            offer = Offer(title=title, url=url)
            offers.add(offer)

        data = json.loads(page.find("script", id="__NEXT_DATA__").text)

        try:
            pagination = data["props"]["pageProps"]["data"]["searchAds"]["pagination"]
            page = pagination["page"]
            total_pages = pagination["totalPages"]

            if page < total_pages:
                split = urlsplit(current_url)
                query = parse_qs(split.query)
                query["page"] = [str(page + 1)]
                new_query = urlencode(query, doseq=True)
                current_url = urlunsplit((split.scheme, split.netloc, split.path, new_query, None))
            else:
                break
        except TypeError:
            break

    return list(offers)


HANDLERS: Dict[str, Callable[[str], List[Offer]]] = {
    "www.olx.pl": get_olx_offers,
    "www.otodom.pl": get_otodom_offers,
}


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
