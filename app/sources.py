import json
from dataclasses import dataclass
from typing import List, Dict, Callable
from urllib.parse import urljoin, urlsplit, parse_qs, urlencode, urlunsplit

import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"


@dataclass(frozen=True, eq=True)
class Offer:
    title: str
    url: str


def get_olx_offers(url: str) -> List[Offer]:
    links = set()

    current_url = url

    while True:
        response = requests.get(current_url, headers={'User-Agent': USER_AGENT})
        assert response.ok
        page = BeautifulSoup(response.text, features="html.parser")
        offers = page.find_all("div", {"data-cy": "ad-card-title"})

        for offer in offers:
            link = offer.find("a")["href"]
            title = offer.text.strip()
            links.add(Offer(title=title, url=normalize_url(link, default_host="www.olx.pl")))

        # check next page
        next_link = page.find("a", {"data-cy": "pagination-forward"})
        if not next_link:
            break

        current_url = normalize_url(next_link["href"], default_host="www.olx.pl")  

    return list(links)

def get_nieruchomosci_online_offers(url: str) -> List[Offer]:
    links = set()

    current_url = url
    
    reached_end = False
    while True:
        response = requests.get(current_url, headers={'User-Agent': USER_AGENT})
        assert response.ok
        page = BeautifulSoup(response.text, features="html.parser")

        cards = page.find_all("div", {"class": "tile"})
        for card in cards:
            if "tile-infon" in card["class"]:
                continue

            if card.get("data-pie") not in ["normal", "", "prime"]: 
                reached_end = True
                break

            link_element = card.find("a")
            if not link_element:
                continue

            link = link_element["href"]
            title = card.find("h2").text.strip()
            links.add(Offer(title=title, url=normalize_url(link)))

        if reached_end:
            break

        next_wrapper = page.find("li", {"class": "next-wrapper"})
        if not next_wrapper:
            break

        current_url = normalize_url(next_wrapper.find("a")["href"])

    return list(links)

def get_otodom_offers(url: str) -> List[Offer]:
    offers = set()

    current_url = url

    while True:
        response = requests.get(current_url, headers={'User-Agent': USER_AGENT})
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
        response = requests.get(current_url, headers={'User-Agent': USER_AGENT})
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
        response = requests.get(current_url, headers={'User-Agent': USER_AGENT})
        assert response.ok

        page = BeautifulSoup(response.text, features="html.parser")
        listings = page.find_all("div", class_="card__outer")

        for listing in listings:
            title = listing.find("div", {"data-cy": "propertyCardTitle"}).text
            offer_url = normalize_url(listing.find("a")["href"], default_host="gratka.pl")
            offer = Offer(title=title, url=offer_url)
            offers.add(offer)

        candidate_links = page.find_all("a", {"aria-current": "page"})
        for link in candidate_links:
            if link.text.strip() == "Następna strona":
                next_page_button = link
                break
        else:
            break

        current_url = normalize_url(next_page_button["href"], default_host="gratka.pl")

    return list(offers)


def get_morizon_offers(url: str) -> List[Offer]:
    offers = set()
    current_url = url

    while True:
        response = requests.get(current_url, headers={'User-Agent': USER_AGENT})
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

def get_rentola_offers(url: str) -> List[Offer]:
    offers = set()
    current_url = url

    while True:
        response = requests.get(current_url, headers={'User-Agent': USER_AGENT})
        assert response.ok

        page = BeautifulSoup(response.text, features="html.parser")
        listings = page.find_all("div", {"data-testid": "propertyTile"})

        for listing in listings:
            title = listing.find("p").text
            offer_url = listing.find("a")["href"]
            offer = Offer(title=title, url=normalize_url(offer_url, default_host="rentola.pl"))
            offers.add(offer)

        pagination = page.find("div", {"role": "navigation"})
        if not pagination:
            break

        next_page_button = pagination.find_all("a")[-1]
        if not next_page_button or next_page_button.get("aria-disabled") == "true":
            break

        current_url = normalize_url(next_page_button["href"], default_host="rentola.pl")

    return list(offers)


def normalize_url(url: str, default_host: str | None = None) -> str:
    split = urlsplit(url)
    if not split.netloc and default_host:
        split = split._replace(netloc=default_host, scheme="https")
    return urlunsplit((split.scheme, split.netloc, split.path, split.query, None))


HANDLERS: Dict[str, Callable[[str], List[Offer]]] = {
    "www.olx.pl": get_olx_offers,
    "m.olx.pl": get_olx_offers,
    "gdansk.nieruchomosci-online.pl": get_nieruchomosci_online_offers,
    "ogloszenia.trojmiasto.pl": get_trojmiasto_offers,
    "rentola.pl": get_rentola_offers,
    "gratka.pl": get_gratka_offers,

    # broken
    # "www.otodom.pl": get_otodom_offers,
    # "www.morizon.pl": get_morizon_offers,
}
