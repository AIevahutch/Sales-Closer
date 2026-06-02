"""Shared constants for the closer acquisition MVP."""

TARGET_CATEGORIES = [
    "Nurse business coach",
    "Nurse career coach",
    "Nurse certification program",
    "Healthcare career coach",
    "ABA/autism business coach",
    "ABA growth consultant",
    "BCBA business coach",
    "General healthcare coach",
    "Not a fit",
]

OUTREACH_STATUSES = [
    "New",
    "Draft Generated",
    "Needs Review",
    "Approved",
    "Ready to Send",
    "Sent",
    "Follow-Up Due",
    "Replied",
    "Call Booked",
    "Trial Offered",
    "Closed Client",
    "Not a Fit",
]

EMAIL_STATUSES = [
    "Not Started",
    "Draft Generated",
    "Needs Review",
    "Approved",
    "Sent",
    "Follow-Up Due",
    "Replied",
    "Call Booked",
    "Trial Offered",
    "Closed Client",
    "Not a Fit",
]

PRIORITIES = ["Very High", "High", "Medium", "Do Not Contact"]

ENGAGEMENT_REVIEW_STATUSES = [
    "Needs Manual Review",
    "Manually Verified",
    "Not Applicable",
]

SEARCH_PROVIDERS = ["sample", "tavily", "brave", "serpapi"]

PREBUILT_SEARCH_QUERIES = {
    "Nurse/Healthcare": [
        "site:.com nurse business coach",
        "site:.com nurse entrepreneur coach",
        "site:.com nurse coach certification",
        "site:.com nurse career coach",
        "site:.com remote nurse career coach",
        "nurse business coach book a call",
        "nurse coach certification application",
        "nurse entrepreneur mastermind",
        "healthcare career coach book a call",
        "nurse transition coach program",
    ],
    "ABA/Autism": [
        "site:.com ABA business coach",
        "site:.com BCBA business coach",
        "site:.com autism business coach",
        "ABA business consultant coaching mastermind",
        "BCBA private practice coaching",
        "ABA clinic growth consultant",
        "autism practice growth consultant",
        "ABA startup bootcamp",
        "ABA business coaching program",
        "autism service provider business coach",
    ],
}

PROSPECT_COLUMNS = [
    "prospect_id",
    "name",
    "brand",
    "category",
    "instagram_handle",
    "instagram_url",
    "website",
    "email",
    "contact_form_url",
    "bio_notes",
    "link_in_bio_url",
    "offer_type",
    "estimated_offer_price",
    "funnel_type",
    "book_call_link",
    "application_link",
    "recent_content_notes",
    "engagement_notes",
    "testimonials_notes",
    "launch_or_cohort_notes",
    "why_they_might_need_a_closer",
    "outreach_angle",
    "discovery_source",
    "discovery_query",
    "confidence_score",
    "engagement_review_status",
    "fit_score",
    "priority",
    "status",
    "date_added",
    "date_dm_generated",
    "date_dm_approved",
    "date_dm_sent",
    "follow_up_1_date",
    "follow_up_2_date",
    "date_email_generated",
    "date_email_approved",
    "date_email_sent",
    "response_notes",
    "outcome",
    "created_at",
    "updated_at",
    # MVP working fields for editable drafts and workflow state.
    "dm_status",
    "dm_draft",
    "email_status",
    "email_subject",
    "email_body",
    "follow_up_1_dm",
    "follow_up_2_dm",
    "follow_up_1_email",
    "follow_up_2_email",
    "follow_up_1_sent_date",
    "follow_up_2_sent_date",
    "scoring_notes",
    "source_urls",
]

TEXT_COLUMNS = [column for column in PROSPECT_COLUMNS if column != "prospect_id"]

SCENARIOS = [
    "Tell me more.",
    "Do you have closing experience?",
    "We are not hiring.",
    "What commission are you looking for?",
    "Can you take calls?",
    "Send me more information.",
    "Do you have experience in our niche?",
    "We already have a closer.",
    "What exactly would you do?",
    "How would a trial work?",
]

