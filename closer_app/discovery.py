"""Public prospect discovery and extraction."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from typing import Dict, List

from .llm import classify_and_score
from .scoring import infer_funnel_type, infer_offer_type
from .utils import (
    clean_text,
    compact_join,
    extract_email,
    extract_instagram_url,
    first_non_empty,
)


def _http_json(url: str, headers: Dict[str, str] = None, payload: Dict[str, object] = None) -> Dict[str, object]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if payload else "GET")
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def sample_search_results(query: str, num_results: int) -> List[Dict[str, str]]:
    base = [
        {
            "title": "RN Business Coach - Book a Strategy Call",
            "url": "https://example-nurse-coach.com",
            "snippet": "Helping nurses build coaching businesses with a cohort program, client wins, and application-only enrollment. Instagram @rncoachstudio.",
        },
        {
            "title": "BCBA Practice Growth Consultant",
            "url": "https://example-bcba-growth.com/apply",
            "snippet": "ABA clinic growth consulting for BCBAs. Apply for private practice mentorship and schedule a consultation.",
        },
        {
            "title": "Remote Nurse Career Coach",
            "url": "https://example-nurse-career.com/book-a-call",
            "snippet": "Career coaching for nurses moving into remote healthcare roles. Book a call or email hello@example-nurse-career.com.",
        },
        {
            "title": "Autism Provider Business Mastermind",
            "url": "https://example-autism-mastermind.com",
            "snippet": "Mastermind for autism service providers and clinic owners with enrollment windows and testimonials.",
        },
    ]
    return base[: max(1, min(num_results, len(base)))]


def search_public_web(provider: str, query: str, api_key: str = "", num_results: int = 10) -> List[Dict[str, str]]:
    provider = (provider or "sample").lower()
    if provider == "sample" or not api_key:
        return sample_search_results(query, num_results)

    try:
        if provider == "tavily":
            data = _http_json(
                "https://api.tavily.com/search",
                headers={"Content-Type": "application/json"},
                payload={"api_key": api_key, "query": query, "max_results": num_results, "search_depth": "basic"},
            )
            return [
                {"title": item.get("title", ""), "url": item.get("url", ""), "snippet": item.get("content", "")}
                for item in data.get("results", [])
            ]
        if provider == "brave":
            encoded = urllib.parse.urlencode({"q": query, "count": num_results})
            data = _http_json(
                f"https://api.search.brave.com/res/v1/web/search?{encoded}",
                headers={"Accept": "application/json", "X-Subscription-Token": api_key},
            )
            return [
                {"title": item.get("title", ""), "url": item.get("url", ""), "snippet": item.get("description", "")}
                for item in data.get("web", {}).get("results", [])
            ]
        if provider == "serpapi":
            encoded = urllib.parse.urlencode({"engine": "google", "q": query, "api_key": api_key, "num": num_results})
            data = _http_json(f"https://serpapi.com/search.json?{encoded}")
            return [
                {"title": item.get("title", ""), "url": item.get("link", ""), "snippet": item.get("snippet", "")}
                for item in data.get("organic_results", [])
            ]
    except Exception:  # Keep discovery usable without polluting the queue with fake leads.
        return []
    return sample_search_results(query, num_results)


def fetch_public_page_text(url: str) -> str:
    if not url or "instagram.com" in url.lower():
        return ""
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 closer-mvp public research"})
        with urllib.request.urlopen(request, timeout=15) as response:
            html = response.read(400_000).decode("utf-8", errors="ignore")
    except Exception:
        return ""

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return clean_text(soup.get_text(" "), 3000)
    except Exception:
        text = re.sub(r"<[^>]+>", " ", html)
        return clean_text(text, 3000)


def _candidate_link(url: str, text: str, *terms: str) -> str:
    lower = text.lower()
    if any(term in lower for term in terms):
        return url
    return ""


def extract_prospect_from_result(
    result: Dict[str, object],
    discovery_query: str,
    target_category: str = "",
    fetch_pages: bool = False,
) -> Dict[str, object]:
    title = clean_text(result.get("title"))
    url = clean_text(result.get("url"))
    snippet = clean_text(result.get("snippet"))
    page_text = fetch_public_page_text(url) if fetch_pages else ""
    evidence = compact_join([title, snippet, page_text[:1200]])
    instagram_url = extract_instagram_url(title, snippet, page_text)
    offer_type = infer_offer_type({"bio_notes": evidence, "discovery_query": discovery_query})
    funnel_type = infer_funnel_type({"bio_notes": evidence, "discovery_query": discovery_query, "website": url})

    prospect = {
        "name": title.split("-")[0].strip() if title else "",
        "brand": title,
        "category": target_category,
        "instagram_url": instagram_url,
        "website": url,
        "email": extract_email(snippet, page_text),
        "contact_form_url": _candidate_link(url, evidence, "contact"),
        "bio_notes": evidence,
        "link_in_bio_url": "",
        "offer_type": offer_type,
        "estimated_offer_price": "Unknown",
        "funnel_type": funnel_type,
        "book_call_link": _candidate_link(url, evidence, "book a call", "schedule", "consultation"),
        "application_link": _candidate_link(url, evidence, "application", "apply"),
        "recent_content_notes": "",
        "engagement_notes": "",
        "testimonials_notes": snippet if "testimonial" in snippet.lower() or "client win" in snippet.lower() else "",
        "launch_or_cohort_notes": snippet if any(term in snippet.lower() for term in ["launch", "cohort", "enrollment"]) else "",
        "why_they_might_need_a_closer": "Possible warm lead follow-up and enrollment-call support need.",
        "outreach_angle": "Support warm enrollment calls and follow-up for healthcare-based coaching offers.",
        "discovery_source": "public search",
        "discovery_query": discovery_query,
        "engagement_review_status": "Needs Manual Review",
        "status": "New",
        "dm_status": "Not Started",
        "email_status": "Not Started",
        "source_urls": url,
    }
    return prospect


def discover_prospects(
    provider: str,
    query: str,
    api_key: str = "",
    num_results: int = 10,
    target_category: str = "",
    fetch_pages: bool = False,
    openai_api_key: str = "",
) -> List[Dict[str, object]]:
    results = search_public_web(provider, query, api_key=api_key, num_results=num_results)
    prospects: List[Dict[str, object]] = []
    for result in results:
        prospect = extract_prospect_from_result(result, query, target_category=target_category, fetch_pages=fetch_pages)
        prospect.update(classify_and_score(prospect, api_key=openai_api_key))
        prospects.append(prospect)
    return prospects
