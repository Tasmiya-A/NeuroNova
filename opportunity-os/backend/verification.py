import re
import urllib.error
import urllib.request

from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlparse


class PageTextParser(HTMLParser):
    """Extract a webpage's title and readable text."""

    def __init__(self):
        super().__init__()
        self.in_title = False
        self.in_script_or_style = False
        self.title_parts = []
        self.text_parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "title":
            self.in_title = True

        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.in_script_or_style = True

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False

        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.in_script_or_style = False

    def handle_data(self, data):
        text = data.strip()

        if not text:
            return

        if self.in_title:
            self.title_parts.append(text)

        if not self.in_script_or_style:
            self.text_parts.append(text)


def validate_http_url(url):
    """Accept only ordinary HTTP/HTTPS URLs."""

    try:
        parsed = urlparse(url)

        return (
            parsed.scheme.lower() in {"http", "https"}
            and bool(parsed.hostname)
            and not parsed.username
            and not parsed.password
        )

    except (TypeError, ValueError):
        return False


def inspect_internship_listing(url, timeout=12):
    """
    Inspect an internship URL and report available evidence.

    This function does not guarantee that a vacancy is genuine,
    currently available, or suitable for an applicant.
    """

    checked_at = datetime.now(timezone.utc).isoformat()

    result = {
        "url": url,
        "final_url": None,
        "checked_at": checked_at,
        "page_reachable": False,
        "http_status": None,
        "page_title": "",
        "internship_mentioned": False,
        "application_language_found": False,
        "closed_language_found": False,
        "verification_status": "unverified",
        "evidence": [],
        "limitations": [
            "Automated webpage inspection is not proof of vacancy authenticity.",
            "Availability and applicant eligibility require further confirmation.",
        ],
    }

    if not validate_http_url(url):
        result["verification_status"] = "invalid_url"
        result["evidence"].append(
            "The supplied URL is not a valid HTTP/HTTPS URL."
        )
        return result

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; OpportunityOS/1.0; "
                "+https://example.org/bot)"
            ),
            "Accept": "text/html,application/xhtml+xml",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:

            result["http_status"] = response.status
            result["final_url"] = response.geturl()

            content_type = response.headers.get(
                "Content-Type", ""
            ).lower()

            if "html" not in content_type:
                result["verification_status"] = (
                    "page_reached_non_html_content"
                )
                result["evidence"].append(
                    "The URL responded, but the response was not HTML."
                )
                return result

            # Read a limited amount of HTML to avoid downloading
            # unexpectedly large pages.
            html_bytes = response.read(1_000_000)

            encoding = response.headers.get_content_charset() or "utf-8"

            html = html_bytes.decode(
                encoding,
                errors="replace",
            )

            parser = PageTextParser()
            parser.feed(html)

            title = " ".join(parser.title_parts).strip()
            page_text = " ".join(parser.text_parts).strip()

            result["page_reachable"] = True
            result["page_title"] = title

            searchable_text = (
                f"{title} {page_text}"
            ).lower()

            # These are indicators, not definitive classifications.
            internship_pattern = (
                r"\b(internship|intern|trainee)\b"
            )

            application_pattern = (
                r"\b("
                r"apply now|apply here|submit application|"
                r"application deadline|apply by|"
                r"applications are open"
                r")\b"
            )

            closed_patterns = [
                r"\bposition\s+(is\s+)?closed\b",
                r"\bjob\s+posting\s+has\s+closed\b",
                r"\bapplications?\s+(are\s+)?closed\b",
                r"\bno longer accepting applications\b",
                r"\bthis job is no longer available\b",
                r"\bvacancy has been filled\b",
                r"\bposition has been filled\b",
            ]

            result["internship_mentioned"] = bool(
                re.search(
                    internship_pattern,
                    searchable_text,
                )
            )

            result["application_language_found"] = bool(
                re.search(
                    application_pattern,
                    searchable_text,
                )
            )

            result["closed_language_found"] = any(
                re.search(pattern, searchable_text)
                for pattern in closed_patterns
            )

            if result["http_status"] != 200:
                result["verification_status"] = (
                    "page_returned_non_success_status"
                )

            elif result["closed_language_found"]:
                result["verification_status"] = (
                    "possible_closed_vacancy"
                )
                result["evidence"].append(
                    "The page contains language indicating "
                    "that the position or applications may be closed."
                )

            elif (
                result["internship_mentioned"]
                and result["application_language_found"]
            ):
                result["verification_status"] = (
                    "possible_open_vacancy"
                )
                result["evidence"].append(
                    "The page mentions an internship and contains "
                    "application-related language."
                )
                result["evidence"].append(
                    "This does not independently establish that "
                    "applications are currently being accepted."
                )

            elif result["internship_mentioned"]:
                result["verification_status"] = (
                    "internship_page_reviewed_status_unclear"
                )
                result["evidence"].append(
                    "Internship-related language was found, "
                    "but open/closed status remains unclear."
                )

            else:
                result["verification_status"] = (
                    "page_reviewed_no_clear_internship_evidence"
                )
                result["evidence"].append(
                    "The inspected page did not contain clear "
                    "internship-related evidence."
                )

    except urllib.error.HTTPError as error:
        result["http_status"] = error.code
        result["verification_status"] = "http_error"
        result["evidence"].append(
            f"The server returned HTTP {error.code}."
        )

    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        UnicodeError,
        ValueError,
    ) as error:
        result["verification_status"] = "page_unreachable"
        result["evidence"].append(
            f"Page inspection failed: {type(error).__name__}: {error}"
        )

    except Exception as error:
        result["verification_status"] = "inspection_error"
        result["evidence"].append(
            f"Unexpected inspection error: "
            f"{type(error).__name__}: {error}"
        )

    return result


if __name__ == "__main__":
    test_url = input(
        "Paste an internship listing URL to inspect: "
    ).strip()

    inspection = inspect_internship_listing(test_url)

    print("\nVACANCY INSPECTION")
    print("=" * 50)

    for key, value in inspection.items():
        print(f"{key}: {value}")
        