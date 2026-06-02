"""Approved Gmail sending support."""

from __future__ import annotations

import base64
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict

from .utils import clean_text, now_iso

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def send_approved_email(
    prospect: Dict[str, object],
    sender_email: str,
    credentials_file: str,
    token_file: str = "data/gmail_token.json",
) -> Dict[str, str]:
    """Send only when the prospect email draft is approved."""
    if clean_text(prospect.get("email_status")) != "Approved":
        return {"ok": "false", "message": "Email must be approved before sending."}
    recipient = clean_text(prospect.get("email"))
    subject = clean_text(prospect.get("email_subject"))
    body = clean_text(prospect.get("email_body"))
    sender = clean_text(sender_email)
    if not recipient or not subject or not body or not sender:
        return {"ok": "false", "message": "Sender, recipient, subject, and body are required."}

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except Exception as exc:
        return {"ok": "false", "message": f"Gmail dependencies are not installed: {exc}"}

    credentials_path = Path(credentials_file)
    if not credentials_path.exists():
        return {"ok": "false", "message": f"Gmail credentials file not found: {credentials_file}"}

    token_path = Path(token_file)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), GMAIL_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())

    message = MIMEText(body)
    message["to"] = recipient
    message["from"] = sender
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    service = build("gmail", "v1", credentials=creds)
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"ok": "true", "message": f"Sent Gmail message {sent.get('id', '')} at {now_iso()}"}

