import requests
from bs4 import BeautifulSoup


def scrape_url(url: str, timeout: int = 15) -> str:
    """
    Fetches a URL and returns its readable text content.

    Strips scripts, styles, and navigation elements.
    Prefers <article> or <main> content over the full <body>.

    Raises:
        requests.RequestException: on network failure
        ValueError: if no readable content is found
    """
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "Mozilla/5.0 (compatible; PodBot/1.0)"},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    # Prefer article or main content; fall back to body
    container = soup.find("article") or soup.find("main") or soup.body
    if not container:
        raise ValueError("No readable content found at URL")

    text = container.get_text(separator="\n", strip=True)

    if not text.strip():
        raise ValueError("No readable text content found at URL")

    return text
