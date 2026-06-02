"""OpenAI API helpers with deterministic fallbacks."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Dict, Optional

from .scoring import score_prospect
from .utils import clean_text

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


def _api_key(explicit: str = "") -> str:
    return explicit or os.environ.get("OPENAI_API_KEY", "")


def chat_completion(
    system_prompt: str,
    user_prompt: str,
    api_key: str = "",
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 700,
) -> str:
    key = _api_key(api_key)
    if not key:
        return ""
    payload = {
        "model": model or os.environ.get("OPENAI_MODEL", "gpt-5.5"),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    request = urllib.request.Request(
        OPENAI_CHAT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return ""
    return clean_text(data.get("choices", [{}])[0].get("message", {}).get("content", ""))


def classify_and_score(prospect: Dict[str, object], api_key: str = "") -> Dict[str, object]:
    """Use OpenAI when available, otherwise return deterministic scoring."""
    fallback = score_prospect(prospect)
    if not _api_key(api_key):
        return fallback

    system_prompt = (
        "You classify and score prospects for Eva Hutchins, a former RN and healthcare "
        "recruiting leader pursuing commission-only high-ticket closing clients. Use only "
        "the supplied public evidence. Do not invent pricing, engagement, hiring intent, "
        "or private facts. Return compact JSON only."
    )
    user_prompt = json.dumps(
        {
            "prospect": prospect,
            "valid_categories": [
                "Nurse business coach",
                "Nurse career coach",
                "Nurse certification program",
                "Healthcare career coach",
                "ABA/autism business coach",
                "ABA growth consultant",
                "BCBA business coach",
                "General healthcare coach",
                "Not a fit",
            ],
            "priority_rules": {
                "80-100": "Very High",
                "60-79": "High",
                "40-59": "Medium",
                "below_40": "Do Not Contact",
            },
            "required_fields": [
                "category",
                "fit_score",
                "priority",
                "confidence_score",
                "engagement_review_status",
                "offer_type",
                "funnel_type",
                "scoring_notes",
            ],
        },
        default=str,
    )
    response = chat_completion(system_prompt, user_prompt, api_key=api_key, temperature=0.1, max_tokens=600)
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        return fallback

    merged = dict(fallback)
    for key in merged:
        if key in parsed and clean_text(parsed[key]):
            merged[key] = parsed[key]
    try:
        merged["fit_score"] = max(1, min(100, int(float(merged["fit_score"]))))
    except (TypeError, ValueError):
        merged["fit_score"] = fallback["fit_score"]
    return merged
