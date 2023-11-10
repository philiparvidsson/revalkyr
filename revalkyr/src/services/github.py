from requests.exceptions import RequestException

from .npm import NPM
from .service import Service
from .url_fetcher import URLFetcher


class GitHub(Service):
    def download_readme(self, package_name: str) -> str | None:
        npm = self.get_service(NPM)
        url_fetcher = self.get_service(URLFetcher)

        filenames = ["readme.rst", "README.rst", "readme.md", "README.md"]

        repo_url = npm.get_github_repo_url(package_name)
        repo_url = self._raw_github_url(repo_url)
        while len(filenames) > 0:
            try:
                filename = filenames.pop()
                url = repo_url + f"/main/{filename}"
                text = url_fetcher.get_text(url)
                self.log(f"Downloaded {filename} for package {package_name}")
                return text
            except RequestException:
                pass

        return None

    def download_source_code(self, package_name: str) -> str | None:
        npm = self.get_service(NPM)
        url_fetcher = self.get_service(URLFetcher)

        filenames = [
            f"lib/{package_name}.ts",
            f"lib/{package_name}.js",
            f"source/{package_name}.ts",
            f"source/{package_name}.js",
            f"src/{package_name}.ts",
            f"src/{package_name}.js",
            "lib/index.ts",
            "lib/index.js",
            "source/index.ts",
            "source/index.js",
            "src/index.ts",
            "src/index.js",
        ]

        repo_url = npm.get_github_repo_url(package_name)
        repo_url = self._raw_github_url(repo_url)
        while len(filenames) > 0:
            try:
                filename = filenames.pop()
                url = repo_url + f"/main/{filename}"
                text = url_fetcher.get_text(url)
                self.log(f"Downloaded {filename} for package {package_name}")
                return text
            except RequestException:
                pass

        return None

    def _raw_github_url(self, url: str) -> str:
        return url.replace("https://github.com", "https://raw.githubusercontent.com")
