"""Approval gate helpers for outreach actions."""

from __future__ import annotations

from typing import Dict, Tuple

from .utils import clean_text

APPROVED_DM_STATUSES = {"Approved", "Ready to Send"}


def require_current_approved_dm(prospect: Dict[str, object], current_draft: object) -> Tuple[bool, str]:
    """Return whether the current DM text matches an approved saved draft."""
    status = clean_text(prospect.get("dm_status"))
    saved_draft = clean_text(prospect.get("dm_draft"))
    current = clean_text(current_draft)
    if not current:
        return False, "Generate and approve a DM before marking it ready or sent."
    if status not in APPROVED_DM_STATUSES:
        return False, "Approve the current DM draft before marking it ready or sent."
    if saved_draft != current:
        return False, "The DM text changed after approval. Save and approve the current draft first."
    return True, ""


def require_current_approved_email(
    prospect: Dict[str, object],
    current_subject: object,
    current_body: object,
) -> Tuple[bool, str]:
    """Return whether the current email subject/body match the approved saved draft."""
    if clean_text(prospect.get("email_status")) != "Approved":
        return False, "Approve the current email draft before sending."
    saved_subject = clean_text(prospect.get("email_subject"))
    saved_body = clean_text(prospect.get("email_body"))
    subject = clean_text(current_subject)
    body = clean_text(current_body)
    if not subject or not body:
        return False, "Subject and body are required before email approval and sending."
    if saved_subject != subject or saved_body != body:
        return False, "The email changed after approval. Save and approve the current draft first."
    return True, ""
