from datetime import datetime, timezone
from urllib.parse import urlparse, unquote
import re

from ddgs import DDGS


GENERIC_TITLE_TERMS = [
    "jobs in india",
    "internships in india",
    "internship jobs",
    "job vacancies",
    "open jobs",
    "open internships",
    "jobs and internships",
    "job search",
    "internship opportunities",
    "internship listings",
    "jobs available",
    "open now",
    "internship openings",
]

GENERIC_URL_TERMS = [
    "/search",
    "/jobs/search",
    "/job-search",
    "/jobsearch",
    "/jobs/",
    "/internships/",
    "/internship-jobs",
    "/job-alerts",
]

KNOWN_JOB_PLATFORMS = {
    "indeed.com",
    "glassdoor.com",
    "naukri.com",
    "linkedin.com",
    "prosple.com",
    "internshala.com",
    "foundit.in",
}


def is_valid_url(url):
    """Return True if the URL is a valid HTTP or HTTPS URL."""
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme in ("http", "https")
            and bool(parsed.netloc)
        )
    except Exception:
        return False


def normalize_domain(url):
    """Extract a normalized domain from a URL."""
    try:
        domain = urlparse(url).netloc.lower()
        return domain.removeprefix("www.")
    except Exception:
        return ""


def is_generic_search_page(title, url):
    """
    Identify likely general search or listing pages.

    This is a heuristic. It can make mistakes, so the result
    should not be treated as proof that a page is generic.
    """
    title_lower = title.lower()
    path = unquote(urlparse(url).path).lower()
    domain = normalize_domain(url)

    title_matches = any(
        term in title_lower
        for term in GENERIC_TITLE_TERMS
    )

    path_matches = any(
        term in path
        for term in GENERIC_URL_TERMS
    )

    # A search/listing title combined with a listing-like URL
    # is stronger evidence than either signal alone.
    if title_matches and path_matches:
        return True

    # Known job platforms sometimes return category/search pages.
    if domain in KNOWN_JOB_PLATFORMS:
        generic_title_patterns = [
            r"\b\d+\s+(open\s+)?(internship|intern|job|jobs|vacanc)",
            r"\b(internships|jobs|vacancies)\s+in\b",
            r"\b(job|internship)\s+(search|listings)\b",
        ]

        if any(
            re.search(pattern, title_lower)
            for pattern in generic_title_patterns
        ):
            return True

    return False


def make_search_queries(skills, location):
    """Build targeted queries from the student's profile."""
    location = location or "India"

    queries = [
        f"site:company careers software engineering intern {location}",
        f"site:jobs.lever.co software engineering intern {location}",
        f"site:boards.greenhouse.io software engineering intern {location}",
        f"Python machine learning intern application {location}",
        f"AI ML intern careers {location}",
    ]

    if skills:
        skill_text = " ".join(skills[:3])

        queries.insert(
            0,
            f'"{skill_text}" internship application {location}',
        )

        queries.insert(
            1,
            f'"{skill_text}" intern careers {location}',
        )

    # Preserve order while removing duplicate queries.
    return list(dict.fromkeys(queries))


def search_opportunities(user_request):
    """
    Collect internship leads from live web search.

    These are leads, not verified vacancies. Search-result
    snippets alone cannot confirm availability, eligibility,
    employer identity, work mode, or required skills.
    """
    print("Starting live internship research...")

    skills = user_request.get("skills", [])
    location = user_request.get("location", "India")

    queries = make_search_queries(skills, location)

    opportunities = []
    seen_urls = set()
    query_failures = 0
    skipped_generic_pages = 0

    try:
        with DDGS() as search:
            for query in queries:
                print(f"\nSearching: {query}")

                try:
                    results = search.text(
                        query,
                        max_results=10,
                    )

                    result_count = 0

                    for result in results:
                        title = str(
                            result.get("title") or ""
                        ).strip()

                        url = str(
                            result.get("href") or ""
                        ).strip()

                        snippet = str(
                            result.get("body") or ""
                        ).strip()

                        if not title or not url:
                            continue

                        if not is_valid_url(url):
                            continue

                        normalized_url = (
                            url.split("#")[0].rstrip("/")
                        )

                        if normalized_url in seen_urls:
                            continue

                        if is_generic_search_page(title, url):
                            skipped_generic_pages += 1
                            print(
                                f"Skipping likely listing page: {title}"
                            )
                            continue

                        seen_urls.add(normalized_url)

                        domain = normalize_domain(url)

                        # Preliminary classification only.
                        title_lower = title.lower()

                        individual_posting_candidate = any(
                            word in title_lower
                            for word in [
                                "intern",
                                "internship",
                                "trainee",
                            ]
                        )

                        opportunity = {
                            "id": (
                                f"WEB{len(opportunities) + 1:03d}"
                            ),
                            "title": title,

                            # Search snippets are not enough to
                            # reliably establish the employer.
                            "company": (
                                "Not extracted; check original listing"
                            ),

                            "location": "Not verified",
                            "work_mode": "Not verified",
                            "required_skills": [],

                            "eligibility": (
                                "Not verified. Review the original listing."
                            ),

                            "experience": "Not verified",

                            "application_url": url,
                            "url": url,
                            "source": domain,
                            "description": snippet,

                            "collected_at": datetime.now(
                                timezone.utc
                            ).isoformat(),

                            "verification_status": (
                                "unverified_search_result"
                            ),

                            "result_type": (
                                "possible_individual_posting"
                                if individual_posting_candidate
                                else "uncertain_search_result"
                            ),

                            "individual_posting_confirmed": False,
                            "active_vacancy_confirmed": False,
                            "eligibility_verified": False,
                        }

                        opportunities.append(opportunity)
                        result_count += 1

                    print(
                        f"Collected {result_count} new results "
                        "from this query."
                    )

                except Exception as error:
                    query_failures += 1
                    print(f"Search query failed: {error}")

    except Exception as error:
        raise RuntimeError(
            f"Could not initialize live web search: {error}"
        ) from error

    if not opportunities:
        raise RuntimeError(
            "No usable search results were collected. "
            "The search service may be temporarily unavailable, "
            "or the filters may have removed all results. "
            "Check your connection and try again."
        )

    print("\nResearch completed.")
    print(f"Unique unverified leads: {len(opportunities)}")
    print(f"Likely listing pages skipped: {skipped_generic_pages}")
    print(f"Failed queries: {query_failures}")

    return opportunities


if __name__ == "__main__":
    profile = {
        "degree": "Computer Science",
        "year": 3,
        "skills": [
            "Python",
            "Machine Learning",
            "SQL",
        ],
        "location": "India",
        "work_mode": "Remote",
    }

    try:
        results = search_opportunities(profile)

        print("\nFIRST 10 SEARCH RESULTS")
        print("=" * 60)

        for index, item in enumerate(results[:10], start=1):
            print(f"\n{index}. {item['title']}")
            print(f"   Source: {item['source']}")
            print(f"   URL: {item['application_url']}")
            print(f"   Type: {item['result_type']}")
            print(
                "   Verification:",
                item["verification_status"],
            )

    except RuntimeError as error:
        print(f"\nResearch failed: {error}")