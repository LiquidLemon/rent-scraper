import json
from dataclasses import dataclass
from typing import List, Dict, Callable
from urllib.parse import urljoin, urlsplit, parse_qs, urlencode, urlunsplit

import requests
from bs4 import BeautifulSoup


@dataclass(frozen=True, eq=True)
class Offer:
    title: str
    url: str


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


def get_trojmiasto_offers(url: str) -> List[Offer]:
    offers = set()
    current_url = url

    while True:
        response = requests.get(current_url)
        assert response.ok

        page = BeautifulSoup(response.text, features="html.parser")
        listings = page.find_all("a", class_="list__item__content__title__name")

        for listing in listings:
            title = listing["title"]
            offer_url = normalize_url(listing["href"])
            offer = Offer(title=title, url=offer_url)
            offers.add(offer)

        next_page_button = page.find("a", title="następna")
        if not next_page_button:
            break

        current_url = urljoin(url, next_page_button["href"])

    return list(offers)


def get_gratka_offers(url: str) -> List[Offer]:
    offers = set()
    current_url = url

    while True:
        response = requests.get(current_url)
        assert response.ok

        page = BeautifulSoup(response.text, features="html.parser")
        listings = page.find_all("a", class_="teaserLink")

        for listing in listings:
            title = listing.title
            offer_url = listing["href"]
            offer = Offer(title=title, url=offer_url)
            offers.add(offer)

        next_page_button = page.find("a", class_="pagination__nextPage")
        if not next_page_button:
            break

        current_url = next_page_button["href"]

    return list(offers)


def get_morizon_offers(url: str) -> List[Offer]:
    offers = set()
    current_url = url

    while True:
        response = requests.get(current_url)
        assert response.ok

        page = BeautifulSoup(response.text, features="html.parser")
        listings = page.find_all("div", class_="row-property")

        for listing in listings:
            if "finances" in listing["class"]:
                # skip ad
                continue

            title = listing.find("h2").text.strip()
            offer_url = listing.find("a", class_="property-url")["href"]
            offer = Offer(title=title, url=offer_url)
            offers.add(offer)

        next_page_button = page.find("a", title="następna strona")
        if not next_page_button or not next_page_button.has_attr("href"):
            break

        current_url = urljoin(url, next_page_button["href"])

    return list(offers)


def normalize_url(url: str) -> str:
    split = urlsplit(url)
    return urlunsplit((split.scheme, split.netloc, split.path, split.query, None))


HANDLERS: Dict[str, Callable[[str], List[Offer]]] = {
    "www.olx.pl": get_olx_offers,
    "www.otodom.pl": get_otodom_offers,
    "ogloszenia.trojmiasto.pl": get_trojmiasto_offers,
    "gratka.pl": get_gratka_offers,
    "www.morizon.pl": get_morizon_offers,
}


def gather_offers(url: str) -> List[Offer]:
    split = urlsplit(url)
    handler = HANDLERS[split.netloc]
    return handler(url)
