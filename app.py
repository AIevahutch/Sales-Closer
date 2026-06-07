from __future__ import annotations

from html import escape
import os
import re
from typing import Dict, Iterable, List, Tuple

import streamlit as st

from closer_app.constants import (
    EMAIL_STATUSES,
    ENGAGEMENT_REVIEW_STATUSES,
    OUTREACH_STATUSES,
    PREBUILT_SEARCH_QUERIES,
    PRIORITIES,
    SCENARIOS,
    SEARCH_PROVIDERS,
    TARGET_CATEGORIES,
)
from closer_app.approval import require_current_approved_dm
from closer_app.db import (
    connection_db_path,
    daily_instagram_queue,
    delete_prospect,
    export_csv,
    followups_due,
    get_connection,
    get_prospect,
    get_settings,
    import_csv,
    list_prospects,
    metrics,
    save_settings,
    update_prospect,
    upsert_prospect,
)
from closer_app.utils import add_days_iso, clean_text, env_or_setting, is_placeholder_url, load_dotenv, today_iso


load_dotenv()

st.set_page_config(
    page_title="Instagram-First Closer Acquisition",
    page_icon="IG",
    layout="wide",
)


APP_CSS = """
<style>
  :root {
    --surface: #ffffff;
    --surface-soft: #f5f7fb;
    --ink: #1c1e21;
    --muted: #65676b;
    --line: #d8dde7;
    --blue: #1877f2;
    --teal: #0f766e;
    --amber: #b45309;
    --rose: #d62976;
    --coral: #f56040;
    --page: #f0f2f5;
  }

  .stApp {
    background: var(--page);
  }

  .block-container {
    max-width: 1180px;
    padding-top: 1rem;
    padding-bottom: 3rem;
  }

  h1, h2, h3 {
    color: var(--ink);
    letter-spacing: 0;
  }

  [data-testid="stSidebar"] {
    background: #132033;
  }

  [data-testid="stSidebar"] * {
    color: #f8fafc;
  }

  [data-testid="stSidebar"] .muted {
    color: #c9d5e4;
  }

  [data-testid="stSidebar"] .workflow-row {
    background: #1f2a3d;
    border-color: rgba(248, 250, 252, 0.14);
  }

  [data-testid="stSidebar"] .workflow-row strong {
    color: #f8fafc;
  }

  [data-testid="stSidebar"] .workflow-row span {
    color: #c9d5e4;
  }

  .app-subtitle {
    color: var(--muted);
    font-size: 1rem;
    margin: -0.45rem 0 1rem;
  }

  .social-header {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(23, 32, 51, 0.08);
    display: grid;
    gap: 1rem;
    grid-template-columns: auto 1fr;
    margin: 0.35rem 0 0.85rem;
    padding: 1rem;
  }

  .social-avatar,
  .post-avatar {
    align-items: center;
    background: #fff;
    border: 3px solid var(--rose);
    border-radius: 50%;
    color: var(--rose);
    display: flex;
    font-weight: 820;
    justify-content: center;
  }

  .social-avatar {
    font-size: 1.25rem;
    height: 66px;
    width: 66px;
  }

  .social-title-row {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    justify-content: space-between;
  }

  .social-name {
    color: var(--ink);
    font-size: 1.28rem;
    font-weight: 820;
    line-height: 1.15;
  }

  .social-handle {
    color: var(--muted);
    font-size: 0.92rem;
    margin-top: 0.12rem;
  }

  .social-stats {
    display: grid;
    gap: 0.6rem;
    grid-template-columns: repeat(4, minmax(86px, 1fr));
    margin-top: 0.8rem;
  }

  .social-stat {
    background: var(--surface-soft);
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 0.58rem 0.68rem;
  }

  .social-stat strong {
    color: var(--ink);
    display: block;
    font-size: 1.14rem;
    line-height: 1.1;
  }

  .social-stat span {
    color: var(--muted);
    display: block;
    font-size: 0.74rem;
    font-weight: 720;
    margin-top: 0.18rem;
    text-transform: uppercase;
  }

  .story-strip {
    display: grid;
    gap: 0.62rem;
    grid-template-columns: repeat(5, minmax(112px, 1fr));
    margin: 0.8rem 0 1rem;
  }

  .story-chip {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    box-shadow: 0 1px 2px rgba(23, 32, 51, 0.06);
    padding: 0.68rem;
  }

  .story-ring {
    align-items: center;
    border: 2px solid var(--coral);
    border-radius: 50%;
    color: var(--coral);
    display: flex;
    font-size: 0.78rem;
    font-weight: 820;
    height: 40px;
    justify-content: center;
    margin-bottom: 0.42rem;
    width: 40px;
  }

  .story-title {
    color: var(--ink);
    display: block;
    font-size: 0.88rem;
    font-weight: 780;
  }

  .story-subtitle {
    color: var(--muted);
    display: block;
    font-size: 0.78rem;
    margin-top: 0.08rem;
  }

  .section-kicker {
    color: var(--teal);
    font-size: 0.76rem;
    font-weight: 760;
    letter-spacing: 0.06em;
    margin-bottom: 0.15rem;
    text-transform: uppercase;
  }

  .section-copy {
    color: var(--muted);
    margin: -0.3rem 0 0.9rem;
  }

  .stat-card,
  .detail-panel,
  .action-band,
  .workflow-row {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(23, 32, 51, 0.08);
  }

  .stat-card {
    min-height: 96px;
    padding: 0.9rem 1rem;
  }

  .stat-label {
    color: var(--muted);
    font-size: 0.78rem;
    font-weight: 720;
    text-transform: uppercase;
  }

  .stat-value {
    color: var(--ink);
    font-size: 1.8rem;
    font-weight: 790;
    line-height: 1.15;
    margin-top: 0.28rem;
  }

  .stat-help {
    color: var(--muted);
    font-size: 0.85rem;
    margin-top: 0.28rem;
  }

  .action-band {
    border-left: 4px solid var(--blue);
    margin: 0.5rem 0 1rem;
    padding: 0.95rem 1rem;
  }

  .action-band strong {
    color: var(--ink);
  }

  .action-band p {
    color: var(--muted);
    margin: 0.15rem 0 0;
  }

  .detail-panel {
    margin: 0.45rem 0 1rem;
    padding: 0.9rem 1rem;
  }

  .panel-title {
    color: var(--ink);
    font-size: 0.96rem;
    font-weight: 760;
    margin-bottom: 0.55rem;
  }

  .detail-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(165px, 1fr));
    gap: 0.65rem 1rem;
  }

  .detail-label {
    color: var(--muted);
    display: block;
    font-size: 0.74rem;
    font-weight: 720;
    text-transform: uppercase;
  }

  .detail-value {
    color: var(--ink);
    display: block;
    font-size: 0.93rem;
    margin-top: 0.12rem;
    overflow-wrap: anywhere;
  }

  .status-chip {
    border: 1px solid #cbd5e1;
    border-radius: 999px;
    display: inline-block;
    font-size: 0.76rem;
    font-weight: 760;
    line-height: 1;
    padding: 0.28rem 0.5rem;
    white-space: nowrap;
  }

  .chip-very-high,
  .chip-needs-review,
  .chip-follow-up-due {
    background: #fff1f2;
    border-color: #fecdd3;
    color: var(--rose);
  }

  .chip-high,
  .chip-ready-to-send,
  .chip-trial-offered {
    background: #fffbeb;
    border-color: #fde68a;
    color: var(--amber);
  }

  .chip-medium,
  .chip-approved,
  .chip-sent,
  .chip-call-booked,
  .chip-closed-client,
  .chip-replied,
  .chip-manually-verified {
    background: #ecfdf5;
    border-color: #99f6e4;
    color: var(--teal);
  }

  .chip-do-not-contact,
  .chip-not-a-fit,
  .chip-not-started,
  .chip-unknown,
  .chip-needs-manual-review,
  .chip-not-applicable {
    background: #f8fafc;
    border-color: #cbd5e1;
    color: #475569;
  }

  .workflow-row {
    box-shadow: none;
    margin: 0.45rem 0;
    padding: 0.62rem 0.72rem;
  }

  .workflow-row strong {
    display: block;
    font-size: 0.9rem;
  }

  .workflow-row span {
    color: #c9d5e4;
    display: block;
    font-size: 0.78rem;
    margin-top: 0.12rem;
  }

  .mvp-table-wrap {
    overflow-x: auto;
    margin: 0.55rem 0 1rem;
  }

  .mvp-table {
    border-collapse: separate;
    border-spacing: 0;
    min-width: 100%;
    font-size: 0.88rem;
  }

  .mvp-table th,
  .mvp-table td {
    border-bottom: 1px solid rgba(96, 112, 134, 0.18);
    padding: 0.58rem 0.62rem;
    text-align: left;
    vertical-align: top;
  }

  .mvp-table th {
    background: var(--surface-soft);
    color: #334155;
    font-size: 0.76rem;
    font-weight: 780;
    position: sticky;
    top: 0;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .mvp-table td {
    color: #243047;
  }

  .mvp-table tr:hover td {
    background: #f9fbfe;
  }

  .feed-card,
  .right-rail-panel {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(23, 32, 51, 0.08);
    margin-bottom: 0.85rem;
    padding: 0.95rem;
  }

  .post-header {
    align-items: center;
    display: grid;
    gap: 0.65rem;
    grid-template-columns: auto 1fr auto;
  }

  .post-avatar {
    border-color: var(--blue);
    color: var(--blue);
    height: 42px;
    width: 42px;
  }

  .post-name {
    color: var(--ink);
    display: block;
    font-weight: 800;
    line-height: 1.1;
  }

  .post-meta {
    color: var(--muted);
    display: block;
    font-size: 0.82rem;
    margin-top: 0.1rem;
  }

  .post-copy {
    color: #303541;
    font-size: 0.94rem;
    line-height: 1.45;
    margin: 0.8rem 0;
  }

  .post-actions {
    border-top: 1px solid #edf0f5;
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    padding-top: 0.72rem;
  }

  .post-action {
    background: var(--surface-soft);
    border-radius: 8px;
    color: #374151;
    font-size: 0.82rem;
    font-weight: 760;
    padding: 0.4rem 0.55rem;
  }

  .link-disabled {
    color: #64748b;
    cursor: not-allowed;
  }

  .rail-title {
    color: var(--ink);
    font-size: 0.95rem;
    font-weight: 820;
    margin-bottom: 0.55rem;
  }

  .rail-row {
    border-top: 1px solid #edf0f5;
    color: #303541;
    font-size: 0.9rem;
    padding: 0.6rem 0;
  }

  .rail-row:first-of-type {
    border-top: 0;
    padding-top: 0;
  }

  .rail-row span {
    color: var(--muted);
    display: block;
    font-size: 0.78rem;
    margin-top: 0.1rem;
  }

  @media (max-width: 760px) {
    .social-header {
      grid-template-columns: 1fr;
    }

    .social-stats,
    .story-strip {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .post-header {
      grid-template-columns: auto 1fr;
    }

    .post-header > :last-child {
      grid-column: 1 / -1;
    }
  }

  .mvp-table a,
  .detail-value a {
    color: var(--blue);
    font-weight: 680;
    text-decoration: none;
  }

  .mvp-table a:hover,
  .detail-value a:hover {
    text-decoration: underline;
  }

  div.stButton > button,
  div.stDownloadButton > button {
    border-radius: 8px;
    font-weight: 720;
  }

  div[data-testid="stMetric"] {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 0.85rem 1rem;
    box-shadow: 0 8px 24px rgba(23, 32, 51, 0.05);
  }
</style>
"""


def rerun() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    st.experimental_rerun()


def inject_ui_styles() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)


def daily_cap_from_settings(settings: Dict[str, str]) -> int:
    try:
        return max(1, min(25, int(settings.get("default_daily_outreach_cap") or 12)))
    except (TypeError, ValueError):
        return 12


def slug(value: object) -> str:
    text = clean_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "unknown"


def chip(value: object) -> str:
    text = clean_text(value) or "Unknown"
    return f"<span class='status-chip chip-{slug(text)}'>{escape(text)}</span>"


def safe_link(url: object, label: str = "") -> str:
    text = clean_text(url)
    if not text:
        return ""
    if is_placeholder_url(text):
        return "<span class='link-disabled'>Invalid sample link</span>"
    href = text if text.startswith(("http://", "https://", "mailto:")) else f"https://{text}"
    visible = label or clean_text(text.replace("https://", "").replace("http://", ""), 42)
    return f"<a href='{escape(href, quote=True)}' target='_blank' rel='noopener noreferrer'>{escape(visible)}</a>"


def disabled_action(label: str) -> str:
    return f"<span class='link-disabled'>{escape(label)}</span>"


def instagram_action(url: object) -> str:
    text = clean_text(url)
    if not text or is_placeholder_url(text):
        return disabled_action("No verified Instagram")
    return safe_link(text, "Open Instagram")


def instagram_handle_link(handle: object) -> str:
    text = clean_text(handle).lstrip("@")
    if not text:
        return ""
    return safe_link(f"https://www.instagram.com/{text}/", f"@{text}")


def email_link(email: object) -> str:
    text = clean_text(email)
    if not text:
        return ""
    return f"<a href='mailto:{escape(text, quote=True)}'>{escape(text)}</a>"


def table_cell(column: str, value: object) -> str:
    text = clean_text(value, 220)
    if not text:
        return ""
    if column in {"priority", "status", "dm_status", "email_status", "engagement_review_status", "outcome"}:
        return chip(text)
    if column == "instagram_handle":
        return instagram_handle_link(text)
    if column in {"instagram_url", "website", "book_call_link", "application_link", "contact_form_url", "link_in_bio_url"}:
        return safe_link(text)
    if column == "email":
        return email_link(text)
    return escape(text)


def section_header(title: str, copy: str = "", kicker: str = "") -> None:
    if kicker:
        st.markdown(f"<div class='section-kicker'>{escape(kicker)}</div>", unsafe_allow_html=True)
    st.subheader(title)
    if copy:
        st.markdown(f"<p class='section-copy'>{escape(copy)}</p>", unsafe_allow_html=True)


def render_stat_cards(cards: Iterable[Tuple[str, object, str]], columns: int = 4) -> None:
    card_list = list(cards)
    if not card_list:
        return
    for row_start in range(0, len(card_list), columns):
        cols = st.columns(min(columns, len(card_list) - row_start))
        for col, (label, value, help_text) in zip(cols, card_list[row_start : row_start + columns]):
            with col:
                st.markdown(
                    f"""
                    <div class='stat-card'>
                      <div class='stat-label'>{escape(label)}</div>
                      <div class='stat-value'>{escape(str(value))}</div>
                      <div class='stat-help'>{escape(help_text)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_detail_panel(title: str, items: Iterable[Tuple[str, object]], note: str = "") -> None:
    rows = []
    for label, value in items:
        raw_value = clean_text(value)
        if not raw_value:
            continue
        if label.lower() in {"instagram", "website", "book call", "application"}:
            rendered_value = safe_link(raw_value)
        elif label.lower() == "email":
            rendered_value = email_link(raw_value)
        elif label.lower() in {"priority", "status", "dm status", "email status", "engagement review"}:
            rendered_value = chip(raw_value)
        else:
            rendered_value = escape(raw_value)
        rows.append(
            f"<div><span class='detail-label'>{escape(label)}</span><span class='detail-value'>{rendered_value}</span></div>"
        )
    note_html = f"<p class='section-copy'>{escape(note)}</p>" if note else ""
    st.markdown(
        f"""
        <div class='detail-panel'>
          <div class='panel-title'>{escape(title)}</div>
          <div class='detail-grid'>{''.join(rows)}</div>
          {note_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_action_band(title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class='action-band'>
          <strong>{escape(title)}</strong>
          <p>{escape(copy)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def count_rows(rows: Iterable[Dict[str, object]], column: str, value: str) -> int:
    return sum(1 for row in rows if row.get(column) == value)


def prospect_label(row: Dict[str, object]) -> str:
    return clean_text(row.get("brand") or row.get("name") or row.get("instagram_handle") or "Unnamed")


def int_stat(stats: Dict[str, object], label: str) -> int:
    try:
        return int(float(str(stats.get(label) or 0)))
    except (TypeError, ValueError):
        return 0


def initials(value: object) -> str:
    text = clean_text(value) or "Lead"
    words = [word for word in re.split(r"[^A-Za-z0-9]+", text) if word]
    if not words:
        return "IG"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


def render_social_header(stats: Dict[str, object], queue: List[Dict[str, object]], due: List[Dict[str, object]], cap: int) -> None:
    title, copy = next_action(stats, queue, due)
    st.markdown(
        f"""
        <div class='social-header'>
          <div class='social-avatar'>EC</div>
          <div>
            <div class='social-title-row'>
              <div>
                <div class='social-name'>Eva's Closer Desk</div>
                <div class='social-handle'>@instagram_first_pipeline - Manual outreach mode</div>
              </div>
              {chip(title)}
            </div>
            <p class='section-copy'>{escape(copy)}</p>
            <div class='social-stats'>
              <div class='social-stat'><strong>{escape(str(stats.get("Total prospects saved", 0)))}</strong><span>Prospects</span></div>
              <div class='social-stat'><strong>{escape(str(stats.get("Priority prospects", 0)))}</strong><span>Priority</span></div>
              <div class='social-stat'><strong>{escape(str(stats.get("Instagram-ready active", 0)))}</strong><span>IG Ready</span></div>
              <div class='social-stat'><strong>{escape(str(len(queue)))}/{escape(str(cap))}</strong><span>Today Queue</span></div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_story_strip(stats: Dict[str, object], queue: List[Dict[str, object]], due: List[Dict[str, object]]) -> None:
    stories = [
        ("Find", "Priority", f"{stats.get('Priority prospects', 0)} high-fit"),
        ("IG", "Ready", f"{stats.get('Instagram-ready active', 0)} profiles"),
        ("Review", "Drafts", f"{max(0, int_stat(stats, 'DMs generated') - int_stat(stats, 'DMs approved'))} pending"),
        ("Send", "Queue", f"{len(queue)} ready"),
        ("Follow", "Due", f"{len(due)} today"),
    ]
    story_html = []
    for ring, title, subtitle in stories:
        story_html.append(
            f"<div class='story-chip'><div class='story-ring'>{escape(ring)}</div>"
            f"<span class='story-title'>{escape(title)}</span>"
            f"<span class='story-subtitle'>{escape(subtitle)}</span></div>"
        )
    st.markdown(f"<div class='story-strip'>{''.join(story_html)}</div>", unsafe_allow_html=True)


def render_activity_card(title: str, copy: str, status: str, actions: Iterable[str]) -> None:
    action_html = "".join(f"<span class='post-action'>{escape(action)}</span>" for action in actions)
    st.markdown(
        f"""
        <div class='feed-card'>
          <div class='post-header'>
            <div class='post-avatar'>{escape(initials(title))}</div>
            <div>
              <span class='post-name'>{escape(title)}</span>
              <span class='post-meta'>{escape(status)}</span>
            </div>
            {chip(status)}
          </div>
          <div class='post-copy'>{escape(copy)}</div>
          <div class='post-actions'>{action_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_prospect_card(row: Dict[str, object], context: str) -> None:
    brand = prospect_label(row)
    handle = clean_text(row.get("instagram_handle"))
    category = clean_text(row.get("category")) or "Uncategorized"
    status = clean_text(row.get("dm_status") or row.get("status") or row.get("priority") or "Review")
    score = clean_text(row.get("fit_score")) or "Unscored"
    notes = clean_text(row.get("scoring_notes") or row.get("bio_notes") or row.get("outreach_angle"), 280)
    if not notes:
        notes = "Review public evidence, confirm fit, and keep personalized claims grounded before outreach."
    link_bits = []
    link_bits.append(instagram_action(row.get("instagram_url")))
    if row.get("website"):
        link_bits.append(safe_link(row.get("website"), "Open Website"))
    else:
        link_bits.append(disabled_action("No verified website"))
    if row.get("email"):
        link_bits.append(email_link(row.get("email")))
    link_html = "".join(f"<span class='post-action'>{link}</span>" for link in link_bits)
    if not link_html:
        link_html = "<span class='post-action'>Add contact source</span>"
    meta = f"{('@' + handle + ' - ') if handle else ''}{category} - Score {score}"
    st.markdown(
        f"""
        <div class='feed-card'>
          <div class='post-header'>
            <div class='post-avatar'>{escape(initials(brand))}</div>
            <div>
              <span class='post-name'>{escape(brand)}</span>
              <span class='post-meta'>{escape(meta)}</span>
            </div>
            {chip(row.get("priority") or status)}
          </div>
          <div class='post-copy'>{escape(notes)}</div>
          <div class='post-actions'>
            <span class='post-action'>{escape(context)}</span>
            <span class='post-action'>{escape(status)}</span>
            {link_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_right_rail(stats: Dict[str, object], queue: List[Dict[str, object]], due: List[Dict[str, object]]) -> None:
    pending_reviews = max(0, int_stat(stats, "DMs generated") - int_stat(stats, "DMs approved"))
    rows = [
        ("Run discovery", "Fill the feed with new nurse, healthcare, ABA, and BCBA prospects."),
        ("Review drafts", f"{pending_reviews} DM draft(s) need approval."),
        ("Manual sends", f"{len(queue)} Instagram prospect(s) are available for today's queue."),
        ("Follow up", f"{len(due)} prospect(s) need a touch today."),
    ]
    row_html = "".join(
        f"<div class='rail-row'><strong>{escape(label)}</strong><span>{escape(copy)}</span></div>" for label, copy in rows
    )
    st.markdown(
        f"""
        <div class='right-rail-panel'>
          <div class='rail-title'>Today</div>
          {row_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class='right-rail-panel'>
          <div class='rail-title'>Safety</div>
          <div class='rail-row'><strong>Manual Instagram sending</strong><span>Drafts can be approved and tracked, but DMs are sent by Eva.</span></div>
          <div class='rail-row'><strong>Evidence-bound personalization</strong><span>Use public facts only and keep unknowns marked as unknown.</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def runtime_settings(conn) -> Dict[str, str]:
    saved = get_settings(conn)
    return {
        "openai_api_key": env_or_setting(saved, "openai_api_key", "OPENAI_API_KEY"),
        "openai_model": env_or_setting(saved, "openai_model", "OPENAI_MODEL") or "gpt-5.5",
        "openai_service_tier": env_or_setting(saved, "openai_service_tier", "OPENAI_SERVICE_TIER") or "default",
        "search_provider": env_or_setting(saved, "search_provider", "SEARCH_PROVIDER") or "sample",
        "search_api_key": env_or_setting(saved, "search_api_key", "SEARCH_API_KEY"),
        "default_daily_outreach_cap": env_or_setting(saved, "default_daily_outreach_cap", "DEFAULT_DAILY_OUTREACH_CAP")
        or "12",
        "dm_automation_mode": saved.get("dm_automation_mode", "Manual MVP mode"),
    }


def render_table(rows: List[Dict[str, object]], columns: List[str]) -> None:
    if not rows:
        st.info("No rows to show yet.")
        return
    header = "".join(f"<th>{escape(column.replace('_', ' ').title())}</th>" for column in columns)
    body = []
    for row in rows:
        cells = "".join(f"<td>{table_cell(column, row.get(column))}</td>" for column in columns)
        body.append(f"<tr>{cells}</tr>")
    st.markdown(
        f"<div class='mvp-table-wrap'><table class='mvp-table'><thead><tr>{header}</tr></thead>"
        + f"<tbody>{''.join(body)}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def priority_chart_rows(prospects: List[Dict[str, object]]) -> List[Dict[str, object]]:
    counts: Dict[str, int] = {}
    for prospect in prospects:
        priority = clean_text(prospect.get("priority")) or "Unknown"
        counts[priority] = counts.get(priority, 0) + 1
    ordered = [priority for priority in PRIORITIES if priority in counts]
    ordered.extend(sorted(priority for priority in counts if priority not in PRIORITIES))
    return [{"priority": priority, "count": counts[priority]} for priority in ordered]


def metric_suffix(label: str) -> str:
    return "%" if label.lower().endswith("rate") else ""


def prospect_options(rows: List[Dict[str, object]]) -> Dict[str, int]:
    options = {}
    for row in rows:
        label = f"{row.get('prospect_id')} - {row.get('brand') or row.get('name') or row.get('instagram_handle') or 'Unnamed'}"
        options[label] = int(row["prospect_id"])
    return options


def next_action(stats: Dict[str, object], queue: List[Dict[str, object]], due: List[Dict[str, object]]) -> Tuple[str, str]:
    total_saved = int(stats.get("Total prospects saved") or 0)
    dms_generated = int(stats.get("DMs generated") or 0)
    dms_approved = int(stats.get("DMs approved") or 0)
    dms_sent = int(stats.get("DMs sent") or 0)

    if due:
        return ("Follow-ups are due", f"{len(due)} prospect(s) need a follow-up today.")
    if dms_approved > dms_sent:
        return ("Send approved DMs manually", f"{dms_approved - dms_sent} approved DM(s) are waiting to be sent and tracked.")
    if dms_generated > dms_approved:
        return ("Review DM drafts", f"{dms_generated - dms_approved} generated DM draft(s) still need approval.")
    if queue:
        return ("Work the Instagram queue", f"{len(queue)} prioritized prospect(s) are ready for DM drafting or review.")
    if total_saved:
        return ("Refresh scoring and pipeline", "Saved prospects exist, but the outreach queue is empty.")
    return ("Run a discovery search", "Sample mode can create starter prospects without API keys.")


def render_sidebar(stats: Dict[str, object], queue: List[Dict[str, object]], due: List[Dict[str, object]], db_path: str) -> None:
    st.sidebar.title("Daily Command")
    sidebar_rows = [
        ("Pipeline", f"{stats.get('Total prospects saved', 0)} saved prospects"),
        ("Priority", f"{stats.get('Priority prospects', 0)} high-fit prospects"),
        ("IG-ready", f"{stats.get('Instagram-ready active', 0)} active profiles"),
        ("Today queue", f"{len(queue)} Instagram-ready"),
        ("Follow-ups", f"{len(due)} due today"),
    ]
    for label, value in sidebar_rows:
        st.sidebar.markdown(
            f"<div class='workflow-row'><strong>{escape(label)}</strong><span>{escape(value)}</span></div>",
            unsafe_allow_html=True,
        )
    st.sidebar.divider()
    st.sidebar.markdown("### Safeguards")
    st.sidebar.markdown(
        "<p class='muted'>Instagram and email sending stay manual in this MVP. Approved drafts are tracked here.</p>",
        unsafe_allow_html=True,
    )
    st.sidebar.caption(f"Database: {db_path}")


def render_today_overview(stats: Dict[str, object], queue: List[Dict[str, object]], due: List[Dict[str, object]], cap: int) -> None:
    title, copy = next_action(stats, queue, due)
    render_stat_cards(
        [
            ("Priority prospects", stats.get("Priority prospects", 0), "Very High or High"),
            ("Instagram-ready", stats.get("Instagram-ready active", 0), "Active profiles"),
            ("Today queue", len(queue), f"Daily cap {cap}"),
            ("Follow-ups due", len(due), today_iso()),
        ]
    )
    render_action_band(title, copy)


def save_scoring(conn, prospect_id: int, prospect: Dict[str, object], openai_key: str = "") -> None:
    from closer_app.llm import classify_and_score

    scored = classify_and_score(prospect, api_key=openai_key)
    update_prospect(conn, prospect_id, scored)


def run_discovery(**kwargs):
    from closer_app.discovery import discover_prospects

    return discover_prospects(**kwargs)


def remember_discovery_results(
    results: List[Dict[str, object]],
    provider: str,
    source: str,
    has_search_key: bool,
) -> None:
    provider_key = (provider or "sample").lower()
    provider_label = provider_key.title()
    st.session_state["discovered_prospects"] = results
    if results and provider_key != "sample" and not has_search_key:
        st.session_state["last_discovery_notice"] = (
            f"No Search API key is saved for {provider_label}, so the app used sample mode and found "
            f"{len(results)} prospect(s). Add a key in Settings for live web search."
        )
    elif results:
        st.session_state["last_discovery_notice"] = (
            f"{source} found {len(results)} prospect(s). Review the evidence, edit anything missing, "
            "then save selected leads into the pipeline."
        )
    elif provider_key != "sample" and has_search_key:
        st.session_state["last_discovery_notice"] = (
            f"No live results came back from {provider_label}. Check the API key, provider quota, or try Sample mode."
        )
    elif provider_key != "sample":
        st.session_state["last_discovery_notice"] = (
            f"{provider_label} needs a Search API key for live results. Add one in Settings or switch to Sample."
        )
    else:
        st.session_state["last_discovery_notice"] = (
            "Sample discovery did not return prospects. Try a broader query or reset to the default sample search."
        )


def make_instagram_dm(prospect: Dict[str, object], api_key: str = "") -> str:
    from closer_app.outreach import generate_instagram_dm

    return generate_instagram_dm(prospect, api_key=api_key)


def make_email(prospect: Dict[str, object], api_key: str = "") -> Dict[str, str]:
    from closer_app.outreach import generate_email

    return generate_email(prospect, api_key=api_key)


def make_follow_up(prospect: Dict[str, object], number: int, channel: str, api_key: str = "") -> str:
    from closer_app.outreach import generate_follow_up

    return generate_follow_up(prospect, number, channel, api_key=api_key)


def make_response_script(scenario: str, prospect: Dict[str, object], api_key: str = "") -> str:
    from closer_app.outreach import generate_response_script

    return generate_response_script(scenario, prospect, api_key=api_key)


conn = get_connection()
settings = runtime_settings(conn)
os.environ.setdefault("OPENAI_MODEL", settings["openai_model"])
os.environ.setdefault("OPENAI_SERVICE_TIER", settings["openai_service_tier"])

inject_ui_styles()

daily_cap = daily_cap_from_settings(settings)
dashboard_stats = metrics(conn)
dashboard_queue = daily_instagram_queue(conn, cap=daily_cap)
dashboard_due = followups_due(conn, today_iso())

st.title("Instagram Closer CRM")
st.markdown(
    "<p class='app-subtitle'>A social-style workspace for finding, reviewing, and manually messaging high-fit closer prospects.</p>",
    unsafe_allow_html=True,
)
render_sidebar(dashboard_stats, dashboard_queue, dashboard_due, connection_db_path(conn))
render_social_header(dashboard_stats, dashboard_queue, dashboard_due, daily_cap)
render_story_strip(dashboard_stats, dashboard_queue, dashboard_due)

tabs = st.tabs(
    [
        "Command Center",
        "Prospect Discovery",
        "Prospects",
        "Scoring",
        "Instagram Outreach",
        "Email Outreach",
        "Follow-Ups",
        "Response Scripts",
        "Metrics",
        "Settings",
    ]
)


with tabs[0]:
    section_header(
        "Command Center",
        "A social feed for today's prospecting actions, priority leads, and manual outreach safeguards.",
        "Home feed",
    )
    feed_col, rail_col = st.columns([1.65, 0.85])
    all_saved_prospects = list_prospects(conn, limit=10000)
    pending_discovery = st.session_state.get("discovered_prospects", [])
    discovery_notice = st.session_state.get("last_discovery_notice")
    with feed_col:
        if discovery_notice:
            render_action_band("Discovery status", discovery_notice)

        if pending_discovery:
            render_activity_card(
                "Discovery results ready",
                f"{len(pending_discovery)} prospect(s) are waiting for review. Save the strongest leads, then draft manual Instagram outreach.",
                "Needs Review",
                ["Review evidence", "Save selected", "Build queue"],
            )
            for row in pending_discovery[:5]:
                render_prospect_card(row, "New discovery")
        elif dashboard_due:
            render_activity_card(
                "Follow-up inbox",
                f"{len(dashboard_due)} prospect(s) are due for a follow-up today. Handle these first before starting new outreach.",
                "Follow-Up Due",
                ["Open Follow-Ups", "Send manually", "Update outcome"],
            )
            for row in dashboard_due[:5]:
                render_prospect_card(row, "Follow-up due")
        elif dashboard_queue:
            render_activity_card(
                "Today's Instagram queue",
                f"{len(dashboard_queue)} prioritized prospect(s) are ready for DM drafting, approval, or manual send tracking.",
                "Ready to Send",
                ["Review profile", "Approve draft", "Track manual send"],
            )
            for row in dashboard_queue[:5]:
                render_prospect_card(row, "Daily queue")
        elif all_saved_prospects:
            render_activity_card(
                "Pipeline needs a next move",
                "Saved prospects exist, but nothing is queued for Instagram today. Check scoring, missing Instagram URLs, or completed statuses.",
                "Needs Review",
                ["Score", "Add Instagram", "Refresh queue"],
            )
            for row in all_saved_prospects[:5]:
                render_prospect_card(row, "Saved prospect")
        else:
            render_activity_card(
                "Start the feed with discovery",
                "Run a sample search to populate the review feed with public prospects. Save only the leads that look credible and evidence-backed.",
                "Not Started",
                ["Sample search", "Review evidence", "Save high-fit leads"],
            )

        action_cols = st.columns(2)
        with action_cols[0]:
            if st.button("Run sample discovery", type="primary", key="command_run_sample_discovery", use_container_width=True):
                with st.spinner("Finding sample prospects..."):
                    discovered_sample = run_discovery(
                        provider="sample",
                        query=PREBUILT_SEARCH_QUERIES["Nurse/Healthcare"][0],
                        api_key=settings["search_api_key"],
                        num_results=10,
                        target_category="Nurse business coach",
                        fetch_pages=False,
                        openai_api_key=settings["openai_api_key"],
                    )
                remember_discovery_results(
                    discovered_sample,
                    "sample",
                    "Sample discovery",
                    bool(settings["search_api_key"]),
                )
                rerun()
        with action_cols[1]:
            if dashboard_queue and st.button("Generate queue DMs", key="command_generate_queue_dms", use_container_width=True):
                for row in dashboard_queue:
                    dm = make_instagram_dm(row, api_key=settings["openai_api_key"])
                    update_prospect(
                        conn,
                        int(row["prospect_id"]),
                        {"dm_draft": dm, "dm_status": "Needs Review", "status": "Needs Review", "date_dm_generated": today_iso()},
                    )
                st.success(f"Generated {len(dashboard_queue)} DM drafts.")
                rerun()
    with rail_col:
        render_right_rail(dashboard_stats, dashboard_queue, dashboard_due)


with tabs[1]:
    section_header(
        "Prospect Discovery",
        "Search public sources, review evidence, and save only the prospects worth a high-quality touch.",
        "Find",
    )
    with st.form("discovery_form"):
        left, right = st.columns([2, 1])
        with left:
            query_group = st.selectbox("Prebuilt query group", list(PREBUILT_SEARCH_QUERIES.keys()))
            selected_query = st.selectbox("Prebuilt search query", PREBUILT_SEARCH_QUERIES[query_group])
            custom_query = st.text_input("Custom search query", value="")
            query = clean_text(custom_query) or selected_query
            target_category = st.selectbox("Target category", TARGET_CATEGORIES[:-1])
        with right:
            provider = st.selectbox(
                "Search provider",
                SEARCH_PROVIDERS,
                index=SEARCH_PROVIDERS.index(settings["search_provider"])
                if settings["search_provider"] in SEARCH_PROVIDERS
                else 0,
            )
            num_results = st.slider("Search results", min_value=1, max_value=25, value=10)
            fetch_pages = st.checkbox("Fetch public page text", value=False)
            st.caption("Sample mode works without API keys. External providers use public search APIs.")
        run_clicked = st.form_submit_button("Run discovery", type="primary", use_container_width=True)

    if provider != "sample" and not settings["search_api_key"]:
        st.info("No Search API key is saved, so this provider will use sample mode. Add a key in Settings for live web results.")

    if run_clicked:
        with st.spinner("Finding and scoring public prospects..."):
            discovered_results = run_discovery(
                provider=provider,
                query=query,
                api_key=settings["search_api_key"],
                num_results=num_results,
                target_category=target_category,
                fetch_pages=fetch_pages,
                openai_api_key=settings["openai_api_key"],
            )
        remember_discovery_results(
            discovered_results,
            provider,
            "Discovery search",
            bool(settings["search_api_key"]),
        )

    discovered = st.session_state.get("discovered_prospects", [])
    if discovered:
        discovery_notice = st.session_state.get("last_discovery_notice")
        if discovery_notice:
            render_action_band("Discovery status", discovery_notice)
        recommended_count = sum(1 for row in discovered if row.get("priority") in {"Very High", "High"})
        render_stat_cards(
            [
                ("Discovered", len(discovered), "Search results"),
                ("Recommended", recommended_count, "Very High or High"),
                ("With Instagram", sum(1 for row in discovered if row.get("instagram_url")), "Manual DM candidates"),
                ("Needs review", sum(1 for row in discovered if row.get("priority") == "Medium"), "Maybe prospects"),
            ]
        )
        render_table(
            discovered,
            [
                "name",
                "brand",
                "category",
                "instagram_url",
                "website",
                "email",
                "offer_type",
                "funnel_type",
                "fit_score",
                "priority",
                "confidence_score",
                "scoring_notes",
            ],
        )
        section_header("Review Queue", "Edit the evidence that matters before saving prospects into the pipeline.")
        review_rows = []
        for index, row in enumerate(discovered):
            label = prospect_label(row) or clean_text(row.get("website")) or f"Prospect {index + 1}"
            score = clean_text(row.get("fit_score")) or "Unscored"
            with st.expander(f"{row.get('priority', 'Review')} - {label} - Score {score}", expanded=index < 2):
                render_prospect_card(row, "Discovery result")
                render_detail_panel(
                    "Evidence Snapshot",
                    [
                        ("Instagram", row.get("instagram_url")),
                        ("Website", row.get("website")),
                        ("Email", row.get("email")),
                        ("Category", row.get("category")),
                        ("Priority", row.get("priority")),
                        ("Fit score", row.get("fit_score")),
                    ],
                    note=clean_text(row.get("scoring_notes"), 260),
                )
                save_it = st.checkbox(
                    "Save prospect",
                    value=row.get("priority") in {"Very High", "High"},
                    key=f"save_discovered_{index}",
                )
                c1, c2 = st.columns(2)
                with c1:
                    edited_name = st.text_input("Name", value=clean_text(row.get("name")), key=f"disc_name_{index}")
                    edited_brand = st.text_input("Brand", value=clean_text(row.get("brand")), key=f"disc_brand_{index}")
                    edited_instagram = st.text_input(
                        "Instagram URL",
                        value=clean_text(row.get("instagram_url")),
                        key=f"disc_instagram_{index}",
                    )
                    edited_email = st.text_input("Email", value=clean_text(row.get("email")), key=f"disc_email_{index}")
                with c2:
                    edited_category = st.selectbox(
                        "Category",
                        TARGET_CATEGORIES,
                        index=TARGET_CATEGORIES.index(row.get("category"))
                        if row.get("category") in TARGET_CATEGORIES
                        else 0,
                        key=f"disc_category_{index}",
                    )
                    edited_website = st.text_input("Website", value=clean_text(row.get("website")), key=f"disc_website_{index}")
                    edited_offer = st.text_input("Offer type", value=clean_text(row.get("offer_type")), key=f"disc_offer_{index}")
                    edited_funnel = st.text_input("Funnel type", value=clean_text(row.get("funnel_type")), key=f"disc_funnel_{index}")
                edited_notes = st.text_area(
                    "Scoring notes",
                    value=clean_text(row.get("scoring_notes")),
                    height=80,
                    key=f"disc_notes_{index}",
                )
                prospect = dict(row)
                prospect.update(
                    {
                        "name": edited_name,
                        "brand": edited_brand,
                        "category": edited_category,
                        "instagram_url": edited_instagram,
                        "website": edited_website,
                        "email": edited_email,
                        "offer_type": edited_offer,
                        "funnel_type": edited_funnel,
                        "scoring_notes": edited_notes,
                    }
                )
                review_rows.append({"save": save_it, "prospect": prospect})
        save_col, _ = st.columns([1, 3])
        with save_col:
            save_clicked = st.button("Save selected prospects", type="primary", use_container_width=True)
        if save_clicked:
            created = updated = 0
            for review in review_rows:
                if review["save"]:
                    prospect = review["prospect"]
                    _, is_new = upsert_prospect(conn, prospect)
                    created += int(is_new)
                    updated += int(not is_new)
            st.success(f"Saved {created} new prospects and updated {updated} duplicates.")
            rerun()
    else:
        discovery_notice = st.session_state.get("last_discovery_notice")
        if discovery_notice:
            render_action_band("Discovery status", discovery_notice)
        render_action_band("No discovery results yet", "Run sample discovery or use a public search provider to fill the review queue.")


with tabs[2]:
    section_header(
        "Prospects",
        "Filter the saved pipeline, inspect the highest-fit records, and keep outreach status clean.",
        "Pipeline",
    )
    filters = st.columns(4)
    with filters[0]:
        filter_status = st.selectbox("Status filter", [""] + OUTREACH_STATUSES)
    with filters[1]:
        filter_priority = st.selectbox("Priority filter", [""] + PRIORITIES)
    with filters[2]:
        filter_category = st.selectbox("Category filter", [""] + TARGET_CATEGORIES)
    with filters[3]:
        limit = st.number_input("Rows", min_value=25, max_value=1000, value=250, step=25)

    prospects = list_prospects(conn, status=filter_status, priority=filter_priority, category=filter_category, limit=int(limit))
    render_stat_cards(
        [
            ("Showing", len(prospects), "Filtered rows"),
            ("Very High", count_rows(prospects, "priority", "Very High"), "Top priority"),
            ("Needs Review", count_rows(prospects, "status", "Needs Review"), "Drafts to inspect"),
            ("Sent", count_rows(prospects, "status", "Sent"), "Manual DMs tracked"),
        ]
    )
    render_table(
        prospects,
        [
            "prospect_id",
            "name",
            "brand",
            "category",
            "instagram_handle",
            "website",
            "email",
            "fit_score",
            "priority",
            "status",
            "dm_status",
            "email_status",
            "outcome",
        ],
    )

    import_col, export_col = st.columns(2)
    with import_col:
        uploaded = st.file_uploader("Import prospects CSV", type=["csv"])
        if uploaded and st.button("Import CSV"):
            result = import_csv(conn, uploaded.getvalue().decode("utf-8"))
            st.success(f"Imported {result['created']} new prospects and updated {result['updated']} duplicates.")
            rerun()
    with export_col:
        st.download_button(
            "Export all prospects CSV",
            data=export_csv(conn),
            file_name=f"closer-prospects-{today_iso()}.csv",
            mime="text/csv",
        )

    options = prospect_options(prospects)
    if options:
        selected_label = st.selectbox("Edit prospect", list(options.keys()))
        selected = get_prospect(conn, options[selected_label])
        if selected:
            render_prospect_card(selected, "Profile record")
            render_detail_panel(
                "Selected Prospect",
                [
                    ("Brand", selected.get("brand")),
                    ("Name", selected.get("name")),
                    ("Instagram", selected.get("instagram_url")),
                    ("Website", selected.get("website")),
                    ("Email", selected.get("email")),
                    ("Priority", selected.get("priority")),
                    ("Status", selected.get("status")),
                    ("Engagement review", selected.get("engagement_review_status")),
                ],
                note=clean_text(selected.get("scoring_notes"), 260),
            )
            with st.form("edit_prospect_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    name = st.text_input("Name", value=clean_text(selected.get("name")))
                    brand = st.text_input("Brand", value=clean_text(selected.get("brand")))
                    category = st.selectbox(
                        "Category",
                        TARGET_CATEGORIES,
                        index=TARGET_CATEGORIES.index(selected.get("category"))
                        if selected.get("category") in TARGET_CATEGORIES
                        else 0,
                    )
                    status = st.selectbox(
                        "Status",
                        OUTREACH_STATUSES,
                        index=OUTREACH_STATUSES.index(selected.get("status"))
                        if selected.get("status") in OUTREACH_STATUSES
                        else 0,
                    )
                with c2:
                    instagram_handle = st.text_input("Instagram handle", value=clean_text(selected.get("instagram_handle")))
                    instagram_url = st.text_input("Instagram URL", value=clean_text(selected.get("instagram_url")))
                    website = st.text_input("Website", value=clean_text(selected.get("website")))
                    email = st.text_input("Email", value=clean_text(selected.get("email")))
                with c3:
                    priority = st.selectbox(
                        "Priority",
                        PRIORITIES,
                        index=PRIORITIES.index(selected.get("priority")) if selected.get("priority") in PRIORITIES else 2,
                    )
                    fit_score = st.text_input("Fit score", value=clean_text(selected.get("fit_score")))
                    engagement_review_status = st.selectbox(
                        "Engagement review",
                        ENGAGEMENT_REVIEW_STATUSES,
                        index=ENGAGEMENT_REVIEW_STATUSES.index(selected.get("engagement_review_status"))
                        if selected.get("engagement_review_status") in ENGAGEMENT_REVIEW_STATUSES
                        else 0,
                    )
                    outcome = st.text_input("Outcome", value=clean_text(selected.get("outcome")))
                bio_notes = st.text_area("Bio / description notes", value=clean_text(selected.get("bio_notes")), height=100)
                response_notes = st.text_area("Response notes", value=clean_text(selected.get("response_notes")), height=80)
                submitted = st.form_submit_button("Save prospect edits", type="primary", use_container_width=True)
                if submitted:
                    update_prospect(
                        conn,
                        int(selected["prospect_id"]),
                        {
                            "name": name,
                            "brand": brand,
                            "category": category,
                            "instagram_handle": instagram_handle,
                            "instagram_url": instagram_url,
                            "website": website,
                            "email": email,
                            "priority": priority,
                            "fit_score": fit_score,
                            "status": status,
                            "engagement_review_status": engagement_review_status,
                            "outcome": outcome,
                            "bio_notes": bio_notes,
                            "response_notes": response_notes,
                        },
                    )
                    st.success("Prospect updated.")
                    rerun()
            delete_col, _ = st.columns([1, 3])
            with delete_col:
                if st.button("Delete selected prospect", use_container_width=True):
                    delete_prospect(conn, int(selected["prospect_id"]))
                    st.warning("Prospect deleted.")
                    rerun()


with tabs[3]:
    section_header(
        "Scoring",
        "Prioritize fit, confidence, and manual engagement review before drafting outreach.",
        "Prioritize",
    )
    prospects = list_prospects(conn, limit=10000)
    render_stat_cards(
        [
            ("Saved", len(prospects), "Pipeline size"),
            ("Scored", sum(1 for row in prospects if clean_text(row.get("fit_score"))), "Has fit score"),
            ("Very High", count_rows(prospects, "priority", "Very High"), "Best fit"),
            ("Manual review", count_rows(prospects, "engagement_review_status", "Needs Manual Review"), "Engagement unknown"),
        ]
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Score unscored prospects", type="primary", use_container_width=True):
            count = 0
            for row in prospects:
                if not clean_text(row.get("fit_score")):
                    save_scoring(conn, int(row["prospect_id"]), row, settings["openai_api_key"])
                    count += 1
            st.success(f"Scored {count} prospects.")
            rerun()
    with c2:
        if st.button("Rescore all prospects", use_container_width=True):
            for row in prospects:
                save_scoring(conn, int(row["prospect_id"]), row, settings["openai_api_key"])
            st.success(f"Rescored {len(prospects)} prospects.")
            rerun()
    render_table(
        list_prospects(conn, limit=10000),
        ["prospect_id", "brand", "category", "fit_score", "priority", "confidence_score", "engagement_review_status", "scoring_notes"],
    )


with tabs[4]:
    section_header(
        "Instagram Outreach",
        "Generate, edit, approve, and manually track DMs for the highest-fit daily queue.",
        "Daily outreach",
    )
    cap = daily_cap
    queue = daily_instagram_queue(conn, cap=cap)
    all_prospects = [row for row in list_prospects(conn, limit=10000) if row.get("instagram_url")]
    sent_outreach = [
        row
        for row in all_prospects
        if clean_text(row.get("dm_status")) == "Sent" or clean_text(row.get("date_dm_sent"))
    ]
    render_stat_cards(
        [
            ("Queue", len(queue), f"Daily cap {cap}"),
            ("Needs Review", count_rows(all_prospects, "dm_status", "Needs Review"), "Draft approval"),
            ("Ready", count_rows(all_prospects, "dm_status", "Ready to Send"), "Manual send lane"),
            ("Sent", len(sent_outreach), "Manual DMs tracked"),
        ]
    )
    if queue:
        render_table(
            queue,
            [
                "prospect_id",
                "brand",
                "instagram_handle",
                "instagram_url",
                "category",
                "priority",
                "fit_score",
                "scoring_notes",
                "dm_status",
                "follow_up_1_date",
            ],
        )
        if st.button("Generate DMs for current queue", type="primary", use_container_width=True):
            for row in queue:
                dm = make_instagram_dm(row, api_key=settings["openai_api_key"])
                update_prospect(
                    conn,
                    int(row["prospect_id"]),
                    {"dm_draft": dm, "dm_status": "Needs Review", "status": "Needs Review", "date_dm_generated": today_iso()},
                )
            st.success(f"Generated {len(queue)} DM drafts.")
            rerun()
    else:
        render_action_band("No Instagram-ready prospects", "Save high-fit prospects with Instagram URLs to populate the daily queue.")

    options = prospect_options(all_prospects)
    if options:
        selected_label = st.selectbox("Instagram prospect", list(options.keys()))
        selected = get_prospect(conn, options[selected_label])
        if selected:
            render_prospect_card(selected, "DM workspace")
            render_detail_panel(
                "Selected Outreach Context",
                [
                    ("Instagram", selected.get("instagram_url")),
                    ("Brand", selected.get("brand")),
                    ("Category", selected.get("category")),
                    ("Priority", selected.get("priority")),
                    ("Fit score", selected.get("fit_score")),
                    ("Candidate status", selected.get("status")),
                    ("DM status", selected.get("dm_status")),
                    ("Engagement review", selected.get("engagement_review_status")),
                    ("Follow-up 1", selected.get("follow_up_1_date")),
                ],
                note=clean_text(selected.get("scoring_notes"), 300),
            )
            st.markdown(instagram_action(selected.get("instagram_url")), unsafe_allow_html=True)
            render_action_band(
                "Why this candidate needs review",
                "DM generation moves candidates into Needs Review. Open Instagram, confirm the public evidence fits, then mark the candidate reviewed before approving or sending.",
            )
            if st.button("Generate DM for selected prospect", type="primary", use_container_width=True):
                dm = make_instagram_dm(selected, api_key=settings["openai_api_key"])
                update_prospect(
                    conn,
                    int(selected["prospect_id"]),
                    {"dm_draft": dm, "dm_status": "Needs Review", "status": "Needs Review", "date_dm_generated": today_iso()},
                )
                st.success("DM generated.")
                rerun()
            review_cols = st.columns(2)
            with review_cols[0]:
                if st.button("Mark Candidate Reviewed", use_container_width=True):
                    update_prospect(
                        conn,
                        int(selected["prospect_id"]),
                        {"status": "Reviewed", "engagement_review_status": "Manually Verified"},
                    )
                    st.success("Candidate marked reviewed.")
                    rerun()
            with review_cols[1]:
                if st.button("Needs More Review", use_container_width=True):
                    update_prospect(
                        conn,
                        int(selected["prospect_id"]),
                        {"status": "Needs Review", "engagement_review_status": "Needs Manual Review"},
                    )
                    st.success("Candidate kept in review.")
                    rerun()
            dm_text = st.text_area("Editable Instagram DM", value=clean_text(selected.get("dm_draft")), height=220)
            actions = st.columns(4)
            with actions[0]:
                if st.button("Save DM draft", use_container_width=True):
                    update_prospect(conn, int(selected["prospect_id"]), {"dm_draft": dm_text, "dm_status": "Needs Review"})
                    st.success("DM draft saved.")
                    rerun()
            with actions[1]:
                if st.button("Approve DM", use_container_width=True):
                    update_prospect(
                        conn,
                        int(selected["prospect_id"]),
                        {"dm_draft": dm_text, "dm_status": "Approved", "status": "Approved", "date_dm_approved": today_iso()},
                    )
                    st.success("DM approved.")
                    rerun()
            with actions[2]:
                if st.button("Ready to Send", use_container_width=True):
                    latest = get_prospect(conn, int(selected["prospect_id"])) or selected
                    ok, message = require_current_approved_dm(latest, dm_text)
                    if not ok:
                        st.error(message)
                    else:
                        update_prospect(conn, int(selected["prospect_id"]), {"dm_status": "Ready to Send", "status": "Ready to Send"})
                        st.success("DM marked ready for manual send.")
                        rerun()
            with actions[3]:
                if st.button("Mark DM Sent", use_container_width=True):
                    latest = get_prospect(conn, int(selected["prospect_id"])) or selected
                    ok, message = require_current_approved_dm(latest, dm_text)
                    if not ok:
                        st.error(message)
                    else:
                        today = today_iso()
                        update_prospect(
                            conn,
                            int(selected["prospect_id"]),
                            {
                                "dm_draft": dm_text,
                                "dm_status": "Sent",
                                "status": "Sent",
                                "date_dm_sent": today,
                                "follow_up_1_date": add_days_iso(today, 2),
                                "follow_up_2_date": add_days_iso(today, 6),
                            },
                        )
                        st.success("DM marked sent and follow-up dates calculated.")
                        rerun()

    if sent_outreach:
        render_action_band(
            "Sent outreach tracker",
            "These candidates have been marked sent in the app, with follow-up dates ready for tracking.",
        )
        render_table(
            sent_outreach,
            [
                "prospect_id",
                "brand",
                "instagram_handle",
                "dm_status",
                "status",
                "date_dm_sent",
                "follow_up_1_date",
                "follow_up_2_date",
            ],
        )
    else:
        render_action_band(
            "No DMs marked sent yet",
            "After you click Mark DM Sent, the candidate will move into the sent tracker below with follow-up dates.",
        )


with tabs[5]:
    section_header(
        "Email Outreach",
        "Prepare polished backup emails for prospects with public email addresses; sending remains manual.",
        "Backup channel",
    )
    email_prospects = [row for row in list_prospects(conn, limit=10000) if row.get("email")]
    render_stat_cards(
        [
            ("Email prospects", len(email_prospects), "Public email found"),
            ("Generated", count_rows(email_prospects, "email_status", "Needs Review"), "Drafts to review"),
            ("Approved", count_rows(email_prospects, "email_status", "Approved"), "Manual-send ready"),
            ("Replies", count_rows(email_prospects, "status", "Replied"), "Tracked outcomes"),
        ]
    )
    options = prospect_options(email_prospects)
    if not options:
        render_action_band("No email prospects yet", "Discovery and imports will surface prospects with public email addresses here.")
    else:
        selected_label = st.selectbox("Email prospect", list(options.keys()))
        selected = get_prospect(conn, options[selected_label])
        if selected:
            render_prospect_card(selected, "Email backup channel")
            render_detail_panel(
                "Selected Email Context",
                [
                    ("Email", selected.get("email")),
                    ("Brand", selected.get("brand")),
                    ("Category", selected.get("category")),
                    ("Priority", selected.get("priority")),
                    ("Email status", selected.get("email_status")),
                    ("Website", selected.get("website")),
                ],
                note=clean_text(selected.get("scoring_notes"), 260),
            )
            if st.button("Generate email", type="primary", use_container_width=True):
                draft = make_email(selected, api_key=settings["openai_api_key"])
                draft.update({"email_status": "Needs Review", "date_email_generated": today_iso()})
                update_prospect(conn, int(selected["prospect_id"]), draft)
                st.success("Email generated.")
                rerun()
            subject = st.text_input("Subject", value=clean_text(selected.get("email_subject")))
            body = st.text_area("Editable email body", value=clean_text(selected.get("email_body")), height=280)
            email_actions = st.columns(2)
            with email_actions[0]:
                if st.button("Save email draft", use_container_width=True):
                    update_prospect(
                        conn,
                        int(selected["prospect_id"]),
                        {"email_subject": subject, "email_body": body, "email_status": "Needs Review"},
                    )
                    st.success("Email draft saved.")
                    rerun()
            with email_actions[1]:
                if st.button("Approve email", use_container_width=True):
                    update_prospect(
                        conn,
                        int(selected["prospect_id"]),
                        {
                            "email_subject": subject,
                            "email_body": body,
                            "email_status": "Approved",
                            "date_email_approved": today_iso(),
                        },
                    )
                    st.success("Email approved.")
                    rerun()
            st.info("Gmail sending is deferred for this MVP. Use approved email drafts for manual sending.")


with tabs[6]:
    section_header(
        "Follow-Ups",
        "Handle due follow-ups and update outcomes quickly after replies or calls.",
        "Nurture",
    )
    due = followups_due(conn, today_iso())
    all_prospects = list_prospects(conn, limit=10000)
    render_stat_cards(
        [
            ("Due today", len(due), today_iso()),
            ("Replied", count_rows(all_prospects, "status", "Replied"), "Needs response"),
            ("Calls booked", count_rows(all_prospects, "status", "Call Booked"), "Sales pipeline"),
            ("Closed", count_rows(all_prospects, "status", "Closed Client"), "Wins tracked"),
        ]
    )
    if due:
        render_table(
            due,
            ["prospect_id", "brand", "status", "follow_up_1_date", "follow_up_1_sent_date", "follow_up_2_date", "follow_up_2_sent_date"],
        )
    else:
        render_action_band("No follow-ups due today", "The queue will populate automatically after DMs are marked sent.")
    options = prospect_options(all_prospects)
    if options:
        selected_label = st.selectbox("Follow-up / outcome prospect", list(options.keys()))
        selected = get_prospect(conn, options[selected_label])
        if selected:
            render_prospect_card(selected, "Follow-up thread")
            render_detail_panel(
                "Follow-Up Context",
                [
                    ("Brand", selected.get("brand")),
                    ("Instagram", selected.get("instagram_url")),
                    ("Email", selected.get("email")),
                    ("Status", selected.get("status")),
                    ("Follow-up 1", selected.get("follow_up_1_date")),
                    ("Follow-up 2", selected.get("follow_up_2_date")),
                ],
                note=clean_text(selected.get("response_notes"), 260),
            )
            follow_col1, follow_col2 = st.columns(2)
            with follow_col1:
                if st.button("Generate follow-up 1", type="primary", use_container_width=True):
                    update_prospect(
                        conn,
                        int(selected["prospect_id"]),
                        {
                            "follow_up_1_dm": make_follow_up(selected, 1, "DM", settings["openai_api_key"]),
                            "follow_up_1_email": make_follow_up(selected, 1, "Email", settings["openai_api_key"]),
                        },
                    )
                    st.success("Follow-up 1 generated.")
                    rerun()
                follow_1_dm = st.text_area("Follow-up 1 DM", value=clean_text(selected.get("follow_up_1_dm")), height=120)
                if st.button("Mark follow-up 1 sent", use_container_width=True):
                    update_prospect(
                        conn,
                        int(selected["prospect_id"]),
                        {"follow_up_1_dm": follow_1_dm, "follow_up_1_sent_date": today_iso(), "status": "Sent"},
                    )
                    st.success("Follow-up 1 marked sent.")
                    rerun()
            with follow_col2:
                if st.button("Generate follow-up 2", type="primary", use_container_width=True):
                    update_prospect(
                        conn,
                        int(selected["prospect_id"]),
                        {
                            "follow_up_2_dm": make_follow_up(selected, 2, "DM", settings["openai_api_key"]),
                            "follow_up_2_email": make_follow_up(selected, 2, "Email", settings["openai_api_key"]),
                        },
                    )
                    st.success("Follow-up 2 generated.")
                    rerun()
                follow_2_dm = st.text_area("Follow-up 2 DM", value=clean_text(selected.get("follow_up_2_dm")), height=120)
                if st.button("Mark follow-up 2 sent", use_container_width=True):
                    update_prospect(
                        conn,
                        int(selected["prospect_id"]),
                        {"follow_up_2_dm": follow_2_dm, "follow_up_2_sent_date": today_iso(), "status": "Sent"},
                    )
                    st.success("Follow-up 2 marked sent.")
                    rerun()

            outcome_cols = st.columns(5)
            outcome_updates = [
                ("Replied", {"status": "Replied", "outcome": "Replied"}),
                ("Call Booked", {"status": "Call Booked", "outcome": "Call Booked"}),
                ("Trial Offered", {"status": "Trial Offered", "outcome": "Trial Offered"}),
                ("Closed Client", {"status": "Closed Client", "outcome": "Closed Client"}),
                ("Not a Fit", {"status": "Not a Fit", "outcome": "Rejected"}),
            ]
            for column, (label, update) in zip(outcome_cols, outcome_updates):
                with column:
                    if st.button(label, use_container_width=True):
                        update_prospect(conn, int(selected["prospect_id"]), update)
                        st.success(f"Marked {label}.")
                        rerun()


with tabs[7]:
    section_header(
        "Response Scripts",
        "Draft concise replies for common objections and prospect questions.",
        "Reply support",
    )
    prospects = list_prospects(conn, limit=10000)
    options = {"No specific prospect": 0}
    options.update(prospect_options(prospects))
    scenario = st.selectbox("Scenario", SCENARIOS)
    selected_label = st.selectbox("Prospect context", list(options.keys()))
    selected = get_prospect(conn, options[selected_label]) if options[selected_label] else {}
    if selected:
        render_detail_panel(
            "Response Context",
            [
                ("Brand", selected.get("brand")),
                ("Category", selected.get("category")),
                ("Priority", selected.get("priority")),
                ("Status", selected.get("status")),
                ("Instagram", selected.get("instagram_url")),
            ],
            note=clean_text(selected.get("response_notes") or selected.get("scoring_notes"), 260),
        )
    else:
        render_action_band("General response mode", "The script will use Eva's positioning without a specific prospect record.")
    if st.button("Generate response script", type="primary", use_container_width=True):
        st.session_state["response_script"] = make_response_script(scenario, selected or {}, settings["openai_api_key"])
    st.text_area("Script", value=st.session_state.get("response_script", ""), height=260)


with tabs[8]:
    section_header(
        "Metrics",
        "Track discovery volume, outreach throughput, replies, calls, trials, and closed-client progress.",
        "Performance",
    )
    stats = metrics(conn)
    render_stat_cards(
        [
            ("Prospects saved", stats.get("Total prospects saved", 0), "Local database"),
            ("DMs sent", stats.get("DMs sent", 0), "Manual sends tracked"),
            ("Response rate", f"{stats.get('Response rate', 0)}%", "Replies / DMs sent"),
            ("Close rate", f"{stats.get('Client close rate', 0)}%", "Closed / DMs sent"),
        ]
    )
    metric_items = list(stats.items())
    for row_start in range(0, len(metric_items), 4):
        cols = st.columns(4)
        for col, (label, value) in zip(cols, metric_items[row_start : row_start + 4]):
            with col:
                suffix = metric_suffix(label)
                st.metric(label, f"{value}{suffix}")
    prospects = list_prospects(conn, limit=10000)
    if prospects:
        render_table(priority_chart_rows(prospects), ["priority", "count"])


with tabs[9]:
    section_header(
        "Settings",
        "Manage local model, search, and daily outreach preferences.",
        "Configuration",
    )
    render_action_band("Local precedence", "Settings are local. Environment variables from .env take precedence when present.")
    with st.form("settings_form"):
        c1, c2 = st.columns(2)
        with c1:
            openai_api_key = st.text_input("OpenAI API key", value=settings["openai_api_key"], type="password")
            openai_model = st.text_input("OpenAI model", value=settings["openai_model"])
            service_tiers = ["default", "auto", "flex", "priority"]
            openai_service_tier = st.selectbox(
                "OpenAI service tier",
                service_tiers,
                index=service_tiers.index(settings["openai_service_tier"])
                if settings["openai_service_tier"] in service_tiers
                else 0,
            )
            search_provider = st.selectbox(
                "Search API provider",
                SEARCH_PROVIDERS,
                index=SEARCH_PROVIDERS.index(settings["search_provider"])
                if settings["search_provider"] in SEARCH_PROVIDERS
                else 0,
            )
            search_api_key = st.text_input("Search API key", value=settings["search_api_key"], type="password")
        with c2:
            default_daily_outreach_cap = st.number_input(
                "Default daily outreach cap",
                min_value=1,
                max_value=25,
                value=daily_cap,
            )
            dm_automation_mode = st.selectbox(
                "DM automation mode",
                ["Manual MVP mode", "Future compliant automation mode"],
                index=0 if settings["dm_automation_mode"] != "Future compliant automation mode" else 1,
            )
        followup_timing = st.text_input("Default follow-up timing", value="48 hours, then 5-7 days")
        if st.form_submit_button("Save settings", type="primary", use_container_width=True):
            save_settings(
                conn,
                {
                    "openai_api_key": openai_api_key,
                    "openai_model": openai_model,
                    "openai_service_tier": openai_service_tier,
                    "search_provider": search_provider,
                    "search_api_key": search_api_key,
                    "default_daily_outreach_cap": str(default_daily_outreach_cap),
                    "dm_automation_mode": dm_automation_mode,
                    "default_follow_up_timing": followup_timing,
                },
            )
            st.success("Settings saved locally.")
            rerun()

    render_detail_panel(
        "Runtime Summary",
        [
            ("Email sending", "Manual/deferred in MVP"),
            ("Instagram sending", "Manual tracking only in MVP"),
            ("OpenAI service tier", settings["openai_service_tier"]),
            ("Database path", connection_db_path(conn)),
        ],
    )
