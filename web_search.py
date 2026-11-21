from urllib.parse import urlparse
from bs4 import BeautifulSoup
from ddgs import DDGS
import requests


class WebSearch:
    # Default search and page fetching configuration
    REGION: str = "wt-wt"
    SAFESEARCH: str = "moderate"
    MAX_RESULTS: int = 3
    TIMEOUT: int = 10
    MAX_CHARS: int = 4000
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    def search(self, query: str) -> list[dict[str, str]]:
        # Return empty list for empty queries
        if not query or not query.strip():
            return []

        try:
            results: list[dict[str, str]] = []
            with DDGS() as ddgs:
                raw_results = ddgs.text(
                    query.strip(),
                    region=self.REGION,
                    safesearch=self.SAFESEARCH,
                    max_results=self.MAX_RESULTS,
                )
                for item in raw_results or []:
                    results.append({
                        "title": item.get("title", "").strip(),
                        "url": item.get("href", "").strip(),
                        "snippet": item.get("body", "").strip(),
                    })
            return results
        except Exception as exc:
            # Log search error and return an empty list
            print(f"Помилка пошуку ({type(exc).__name__}): {exc}")
            return []

    def _is_valid_http_url(self, url: str) -> bool:
        # Allow only http/https URLs with a valid host
        if not url or not isinstance(url, str):
            return False
        parsed = urlparse(url.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)

    def read_page(self, url: str) -> str:
        if not self._is_valid_http_url(url):
            return ""

        try:
            response = requests.get(
                url.strip(),
                timeout=self.TIMEOUT,
                headers={"User-Agent": self.USER_AGENT},
            )
            response.raise_for_status()

            # Ensure the response is an HTML document
            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                return ""

            # Pass raw bytes so BeautifulSoup handles UTF-8 / page charset properly
            soup = BeautifulSoup(response.content, "html.parser")
            # Remove non-content elements like scripts, styles, headers, and footers
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "form"]):
                tag.decompose()

            lines = [line.strip() for line in soup.get_text(separator="\n").splitlines() if line.strip()]
            cleaned_text = "\n".join(lines)
            return cleaned_text[:self.MAX_CHARS]
        except Exception as exc:
            # Return an empty string on any page fetching or parsing error
            print(f"Помилка читання сторінки ({type(exc).__name__}): {exc}")
            return ""


if __name__ == "__main__":
    # 1. Create a WebSearch instance
    searcher = WebSearch()

    # 2. Perform a search for a sample query
    query = "Python документація"
    found = searcher.search(query)
    print(f"Знайдено результатів: {len(found)}")

    # 3–5. Get a result URL, fetch the page, and print the extracted text
    if found:
        selected_url = found[0]["url"]
        print(f"Обраний URL: {selected_url}\n")
        page_content = searcher.read_page(selected_url)
        print("Вміст сторінки:")
        print(page_content if page_content else "Текст сторінки не вдалося отримати.")
    else:
        print("Результатів пошуку не знайдено.")