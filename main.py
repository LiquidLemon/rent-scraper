import argparse
import os
from dataclasses import dataclass
from datetime import datetime
import sqlite3
from typing import List
from urllib.parse import urlsplit, urlunsplit

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--notify", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    url = "https://www.olx.pl/nieruchomosci/mieszkania/wynajem/gdansk/?search%5Bdistrict_id%5D=99"
    # url = "https://www.olx.pl/nieruchomosci/mieszkania/wynajem/gdansk/?search%5Bdist%5D=2&search%5Bdistrict_id%5D=99"
    offers = get_olx_offers(url)

    db = sqlite3.connect("offers.sqlite")
    init_database(db)

    missing = filter_missing_offers(db, offers)
    save_offers(db, missing)

    print(f"New offers: {len(missing)}")

    for offer in missing:
        if args.notify:
            pushbullet_send(offer)
        else:
            print(f"Would notify: {offer.url}")


if __name__ == "__main__":
    main()
