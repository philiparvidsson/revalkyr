import requests

from bs4 import BeautifulSoup
from requests.exceptions import RequestException

from .service import Service
from ..context import Context


class NPM(Service):
    def __init__(self, ctx: Context):
        super().__init__(ctx)

        self._cache: dict[str, str | None] = dict()

    def get_github_repo_url(self, package_name: str) -> str | None:
        if package_name not in self._cache:
            self.log(
                f"Looking up GitHub repository URL for {package_name} on npmjs.com..."
            )

            url = f"https://www.npmjs.com/package/{package_name}"
            try:
                res = requests.get(url)
                res.raise_for_status()

                soup = BeautifulSoup(res.text, "lxml")
                repo_url_element = soup.select_one("#repository-link")
                if repo_url_element:
                    repo_url = repo_url_element.text.strip()
                    if not repo_url.startswith("http"):
                        repo_url = "https://" + repo_url
                    self._cache[package_name] = repo_url
                    self.log(f"Found it! {repo_url}")
                else:
                    self._cache[package_name] = None
                    self.log("Repository URL not found on the package page.")
            except RequestException as e:
                self._cache[package_name] = None
                self.log(f"Couldn't retrieve the package page: {e}")

        return self._cache[package_name]
