import json
from dataclasses import dataclass
from typing import List, Dict, Callable, Optional
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
        offers = page.find_all("div", {"data-cy": "l-card"})

        for offer in offers:
            link = offer.find("a")["href"]
            title = offer.find("h6").get_text()
            links.add(Offer(title=title, url=normalize_url(link, "www.olx.pl")))

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
        listings = page.find_all("a", class_="offer__outer")

        for listing in listings:
            general_location = listing.find("div", {"data-testid": "offer__location__tree"}).text.strip()
            specific_location = listing.find("span", {"data-testid": "offer__location__highest-accuracy"})

            if specific_location:
                title = f"{general_location} - {specific_location.text.strip()}"
            else:
                title = general_location

            offer_url = f"https://www.morizon.pl{listing['href']}"
            offer = Offer(title=title, url=offer_url)
            offers.add(offer)

        next_page_link = page.find("link", {"data-hid": "next"})
        if not next_page_link:
            break

        current_url = next_page_link["href"]

    return list(offers)


def normalize_url(url: str, domain: Optional[str] = None) -> str:
    split = urlsplit(url)

    if split.netloc:
        domain = split.netloc

    if split.scheme:
        scheme = split.scheme
    else:
        scheme = "https"

    return urlunsplit((scheme, domain, split.path, split.query, None))


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
