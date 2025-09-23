import marimo

__generated_with = "0.16.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import requests
    from bs4 import BeautifulSoup
    return BeautifulSoup, requests


@app.cell
def _():
    from sources import (
        get_olx_offers,
        get_nieruchomosci_online_offers,
        get_rentola_offers,
        get_gratka_offers,
    )
    return (get_gratka_offers,)


@app.cell
def _():
    OLX_URL = "https://m.olx.pl/nieruchomosci/mieszkania/gdansk/q-mieszkanie-do-wynaj%C4%99cia/?search%5Border%5D=relevance:desc&search%5Bfilter_enum_rooms%5D%5B0%5D=two"

    NIERUCHOMOSCI_URL = "https://gdansk.nieruchomosci-online.pl/szukaj.html?3,mieszkanie,wynajem,,Gda%C5%84sk:7183,,,,-2600,,,,,,,2-2&q="

    RENTOLA_URL = (
        "https://rentola.pl/wynajem?location=gdansk&property_types=apartment"
    )

    GRATKA_URL = (
        "https://gratka.pl/nieruchomosci/mieszkania/gdansk/wynajem"
    )

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    }
    return GRATKA_URL, HEADERS


@app.cell
def _(BeautifulSoup, GRATKA_URL, HEADERS, requests):
    resp = requests.get(GRATKA_URL, headers=HEADERS)
    soup = BeautifulSoup(resp.text, "html.parser")
    return (soup,)


@app.cell
def _(soup):
    for link in soup.find_all("a", {"aria-current": "page"}):
        print(link.text)
    return


@app.cell
def _(GRATKA_URL, get_gratka_offers):
    get_gratka_offers(GRATKA_URL)
    return


if __name__ == "__main__":
    app.run()
