"""Message, follow-up, and response script generation."""

from __future__ import annotations

from typing import Dict

from .llm import chat_completion
from .utils import clean_text, first_non_empty


def _observation(prospect: Dict[str, object]) -> str:
    for key in [
        "outreach_angle",
        "bio_notes",
        "offer_type",
        "funnel_type",
        "testimonials_notes",
        "launch_or_cohort_notes",
    ]:
        text = clean_text(prospect.get(key), 180)
        if text:
            return text
    return "your work with healthcare-based business owners"


def _audience(prospect: Dict[str, object]) -> str:
    category = clean_text(prospect.get("category"))
    if "ABA" in category or "BCBA" in category or "autism" in category.lower():
        return "ABA, autism, and BCBA business owners"
    if "career" in category.lower():
        return "nurses and healthcare professionals navigating career moves"
    if "certification" in category.lower():
        return "nurses pursuing coaching certification"
    if "nurse" in category.lower():
        return "nurses building coaching or consulting businesses"
    return "healthcare-based coaching clients"


def _first_name(prospect: Dict[str, object]) -> str:
    name = clean_text(prospect.get("name"))
    if not name:
        return "there"
    return name.split()[0].strip(",")


def _brand_or_name(prospect: Dict[str, object]) -> str:
    return first_non_empty(prospect.get("brand"), prospect.get("name"), prospect.get("instagram_handle"), "your brand")


def generate_instagram_dm(prospect: Dict[str, object], api_key: str = "") -> str:
    system_prompt = (
        "Draft concise Instagram DMs for Eva Hutchins. Use only supplied evidence. "
        "Do not claim direct high-ticket closing experience. Do not mention engagement unless "
        "engagement_review_status is Manually Verified. Do not invent pricing or results. "
        "Tone: confident, polished, feminine, professional, direct, not desperate. 80-140 words."
    )
    user_prompt = f"""
Prospect:
{prospect}

Required structure:
- Friendly observation from public notes.
- Eva is a former RN and healthcare recruiting leader.
- Include only 1-2 metrics: 10,000+ healthcare professionals contacted, 1,200+ interested leads, 40+ hires, 95%+ offer acceptance, nearly $1M cost savings.
- Offer commission-only trial support for warm enrollment calls/follow-up.
- Mention AI/Codex lightly as lead follow-up organization.
- End with a simple question about sales calls or enrollment follow-up.
"""
    generated = chat_completion(system_prompt, user_prompt, api_key=api_key, temperature=0.4, max_tokens=320)
    if generated:
        return generated

    return (
        f"Hi {_first_name(prospect)}, I love how you're helping {_audience(prospect)}. "
        f"I noticed {clean_text(_observation(prospect), 130)}.\n\n"
        "I'm a former RN and healthcare recruiting leader. At Kaiser, I supported large "
        "healthcare pipelines and helped move healthcare professionals from interest to final decision, "
        "including 1,200+ interested leads and a 95%+ offer acceptance rate.\n\n"
        "I'm now moving into high-ticket closing for healthcare-based coaching and education brands, "
        "and I'd be open to supporting warm enrollment calls on a commission-only trial. I also use "
        "AI/Codex to organize follow-up so warm prospects do not fall through the cracks. Are you "
        "currently looking for support with sales calls or enrollment follow-up?"
    )


def generate_email(prospect: Dict[str, object], api_key: str = "") -> Dict[str, str]:
    system_prompt = (
        "Draft personalized outreach emails for Eva Hutchins using only supplied evidence. "
        "Do not invent facts, pricing, engagement, or hiring intent. Email must ask for approval-worthy "
        "conversation, not assume need."
    )
    user_prompt = f"""
Prospect:
{prospect}

Return a subject line and body. Include Eva's former RN and healthcare recruiting credibility,
2-3 strongest transferable metrics, commission-only trial language, a light AI/Codex follow-up workflow line,
and a clear ask for a quick conversation.
"""
    generated = chat_completion(system_prompt, user_prompt, api_key=api_key, temperature=0.4, max_tokens=600)
    if generated:
        lines = [line.strip() for line in generated.splitlines() if line.strip()]
        subject = "Commission-only enrollment support for " + _brand_or_name(prospect)
        body_lines = lines
        if lines and lines[0].lower().startswith("subject"):
            subject = lines[0].split(":", 1)[-1].strip()
            body_lines = lines[1:]
        return {"email_subject": subject, "email_body": "\n".join(body_lines).strip()}

    subject = f"Commission-only enrollment support for {_brand_or_name(prospect)}"
    body = (
        f"Hi {_first_name(prospect)},\n\n"
        f"I came across {_brand_or_name(prospect)} and appreciated the focus on {_audience(prospect)}. "
        f"The note that stood out to me was: {clean_text(_observation(prospect), 160)}.\n\n"
        "I'm a former RN and healthcare recruiting leader with Kaiser Permanente sourcing experience. "
        "Across healthcare recruiting work, I contacted 10,000+ healthcare professionals, generated "
        "1,200+ interested leads, supported 40+ hires, and helped maintain a 95%+ offer acceptance rate.\n\n"
        "I'm now moving into commission-only high-ticket closing for healthcare-based coaching and education "
        "brands. I can support warm enrollment calls, follow-up, and simple AI/Codex-assisted lead organization "
        "so interested prospects do not fall through the cracks.\n\n"
        "Would it be worth a quick conversation about a small commission-only trial?"
    )
    return {"email_subject": subject, "email_body": body}


def generate_follow_up(prospect: Dict[str, object], number: int = 1, channel: str = "DM", api_key: str = "") -> str:
    system_prompt = (
        "Draft short, warm follow-ups for Eva Hutchins. Do not be pushy. Use only evidence supplied. "
        "Focus on whether the prospect needs support with enrollment calls or follow-up."
    )
    user_prompt = f"Prospect: {prospect}\nFollow-up number: {number}\nChannel: {channel}"
    generated = chat_completion(system_prompt, user_prompt, api_key=api_key, temperature=0.35, max_tokens=220)
    if generated:
        return generated
    if number == 1:
        return (
            f"Hi {_first_name(prospect)}, just wanted to follow up on my note. If {_brand_or_name(prospect)} "
            "is already covered on enrollment calls, no worries at all. If warm lead follow-up or sales-call "
            "coverage is becoming a bottleneck, I would be happy to explore a commission-only trial."
        )
    return (
        f"Hi {_first_name(prospect)}, last quick follow-up from me. I know timing may not be right, but if you "
        "ever want help converting warm healthcare/coaching leads through calls and follow-up, I would be glad "
        "to connect. Either way, wishing you a strong enrollment season."
    )


def generate_response_script(scenario: str, prospect: Dict[str, object], api_key: str = "") -> str:
    system_prompt = (
        "Draft concise response scripts for Eva Hutchins. Be direct, credible, and honest. "
        "Do not claim direct high-ticket closing experience. Position healthcare recruiting and RN background "
        "as transferable sales/enrollment credibility."
    )
    user_prompt = f"Scenario: {scenario}\nProspect: {prospect}"
    generated = chat_completion(system_prompt, user_prompt, api_key=api_key, temperature=0.35, max_tokens=360)
    if generated:
        return generated

    scenario_lower = scenario.lower()
    if "closing experience" in scenario_lower:
        return (
            "Great question. I am transitioning into high-ticket closing from healthcare recruiting, so I would "
            "not position myself as someone who has already closed coaching offers. What I do bring is RN context, "
            "Kaiser healthcare sourcing experience, high-volume candidate communication, follow-up discipline, "
            "and experience helping people move from interest to final decision. That is why I would suggest a "
            "commission-only trial with clear expectations and easy performance tracking."
        )
    if "commission" in scenario_lower:
        return (
            "I am flexible for the trial and would want the structure to make sense for your offer price, sales "
            "cycle, and current close rate. For a first test, I would be comfortable with commission-only terms "
            "tied to paid clients I help close, with the exact percentage agreed before calls begin."
        )
    if "not hiring" in scenario_lower:
        return (
            "Totally understand. I am not looking to add complexity. If you ever want a low-risk commission-only "
            "trial for warm enrollment calls or follow-up, I would be happy to reconnect. Either way, I appreciate "
            "you taking a look."
        )
    return (
        "Absolutely. My focus would be helping with warm enrollment conversations, structured follow-up, and simple "
        "lead organization so interested prospects do not fall through the cracks. Because I am moving from healthcare "
        "recruiting into closing, I would suggest starting with a clearly scoped commission-only trial."
    )

