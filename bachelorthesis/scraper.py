import requests
from bs4 import BeautifulSoup


CHAINS = ["ethereum",]


def _get_link(chain):
    return f'https://opensea.io/rankings?sortBy=total_volume&chain={chain}'


def _get_html():
    chain = CHAINS[0]
    link = _get_link(chain)
    
    headers = {
        "Referer": link,
        "sec-ch-ua": '"Chromium";v="104", " Not A;Brand";v="99", "Google Chrome";v="104"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64)" 
                       "AppleWebKit/537.36 (KHTML, like Gecko)"
                       "Chrome/104.0.0.0 Safari/537.36")
    }
    return requests.get(link, headers=headers).content


def _extract_js_script():
    raw_html = _get_html()
    soup = BeautifulSoup(raw_html, "lxml")
    return soup.findAll('script')[0].string


def get_slug_names():
    script = _extract_js_script()
    
    location_slug = -1
    location_logo = -1
    
    slug_names = []
    
    while True:
        location_slug = script.find('"slug":"', location_slug + 1)
        location_logo = script.find('","logo', location_logo + 1)
        
        # Break if not found.
        if location_slug == -1: break
        if location_logo == -1: break
        
        # Display result.
        slug_names.append(script[location_slug+8:location_logo])
    return slug_names
