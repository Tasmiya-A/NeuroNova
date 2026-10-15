import re
from urllib.parse import urlparse


def rank_opportunities(opportunities, user_request):
    """Rank internship leads using available evidence.

    Scores indicate estimated relevance, not proof that a vacancy
    is genuine, active, or suitable for the applicant.
    """

    ranked = []

    user_skills = {
        skill.strip().lower()
        for skill in user_request.get("skills", [])
        if isinstance(skill, str) and skill.strip()
    }

    preferred_mode = str(
        user_request.get("work_mode", "Any") or "Any"
    ).strip().lower()

    generic_domains = {
        "indeed.com",
        "glassdoor.com",
        "naukri.com",
        "linkedin.com",
        "internshala.com",
        "prosple.com",
        "foundit.in",
    }

    generic_title_patterns = [
        r"\b\d+\s+(open\s+)?(internship|intern|job|jobs|vacanc)",
        r"\b(internships|jobs|vacancies)\s+in\b",
        r"\b(job|internship)\s+(search|listings)\b",
        r"\bfind\s+(internships|jobs)\b",
        r"\binternship opportunities\b",
        r"\bjob vacancies\b",
        r"\bopen roles\b",
    ]

    generic_path_patterns = [
        "/search",
        "/jobs/search",
        "/job-search",
        "/jobsearch",
        "/jobs/",
        "/internships/",
        "/internship-jobs",
        "/job-alerts",
    ]

    for opportunity in opportunities:
        item = opportunity.copy()

        title = str(item.get("title") or "").strip()
        description = str(item.get("description") or "").strip()
        company = str(item.get("company") or "").strip()
        url = str(
            item.get("url") or item.get("application_url") or ""
        ).strip()

        title_lower = title.lower()
        description_lower = description.lower()
        combined_text = f"{title} {description}".lower()

        parsed = urlparse(url)
        domain = parsed.netloc.lower().removeprefix("www.")
        path = parsed.path.lower()

        score = 0.0
        reasons = []

        # 1. Identify likely general listing pages.
        generic_title = any(
            re.search(pattern, title_lower)
            for pattern in generic_title_patterns
        )

        generic_path = any(
            pattern in path for pattern in generic_path_patterns
        )

        is_github_tracker = (
            domain == "github.com"
            and any(
                term in combined_text
                for term in [
                    "internship tracker",
                    "internship list",
                    "internship resources",
                    "internship repository",
                ]
            )
        )

        is_career_homepage = (
            path.rstrip("/") in {
                "",
                "/careers",
                "/career",
                "/jobs",
                "/internships",
            }
            and not re.search(
                r"\b(intern|internship|trainee)\b",
                title_lower,
            )
        )

        is_generic_page = (
            generic_title
            or is_github_tracker
            or is_career_homepage
            or (
                domain in generic_domains
                and generic_path
            )
        )

        if is_generic_page:
            score -= 40
            reasons.append(
                "Likely general listing or resource page; "
                "not confirmed as an individual vacancy"
            )
        else:
            reasons.append(
                "Not identified as an obvious general listing page"
            )

        # 2. Internship relevance.
        internship_title = bool(
            re.search(r"\b(intern|internship|trainee)\b", title_lower)
        )

        if internship_title:
            score += 25
            reasons.append("Title indicates an internship or trainee role")
        else:
            reasons.append("Internship role is not clear from the title")

        # 3. Match user skills against the available text.
        # This indicates mentions, not confirmed job requirements.
        mentioned_skills = {
            skill
            for skill in user_skills
            if re.search(
                rf"(?<!\w){re.escape(skill)}(?!\w)",
                combined_text,
            )
        }

        required_skills = {
            skill.strip().lower()
            for skill in item.get("required_skills", [])
            if isinstance(skill, str) and skill.strip()
        }

        matched_required_skills = user_skills.intersection(
            required_skills
        )

        if required_skills:
            skill_score = (
                len(matched_required_skills) / len(required_skills)
            ) * 35

            score += skill_score
            reasons.append(
                f"Matches {len(matched_required_skills)} of "
                f"{len(required_skills)} extracted required skills"
            )

        elif mentioned_skills:
            score += min(20, 5 * len(mentioned_skills))
            reasons.append(
                "User skills mentioned in search text: "
                + ", ".join(sorted(mentioned_skills))
                + "; job requirements are unconfirmed"
            )
        else:
            reasons.append(
                "No user skills were identified in the available text"
            )

        # 4. Experience suitability: award points only when explicitly known.
        experience = str(item.get("experience") or "").strip().lower()

        if experience in {
            "beginner",
            "entry level",
            "entry-level",
            "no experience required",
            "not required",
        }:
            score += 10
            reasons.append("Entry-level suitability is indicated")
        else:
            reasons.append(
                "Experience requirements are unknown or need review"
            )

        # 5. Work-mode suitability: unknown is not a match.
        actual_mode = str(item.get("work_mode") or "").strip().lower()

        if preferred_mode == "any":
            score += 5
            reasons.append("No work-mode preference was imposed")
        elif actual_mode in {
            "remote", "hybrid", "onsite", "on-site", "in-person"
        }:
            normalized_actual = (
                "onsite"
                if actual_mode in {"on-site", "in-person"}
                else actual_mode
            )
            normalized_preferred = (
                "onsite"
                if preferred_mode in {"on-site", "in-person"}
                else preferred_mode
            )

            if normalized_actual == normalized_preferred:
                score += 10
                reasons.append("Work mode matches the preference")
            else:
                score -= 10
                reasons.append("Work mode conflicts with the preference")
        else:
            reasons.append("Work mode is not verified")

        # 6. Employer information.
        if company and not any(
            phrase in company.lower()
            for phrase in ["not extracted", "unknown", "not verified"]
        ):
            reasons.append(
                "A company name is present but has not been independently verified"
            )
        else:
            reasons.append("Company name has not been reliably extracted")

        # 7. Preserve uncertainty.
        item["score"] = round(max(0.0, score), 2)
        item["reasons"] = reasons
        item["matched_skills"] = sorted(
            matched_required_skills or mentioned_skills
        )
        item["is_generic_search_page"] = is_generic_page

        # Ranking must not imply successful verification.
        item["eligibility_verified"] = False

        if not item.get("verification_status"):
            item["verification_status"] = "unverified_search_result"

        item["active_vacancy_confirmed"] = False

        ranked.append(item)

    # General pages should not outrank likely individual postings
    # just because their descriptions contain many matching keywords.
    ranked.sort(
        key=lambda item: (
            item["is_generic_search_page"],
            -item["score"],
        )
    )

    return ranked