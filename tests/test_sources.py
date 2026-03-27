import sys
from pathlib import Path

import pytest

# Allow importing from app/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from sources import (
    Offer,
    get_gratka_offers,
    get_nieruchomosci_online_offers,
    get_olx_offers,
    get_otodom_offers,
    get_morizon_offers,
    get_rentola_offers,
    get_trojmiasto_offers,
)

# fmt: off
SOURCES = [
    pytest.param(
        "olx",
        "https://m.olx.pl/nieruchomosci/mieszkania/gdansk/q-mieszkanie-do-wynaj%C4%99cia/?search%5Border%5D=relevance:desc&search%5Bfilter_enum_rooms%5D%5B0%5D=two",
        get_olx_offers,
        id="olx",
    ),
    pytest.param(
        "nieruchomosci_online",
        "https://gdansk.nieruchomosci-online.pl/szukaj.html?3,mieszkanie,wynajem,,Gda%C5%84sk:7183,,,,-2600,,,,,,,2-2&q=",
        get_nieruchomosci_online_offers,
        id="nieruchomosci_online",
    ),
    pytest.param(
        "trojmiasto",
        "https://ogloszenia.trojmiasto.pl/nieruchomosci-mam-do-wynajecia/ai,_2600,b2i,1,fi,1,m2i,1,ri,2_3.html",
        get_trojmiasto_offers,
        id="trojmiasto",
    ),
    pytest.param(
        "rentola",
        "https://rentola.pl/wynajem?location=warszawa&property_types=room&property_types=apartment",
        get_rentola_offers,
        id="rentola",
    ),
    pytest.param(
        "gratka",
        "https://gratka.pl/nieruchomosci/mieszkania/gdansk/wynajem",
        get_gratka_offers,
        id="gratka",
    ),
    pytest.param(
        "otodom",
        "https://www.otodom.pl/pl/wyniki/wynajem/mieszkanie,2-pokoje/pomorskie/gdansk/gdansk/gdansk?limit=36&by=DEFAULT&direction=DESC",
        get_otodom_offers,
        marks=pytest.mark.skip(reason="scraper broken — needs fixing"),
        id="otodom",
    ),
    pytest.param(
        "morizon",
        # TODO: add a working morizon.pl search URL here
        "https://www.morizon.pl/do-wynajecia/mieszkania/gdansk/",
        get_morizon_offers,
        marks=pytest.mark.skip(reason="scraper broken — needs fixing"),
        id="morizon",
    ),
]
# fmt: on


@pytest.mark.timeout(30)
@pytest.mark.parametrize("name,url,handler", SOURCES)
def test_parse_first_page(name, url, handler):
    """Each source should return non-empty offers from page 1."""
    offers = handler(url, max_pages=1)

    assert len(offers) > 0, f"{name}: expected at least one offer, got none"
    for offer in offers:
        assert isinstance(offer, Offer)
        assert offer.title.strip(), f"{name}: offer has empty title"
        assert offer.url.strip(), f"{name}: offer has empty url"


@pytest.mark.timeout(60)
@pytest.mark.parametrize("name,url,handler", SOURCES)
def test_pagination(name, url, handler):
    """Each source should return more offers when fetching 2 pages vs 1."""
    page1_offers = handler(url, max_pages=1)
    page2_offers = handler(url, max_pages=2)

    assert len(page2_offers) > len(page1_offers), (
        f"{name}: pagination broken — page1={len(page1_offers)}, pages1+2={len(page2_offers)}"
    )
