import re
from bs4 import BeautifulSoup
from app.utils.logger import logger


REMOVE_TAGS = [
    "script", "style", "noscript", "iframe", "form",
    "meta", "link",
]

REMOVE_CLASSES = [
    "breadcrumb", "usa-nav", "usa-footer", "usa-banner",
    "usa-header", "site-header", "site-footer",
    "back-to-top", "pagination", "feedback",
]


class DataSanitizer:
    MIN_CONTENT_LENGTH = 50

    def sanitize(self, html: str, url: str = "") -> str:
        try:
            soup = BeautifulSoup(html, "html.parser")

            # remove scripts and styles
            for tag in REMOVE_TAGS:
                for element in soup.find_all(tag):
                    element.decompose()

            # remove known nav/footer classes
            for cls in REMOVE_CLASSES:
                for element in soup.find_all(class_=re.compile(cls, re.IGNORECASE)):
                    element.decompose()

            # try main content area first
            main = (
                soup.find("main") or
                soup.find(id="main-content") or
                soup.find(class_=re.compile("main-content|policy-content|chapter", re.IGNORECASE)) or
                soup.find("article") or
                soup.body or
                soup
            )

            text = main.get_text(separator="\n", strip=True)
            text = self._clean_text(text)

            if len(text) >= self.MIN_CONTENT_LENGTH:
                return text

            # fallback — get everything from body
            if soup.body:
                text = soup.body.get_text(separator="\n", strip=True)
                text = self._clean_text(text)

            if len(text) < self.MIN_CONTENT_LENGTH:
                logger.warning(f"Content too short after sanitization: {url}")
                return ""

            return text

        except Exception as e:
            logger.error(f"Sanitization failed for {url}: {e}")
            return ""

    def _clean_text(self, text: str) -> str:
        text = re.sub(r" {2,}", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"^\d+\s*$", "", text, flags=re.MULTILINE)
        return text.strip()
