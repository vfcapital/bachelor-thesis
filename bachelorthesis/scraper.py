import requests
from bs4 import BeautifulSoup

CHAIN = "ethereum"
CATEGORY = "art"

ETHERSCAN_KEY = "4TBHVWQDA6MMBY26PE4VTW1YDWMPZKFN1U"

def _get_slugs_link():
    return f"https://opensea.io/rankings?sortBy=total_volume&chain={CHAIN}&category={CATEGORY}"

def _get_opensea_collection_link(slug):
    return f"https://opensea.io/collection/{slug}"


def _get_etherscan_link(address):
    return f"https://etherscan.io/txs?a={address}&f=3"


def _get_html(link):
    headers = {
        "Referer": link,
        "sec-ch-ua": '"Chromium";v="104",'
        '" Not A;Brand";v="99",'
        '"Google Chrome";v="104"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            "AppleWebKit/537.36 (KHTML, like Gecko)"
            "Chrome/104.0.0.0 Safari/537.36"
        ),
    }
    return requests.get(link, headers=headers).content


def _extract_js_script(link):
    raw_html = _get_html(link)
    soup = BeautifulSoup(raw_html, "lxml")
    return soup#.findAll("script")[0].string


def get_slug_names():
    link = _get_slugs_link()
    script = _extract_js_script(link)

    location_slug = -1
    location_logo = -1

    slug_names = []

    while True:
        location_slug = script.find('"slug":"', location_slug + 1)
        location_logo = script.find('","logo', location_logo + 1)

        # Break if not found.
        if location_slug == -1:
            break
        if location_logo == -1:
            break

        # Display result.
        slug_names.append(script[location_slug + 8 : location_logo])
    return slug_names


def get_collection_address(slug):
    link = _get_opensea_collection_link(slug)
    script = _extract_js_script(link)

    location_address = -1
    location_chain = -1

    address = []

    while True:
        location_address = script.find('etherscan.io', location_address + 1)
        location_chain = script.find('","chain', location_chain + 1)

        # Break if not found.
        if location_address == -1:
            break
        if location_chain == -1:
            break

        # Display result.
        address.append(script[location_address + 26 : location_chain])
    return address[0].replace("u002F","")


def get_etherscan(address):
    link = _get_etherscan_link(address)
    raw_html = _get_html(link)
    soup = BeautifulSoup(raw_html, "lxml")
    return soup