import os
from datetime import datetime
import sqlite3
from typing import List
from urllib.parse import urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup


def normalize_url(url: str) -> str:
    split = urlsplit(url)
    return urlunsplit((split.scheme, split.netloc, split.path, split.query, None))


def get_olx_offers(url: str) -> List[str]:
    links = set()

    current_url = url

    while True:
        response = requests.get(current_url)
        assert response.ok
        page = BeautifulSoup(response.text, features="html.parser")
        offers = page.find_all("td", class_="offer")

        for offer in offers:
            link = offer.find("a", class_="link")["href"]
            links.add(normalize_url(link))

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
    cur.execute("CREATE TABLE IF NOT EXISTS offers (id INTEGER NOT NULL PRIMARY KEY, url TEXT, scraped_at TEXT)")
    cur.close()


def filter_missing_offers(db: sqlite3.Connection, urls: List[str]) -> List[str]:
    missing_offers = []

    cur = db.cursor()

    for url in urls:
        cur.execute("SELECT * FROM offers WHERE url = ?", (url,))
        result = cur.fetchall()
        if not result:
            missing_offers.append(url)

    cur.close()

    return missing_offers


def save_offers(db: sqlite3.Connection, urls: List[str]):
    cur = db.cursor()

    scraped_at = datetime.now().isoformat()
    rows = [(url, scraped_at) for url in urls]
    cur.executemany("INSERT INTO offers (url, scraped_at) VALUES (?, ?)", rows)

    cur.close()
    db.commit()


def pushbullet_send(url: str):
    payload = {
        "type": "link",
        "title": "Scraper",
        "body": "Nowa oferta",
        "url": url,
    }

    headers = {"Access-Token": os.getenv("PUSHBULLET_TOKEN")}

    response = requests.post("https://api.pushbullet.com/v2/pushes", json=payload, headers=headers)
    assert response.ok


def main():
    url = "https://www.olx.pl/nieruchomosci/mieszkania/wynajem/gdansk/?search%5Bdistrict_id%5D=99"
    # url = "https://www.olx.pl/nieruchomosci/mieszkania/wynajem/gdansk/?search%5Bdist%5D=2&search%5Bdistrict_id%5D=99"
    offers = get_olx_offers(url)

    db = sqlite3.connect("offers.sqlite")
    init_database(db)

    missing = filter_missing_offers(db, offers)
    save_offers(db, missing)

    for url in missing:
        pushbullet_send(url)

    print(f"New offers: {len(missing)}.")


if __name__ == "__main__":
    main()
