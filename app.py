from __future__ import annotations

from html import escape
import os
from typing import Dict, List

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
from closer_app.approval import require_current_approved_dm, require_current_approved_email
from closer_app.db import (
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
from closer_app.utils import add_days_iso, clean_text, env_or_setting, load_dotenv, today_iso


load_dotenv()

st.set_page_config(
    page_title="Instagram-First Closer Acquisition",
    page_icon="",
    layout="wide",
)


def rerun() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    st.experimental_rerun()


def runtime_settings(conn) -> Dict[str, str]:
    saved = get_settings(conn)
    return {
        "openai_api_key": env_or_setting(saved, "openai_api_key", "OPENAI_API_KEY"),
        "openai_model": env_or_setting(saved, "openai_model", "OPENAI_MODEL") or "gpt-4o-mini",
        "search_provider": env_or_setting(saved, "search_provider", "SEARCH_PROVIDER") or "sample",
        "search_api_key": env_or_setting(saved, "search_api_key", "SEARCH_API_KEY"),
        "gmail_credentials_file": env_or_setting(saved, "gmail_credentials_file", "GMAIL_CREDENTIALS_FILE")
        or "data/gmail_credentials.json",
        "sender_email": env_or_setting(saved, "sender_email", "SENDER_EMAIL"),
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
        cells = "".join(f"<td>{escape(clean_text(row.get(column), 220))}</td>" for column in columns)
        body.append(f"<tr>{cells}</tr>")
    st.markdown(
        """
        <style>
          .mvp-table-wrap { overflow-x: auto; margin: 0.5rem 0 1rem; }
          .mvp-table { border-collapse: collapse; min-width: 100%; font-size: 0.88rem; }
          .mvp-table th, .mvp-table td {
            border-bottom: 1px solid rgba(49, 51, 63, 0.16);
            padding: 0.45rem 0.55rem;
            text-align: left;
            vertical-align: top;
          }
          .mvp-table th { font-weight: 700; white-space: nowrap; }
        </style>
        """
        + f"<div class='mvp-table-wrap'><table class='mvp-table'><thead><tr>{header}</tr></thead>"
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


def prospect_options(rows: List[Dict[str, object]]) -> Dict[str, int]:
    options = {}
    for row in rows:
        label = f"{row.get('prospect_id')} - {row.get('brand') or row.get('name') or row.get('instagram_handle') or 'Unnamed'}"
        options[label] = int(row["prospect_id"])
    return options


def save_scoring(conn, prospect_id: int, prospect: Dict[str, object], openai_key: str = "") -> None:
    from closer_app.llm import classify_and_score

    scored = classify_and_score(prospect, api_key=openai_key)
    update_prospect(conn, prospect_id, scored)


def run_discovery(**kwargs):
    from closer_app.discovery import discover_prospects

    return discover_prospects(**kwargs)


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


def send_email_after_approval(prospect: Dict[str, object], sender_email: str, credentials_file: str) -> Dict[str, str]:
    from closer_app.gmail_service import send_approved_email

    return send_approved_email(prospect, sender_email=sender_email, credentials_file=credentials_file)


conn = get_connection()
settings = runtime_settings(conn)
os.environ.setdefault("OPENAI_MODEL", settings["openai_model"])

st.title("Instagram-First Closer Client Acquisition")
st.caption("Local prospect discovery, scoring, Instagram-first outreach, approved email sending, and follow-up tracking.")

tabs = st.tabs(
    [
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
    st.subheader("Prospect Discovery")
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

    if st.button("Run discovery", type="primary"):
        with st.spinner("Finding and scoring public prospects..."):
            st.session_state["discovered_prospects"] = run_discovery(
                provider=provider,
                query=query,
                api_key=settings["search_api_key"],
                num_results=num_results,
                target_category=target_category,
                fetch_pages=fetch_pages,
                openai_api_key=settings["openai_api_key"],
            )

    discovered = st.session_state.get("discovered_prospects", [])
    if discovered:
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
        review_rows = []
        for index, row in enumerate(discovered):
            label = row.get("brand") or row.get("name") or row.get("website") or f"Prospect {index + 1}"
            with st.expander(f"{row.get('priority', 'Review')} - {label}", expanded=index < 2):
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
        if st.button("Save selected prospects"):
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
        st.info("Run a discovery search or use sample mode to generate starter prospects.")


with tabs[1]:
    st.subheader("Prospects")
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
                submitted = st.form_submit_button("Save prospect edits")
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
            if st.button("Delete selected prospect"):
                delete_prospect(conn, int(selected["prospect_id"]))
                st.warning("Prospect deleted.")
                rerun()


with tabs[2]:
    st.subheader("Scoring")
    prospects = list_prospects(conn, limit=10000)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Score unscored prospects"):
            count = 0
            for row in prospects:
                if not clean_text(row.get("fit_score")):
                    save_scoring(conn, int(row["prospect_id"]), row, settings["openai_api_key"])
                    count += 1
            st.success(f"Scored {count} prospects.")
            rerun()
    with c2:
        if st.button("Rescore all prospects"):
            for row in prospects:
                save_scoring(conn, int(row["prospect_id"]), row, settings["openai_api_key"])
            st.success(f"Rescored {len(prospects)} prospects.")
            rerun()
    render_table(
        list_prospects(conn, limit=10000),
        ["prospect_id", "brand", "category", "fit_score", "priority", "confidence_score", "engagement_review_status", "scoring_notes"],
    )


with tabs[3]:
    st.subheader("Instagram Outreach")
    cap = int(settings["default_daily_outreach_cap"] or 12)
    queue = daily_instagram_queue(conn, cap=cap)
    st.caption(f"Daily queue cap: {cap}. Priority order is Very High, High, then Medium.")
    if queue:
        render_table(
            queue,
            [
                "prospect_id",
                "brand",
                "instagram_handle",
                "category",
                "priority",
                "fit_score",
                "scoring_notes",
                "dm_status",
                "follow_up_1_date",
            ],
        )
        if st.button("Generate DMs for current queue"):
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
        st.info("No Instagram-ready prospects are queued yet.")

    all_prospects = [row for row in list_prospects(conn, limit=10000) if row.get("instagram_url")]
    options = prospect_options(all_prospects)
    if options:
        selected_label = st.selectbox("Instagram prospect", list(options.keys()))
        selected = get_prospect(conn, options[selected_label])
        if selected:
            if selected.get("instagram_url"):
                st.markdown(f"[Open Instagram profile]({selected['instagram_url']})")
            st.write(
                {
                    "recommended_action": "Like 1 recent post, leave 1 thoughtful comment if appropriate, watch stories if available, then send the approved DM manually.",
                    "priority": selected.get("priority"),
                    "fit_score": selected.get("fit_score"),
                    "reason_selected": selected.get("scoring_notes"),
                }
            )
            if st.button("Generate DM for selected prospect"):
                dm = make_instagram_dm(selected, api_key=settings["openai_api_key"])
                update_prospect(
                    conn,
                    int(selected["prospect_id"]),
                    {"dm_draft": dm, "dm_status": "Needs Review", "status": "Needs Review", "date_dm_generated": today_iso()},
                )
                st.success("DM generated.")
                rerun()
            dm_text = st.text_area("Editable Instagram DM", value=clean_text(selected.get("dm_draft")), height=220)
            actions = st.columns(4)
            with actions[0]:
                if st.button("Save DM draft"):
                    update_prospect(conn, int(selected["prospect_id"]), {"dm_draft": dm_text, "dm_status": "Needs Review"})
                    st.success("DM draft saved.")
                    rerun()
            with actions[1]:
                if st.button("Approve DM"):
                    update_prospect(
                        conn,
                        int(selected["prospect_id"]),
                        {"dm_draft": dm_text, "dm_status": "Approved", "status": "Approved", "date_dm_approved": today_iso()},
                    )
                    st.success("DM approved.")
                    rerun()
            with actions[2]:
                if st.button("Ready to Send"):
                    latest = get_prospect(conn, int(selected["prospect_id"])) or selected
                    ok, message = require_current_approved_dm(latest, dm_text)
                    if not ok:
                        st.error(message)
                    else:
                        update_prospect(conn, int(selected["prospect_id"]), {"dm_status": "Ready to Send", "status": "Ready to Send"})
                        st.success("DM marked ready for manual send.")
                        rerun()
            with actions[3]:
                if st.button("Mark DM Sent"):
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


with tabs[4]:
    st.subheader("Email Outreach")
    email_prospects = [row for row in list_prospects(conn, limit=10000) if row.get("email")]
    options = prospect_options(email_prospects)
    if not options:
        st.info("No prospects with public email addresses yet.")
    else:
        selected_label = st.selectbox("Email prospect", list(options.keys()))
        selected = get_prospect(conn, options[selected_label])
        if selected:
            st.write({"recipient": selected.get("email"), "email_status": selected.get("email_status")})
            if st.button("Generate email"):
                draft = make_email(selected, api_key=settings["openai_api_key"])
                draft.update({"email_status": "Needs Review", "date_email_generated": today_iso()})
                update_prospect(conn, int(selected["prospect_id"]), draft)
                st.success("Email generated.")
                rerun()
            subject = st.text_input("Subject", value=clean_text(selected.get("email_subject")))
            body = st.text_area("Editable email body", value=clean_text(selected.get("email_body")), height=280)
            email_actions = st.columns(3)
            with email_actions[0]:
                if st.button("Save email draft"):
                    update_prospect(
                        conn,
                        int(selected["prospect_id"]),
                        {"email_subject": subject, "email_body": body, "email_status": "Needs Review"},
                    )
                    st.success("Email draft saved.")
                    rerun()
            with email_actions[1]:
                if st.button("Approve email"):
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
            with email_actions[2]:
                if st.button("Send approved email"):
                    latest = get_prospect(conn, int(selected["prospect_id"])) or selected
                    ok, message = require_current_approved_email(latest, subject, body)
                    if not ok:
                        st.error(message)
                    else:
                        result = send_email_after_approval(
                            latest,
                            sender_email=settings["sender_email"],
                            credentials_file=settings["gmail_credentials_file"],
                        )
                        if result["ok"] == "true":
                            update_prospect(
                                conn,
                                int(selected["prospect_id"]),
                                {"email_status": "Sent", "date_email_sent": today_iso(), "response_notes": result["message"]},
                            )
                            st.success(result["message"])
                            rerun()
                        else:
                            st.error(result["message"])


with tabs[5]:
    st.subheader("Follow-Ups")
    due = followups_due(conn, today_iso())
    if due:
        render_table(
            due,
            ["prospect_id", "brand", "status", "follow_up_1_date", "follow_up_1_sent_date", "follow_up_2_date", "follow_up_2_sent_date"],
        )
    else:
        st.info("No follow-ups due today.")
    all_prospects = list_prospects(conn, limit=10000)
    options = prospect_options(all_prospects)
    if options:
        selected_label = st.selectbox("Follow-up / outcome prospect", list(options.keys()))
        selected = get_prospect(conn, options[selected_label])
        if selected:
            st.write(
                {
                    "follow_up_1_date": selected.get("follow_up_1_date"),
                    "follow_up_2_date": selected.get("follow_up_2_date"),
                    "status": selected.get("status"),
                }
            )
            follow_col1, follow_col2 = st.columns(2)
            with follow_col1:
                if st.button("Generate follow-up 1"):
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
                if st.button("Mark follow-up 1 sent"):
                    update_prospect(
                        conn,
                        int(selected["prospect_id"]),
                        {"follow_up_1_dm": follow_1_dm, "follow_up_1_sent_date": today_iso(), "status": "Sent"},
                    )
                    st.success("Follow-up 1 marked sent.")
                    rerun()
            with follow_col2:
                if st.button("Generate follow-up 2"):
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
                if st.button("Mark follow-up 2 sent"):
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
                    if st.button(label):
                        update_prospect(conn, int(selected["prospect_id"]), update)
                        st.success(f"Marked {label}.")
                        rerun()


with tabs[6]:
    st.subheader("Response Scripts")
    prospects = list_prospects(conn, limit=10000)
    options = {"No specific prospect": 0}
    options.update(prospect_options(prospects))
    scenario = st.selectbox("Scenario", SCENARIOS)
    selected_label = st.selectbox("Prospect context", list(options.keys()))
    selected = get_prospect(conn, options[selected_label]) if options[selected_label] else {}
    if st.button("Generate response script"):
        st.session_state["response_script"] = make_response_script(scenario, selected or {}, settings["openai_api_key"])
    st.text_area("Script", value=st.session_state.get("response_script", ""), height=260)


with tabs[7]:
    st.subheader("Metrics")
    stats = metrics(conn)
    metric_items = list(stats.items())
    for row_start in range(0, len(metric_items), 4):
        cols = st.columns(4)
        for col, (label, value) in zip(cols, metric_items[row_start : row_start + 4]):
            with col:
                suffix = "%" if "rate" in label.lower() else ""
                st.metric(label, f"{value}{suffix}")
    prospects = list_prospects(conn, limit=10000)
    if prospects:
        render_table(priority_chart_rows(prospects), ["priority", "count"])


with tabs[8]:
    st.subheader("Settings")
    st.caption("Settings are local. Environment variables from .env take precedence when present.")
    with st.form("settings_form"):
        c1, c2 = st.columns(2)
        with c1:
            openai_api_key = st.text_input("OpenAI API key", value=settings["openai_api_key"], type="password")
            openai_model = st.text_input("OpenAI model", value=settings["openai_model"])
            search_provider = st.selectbox(
                "Search API provider",
                SEARCH_PROVIDERS,
                index=SEARCH_PROVIDERS.index(settings["search_provider"])
                if settings["search_provider"] in SEARCH_PROVIDERS
                else 0,
            )
            search_api_key = st.text_input("Search API key", value=settings["search_api_key"], type="password")
        with c2:
            gmail_credentials_file = st.text_input("Gmail credentials file", value=settings["gmail_credentials_file"])
            sender_email = st.text_input("Sender email", value=settings["sender_email"])
            default_daily_outreach_cap = st.number_input(
                "Default daily outreach cap",
                min_value=1,
                max_value=25,
                value=int(settings["default_daily_outreach_cap"] or 12),
            )
            dm_automation_mode = st.selectbox(
                "DM automation mode",
                ["Manual MVP mode", "Future compliant automation mode"],
                index=0 if settings["dm_automation_mode"] != "Future compliant automation mode" else 1,
            )
        followup_timing = st.text_input("Default follow-up timing", value="48 hours, then 5-7 days")
        if st.form_submit_button("Save settings"):
            save_settings(
                conn,
                {
                    "openai_api_key": openai_api_key,
                    "openai_model": openai_model,
                    "search_provider": search_provider,
                    "search_api_key": search_api_key,
                    "gmail_credentials_file": gmail_credentials_file,
                    "sender_email": sender_email,
                    "default_daily_outreach_cap": str(default_daily_outreach_cap),
                    "dm_automation_mode": dm_automation_mode,
                    "default_follow_up_timing": followup_timing,
                },
            )
            st.success("Settings saved locally.")
            rerun()

    gmail_status = "Configured" if settings["gmail_credentials_file"] and os.path.exists(settings["gmail_credentials_file"]) else "Not configured"
    st.write(
        {
            "Gmail API credentials status": gmail_status,
            "Instagram sending": "Manual tracking only in MVP",
            "Database path": os.environ.get("CLOSER_DB_PATH", "data/closer_acquisition.sqlite3"),
        }
    )
