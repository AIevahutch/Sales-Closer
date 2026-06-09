"""Classification and explainable fit scoring."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .constants import TARGET_CATEGORIES
from .utils import clean_text, coerce_int, extract_domain, first_non_empty


def _contains(text: str, *terms: str) -> bool:
    return any(term.lower() in text for term in terms)


def classify_category(prospect: Dict[str, object]) -> Tuple[str, int]:
    """Return a conservative category and confidence score from public notes."""
    text = " ".join(
        clean_text(prospect.get(key)).lower()
        for key in [
            "name",
            "brand",
            "category",
            "bio_notes",
            "offer_type",
            "funnel_type",
            "website",
            "discovery_query",
            "recent_content_notes",
        ]
    )

    if _contains(text, "bcba"):
        return "BCBA business coach", 82
    if _contains(text, "aesthetic injector", "injectable training", "injector training", "botox training", "dermal filler"):
        return "Aesthetic injector training", 86
    if _contains(text, "med spa", "medical spa", "aesthetic business", "spa owner"):
        return "Med spa business coaching", 84
    if _contains(text, "land investing", "real estate investing", "real estate investor", "creative finance", "subto"):
        return "Real estate investing education", 84
    if _contains(text, "business acquisition", "buy a business", "small business buyer", "acquire", "acquisition accelerator"):
        return "Business acquisition education", 84
    if _contains(text, "coding bootcamp", "tech bootcamp", "data analytics bootcamp", "cybersecurity bootcamp"):
        return "Tech career bootcamp", 82
    if _contains(text, "executive career", "reverse recruiting", "career bootcamp", "career accelerator", "salary negotiation"):
        return "Executive career coaching", 82
    if _contains(text, "creator economy", "creator college", "creator business", "content creator mastermind", "high ticket coaching", "business mastermind"):
        return "Creator/business mastermind", 78
    if _contains(text, "premium fitness", "weight loss coaching", "fertility coaching", "wellness coaching"):
        return "Premium wellness coaching", 74
    if _contains(text, "aba", "applied behavior analysis"):
        if _contains(text, "growth", "clinic", "practice", "startup", "business"):
            return "ABA growth consultant", 82
        return "ABA/autism business coach", 76
    if _contains(text, "autism"):
        return "ABA/autism business coach", 74
    if _contains(text, "certification", "certified nurse coach"):
        return "Nurse certification program", 80
    if _contains(text, "remote nurse", "career coach", "career transition", "nurse transition"):
        return "Nurse career coach", 78
    if _contains(text, "nurse entrepreneur", "nurse business", "nurse coach", "rn entrepreneur"):
        return "Nurse business coach", 82
    if _contains(text, "healthcare career", "health care career", "clinician career"):
        return "Healthcare career coach", 74
    if _contains(text, "healthcare", "clinician", "nurse"):
        return "General healthcare coach", 62
    return "Not a fit", 35


def priority_for_score(score: int) -> str:
    if score >= 80:
        return "Very High"
    if score >= 60:
        return "High"
    if score >= 40:
        return "Medium"
    return "Do Not Contact"


def infer_offer_type(prospect: Dict[str, object]) -> str:
    text = " ".join(clean_text(value).lower() for value in prospect.values())
    if _contains(text, "certification"):
        return "Certification program"
    if _contains(text, "mastermind"):
        return "Mastermind"
    if _contains(text, "cohort"):
        return "Cohort program"
    if _contains(text, "consulting", "consultant"):
        return "Consulting"
    if _contains(text, "coaching", "coach"):
        return "Coaching"
    if _contains(text, "course"):
        return "Course"
    return ""


def infer_funnel_type(prospect: Dict[str, object]) -> str:
    text = " ".join(clean_text(value).lower() for value in prospect.values())
    if _contains(text, "application", "apply now"):
        return "Application funnel"
    if _contains(text, "book a call", "schedule a call", "strategy call", "consultation"):
        return "Book-a-call funnel"
    if _contains(text, "waitlist"):
        return "Waitlist"
    if _contains(text, "webinar", "workshop"):
        return "Webinar/workshop funnel"
    return ""


def _price_signal(prospect: Dict[str, object]) -> bool:
    explicit = clean_text(prospect.get("estimated_offer_price")).lower()
    text = " ".join(clean_text(value).lower() for value in prospect.values())
    if explicit and explicit not in {"unknown", "n/a", "none"}:
        numbers = [int(match.replace(",", "")) for match in re.findall(r"\$?([1-9][0-9]{1,2},[0-9]{3}|[2-9][0-9]{3,})", explicit)]
        if numbers and max(numbers) >= 2000:
            return True
    return _contains(text, "high ticket", "mastermind", "certification", "cohort", "application only")


def score_prospect(prospect: Dict[str, object]) -> Dict[str, object]:
    """Score fit from 1-100 with reason codes and conservative defaults."""
    category, category_confidence = classify_category(prospect)
    score = 0
    reasons: List[str] = []

    if category in TARGET_CATEGORIES and category != "Not a fit":
        if category in {
            "Aesthetic injector training",
            "Med spa business coaching",
            "Real estate investing education",
            "Business acquisition education",
            "Tech career bootcamp",
            "Executive career coaching",
            "Nurse business coach",
            "Nurse career coach",
            "Nurse certification program",
            "ABA/autism business coach",
            "ABA growth consultant",
            "BCBA business coach",
        }:
            score += 25
            reasons.append("clear target niche")
        else:
            score += 15
            reasons.append("adjacent healthcare niche")
    else:
        score += 5
        reasons.append("weak or unclear niche fit")

    if prospect.get("instagram_url") or prospect.get("instagram_handle"):
        score += 12
        reasons.append("Instagram profile found")
    if prospect.get("link_in_bio_url"):
        score += 5
        reasons.append("link in bio found")
    if prospect.get("website") and extract_domain(prospect.get("website")):
        score += 8
        reasons.append("website found")
    if prospect.get("email"):
        score += 6
        reasons.append("public email found")
    if prospect.get("book_call_link"):
        score += 10
        reasons.append("book-a-call link found")
    if prospect.get("application_link"):
        score += 10
        reasons.append("application funnel found")

    offer_type = first_non_empty(prospect.get("offer_type"), infer_offer_type(prospect))
    if offer_type:
        score += 8
        reasons.append(f"offer type: {offer_type}")

    funnel_type = first_non_empty(prospect.get("funnel_type"), infer_funnel_type(prospect))
    if funnel_type:
        score += 6
        reasons.append(f"funnel type: {funnel_type}")

    if _price_signal(prospect):
        score += 8
        reasons.append("possible $2k+ offer signal")

    if prospect.get("recent_content_notes"):
        score += 4
        reasons.append("recent content notes present")

    engagement_status = clean_text(prospect.get("engagement_review_status")) or "Needs Manual Review"
    if engagement_status == "Manually Verified" and prospect.get("engagement_notes"):
        score += 5
        reasons.append("engagement manually verified")

    if prospect.get("testimonials_notes"):
        score += 5
        reasons.append("testimonials or client wins found")
    if prospect.get("launch_or_cohort_notes"):
        score += 6
        reasons.append("launch/cohort/enrollment signal")
    if prospect.get("why_they_might_need_a_closer"):
        score += 4
        reasons.append("closer need hypothesis documented")
    if prospect.get("outreach_angle"):
        score += 3
        reasons.append("clear outreach angle")

    score = min(max(score, 1), 100)
    if category == "Not a fit":
        score = min(score, 35)

    confidence = max(category_confidence, coerce_int(prospect.get("confidence_score"), 0))
    if prospect.get("website") and (prospect.get("instagram_url") or prospect.get("email")):
        confidence = min(confidence + 8, 95)

    return {
        "category": category,
        "fit_score": score,
        "priority": priority_for_score(score),
        "confidence_score": confidence,
        "engagement_review_status": engagement_status,
        "offer_type": offer_type,
        "funnel_type": funnel_type,
        "scoring_notes": "; ".join(reasons),
    }
