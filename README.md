# Automated Instagram-First Closer Client Acquisition System

Local Streamlit app for helping Eva Hutchins discover, score, prioritize, and follow up with nurse, healthcare, ABA, autism, and BCBA business coaching prospects.

## What The MVP Does

- Runs public prospect discovery through a pluggable search provider.
- Extracts public search/profile signals into a local SQLite prospect database.
- Classifies and scores prospects with explainable fit reasons.
- Prioritizes Very High and High-fit Instagram outreach.
- Generates personalized Instagram DMs for review and manual sending.
- Generates personalized email drafts for review and manual sending.
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
OPENAI_MODEL=gpt-5.5
SEARCH_PROVIDER=sample
SEARCH_API_KEY=
```

Use `SEARCH_PROVIDER=sample` for no-cost demo discovery. Supported public search API provider values are `sample`, `tavily`, `brave`, and `serpapi`.
The app does not set `service_tier`, so OpenAI requests use the project default/standard processing unless you configure a different tier in the OpenAI project.

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

## Email

Gmail API sending is intentionally deferred from the MVP. The app can generate, edit, and approve email drafts, but Eva sends any email manually outside the app. This keeps the first version focused on Instagram outreach and avoids OAuth setup complexity.

## Safety Rules

- Use public web/search results only.
- Do not scrape private data or bypass platform restrictions.
- Instagram sending is manual in the MVP.
- Email sending is manual/deferred in the MVP.
- Unknown pricing stays `Unknown`.
- Unverified Instagram engagement stays `Needs Manual Review`.
- Outreach must not claim Eva has already closed high-ticket coaching offers.

## Tests

Run the dependency-light core test suite with:

```bash
python3 -m unittest discover -s tests
```

## Local Runtime Notes

If Streamlit starts slowly or shows frontend/network warnings while this project is stored in iCloud Drive, move the project or at least the virtual environment to a fully local folder with several GB of free disk space, then reinstall dependencies. The app avoids pandas/Arrow-backed Streamlit table widgets, but Streamlit still serves frontend assets from the active environment, so cloud-placeholder files can cause local launch timeouts.
