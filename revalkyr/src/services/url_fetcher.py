import requests

from .service import Service
from ..context import Context


class URLFetcher(Service):
    def __init__(self, ctx: Context):
        super().__init__(ctx)

        self._cache: dict[str, str] = dict()

    def get_text(self, url: str) -> str:
        if url not in self._cache:
            res = requests.get(url)
            res.raise_for_status()
            self._cache[url] = res.text

        return self._cache[url]
