# Automated Instagram-First Closer Client Acquisition System

Local Streamlit app for helping Eva Hutchins discover, score, prioritize, and follow up with nurse, healthcare, ABA, autism, and BCBA business coaching prospects.

## What The MVP Does

- Runs public prospect discovery through a pluggable search provider.
- Extracts public search/profile signals into a local SQLite prospect database.
- Classifies and scores prospects with explainable fit reasons.
- Prioritizes Very High and High-fit Instagram outreach.
- Generates personalized Instagram DMs for review and manual sending.
- Generates personalized emails and sends only after approval through Gmail API.
- Calculates follow-up dates and tracks replies, booked calls, trials, and closed clients.
- Supports CSV import/export and daily metrics.

## Local Setup

1. Create a virtual environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Create a local environment file.

```bash
cp .env.example .env
```

4. Add keys as available.

```bash
OPENAI_API_KEY=your_openai_key
SEARCH_PROVIDER=sample
SEARCH_API_KEY=
GMAIL_CREDENTIALS_FILE=data/gmail_credentials.json
SENDER_EMAIL=you@example.com
```

Use `SEARCH_PROVIDER=sample` for no-cost demo discovery. Supported public search API provider values are `sample`, `tavily`, `brave`, and `serpapi`.

5. Run the app locally.

```bash
streamlit run app.py
```

6. First daily workflow.

- Open Prospect Discovery.
- Choose a prebuilt query or enter a custom query.
- Run discovery.
- Review and save selected prospects.
- Open Instagram Outreach.
- Generate the first 10-15 DMs.
- Edit and approve DMs.
- Open Instagram profile links and send manually.
- Mark DMs as sent.
- Track replies and follow-ups.

## Gmail API

Email sending is approval-gated. The app will not send email unless the prospect email status is `Approved`.

To enable Gmail:

- Create OAuth client credentials in Google Cloud for Gmail API.
- Save the client secret JSON at `data/gmail_credentials.json`.
- Set `SENDER_EMAIL`.
- Approve an email draft in the app, then click `Send approved email`.
- The first send opens a local OAuth flow and stores `data/gmail_token.json`.

## Safety Rules

- Use public web/search results only.
- Do not scrape private data or bypass platform restrictions.
- Instagram sending is manual in the MVP.
- Email sending requires explicit approval.
- Unknown pricing stays `Unknown`.
- Unverified Instagram engagement stays `Needs Manual Review`.
- Outreach must not claim Eva has already closed high-ticket coaching offers.

## Tests

Run the dependency-light core test suite with:

```bash
python3 -m unittest discover -s tests
```

