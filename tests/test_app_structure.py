from pathlib import Path
import unittest

from closer_app.constants import PREBUILT_SEARCH_QUERIES, PROSPECT_COLUMNS


class AppStructureTests(unittest.TestCase):
    def test_app_declares_required_tabs_and_workflows(self):
        app_source = Path("app.py").read_text()

        for tab in [
            "Prospect Discovery",
            "Prospects",
            "Scoring",
            "Instagram Outreach",
            "Email Outreach",
            "Follow-Ups",
            "Response Scripts",
            "Metrics",
            "Settings",
        ]:
            self.assertIn(tab, app_source)

        for label in [
            "Run discovery",
            "Save selected prospects",
            "Generate DMs for current queue",
            "Approve DM",
            "Mark DM Sent",
            "Approve email",
            "Send approved email",
            "Export all prospects CSV",
        ]:
            self.assertIn(label, app_source)

    def test_schema_contains_required_prospect_fields(self):
        for column in [
            "prospect_id",
            "name",
            "brand",
            "category",
            "instagram_handle",
            "instagram_url",
            "website",
            "email",
            "book_call_link",
            "application_link",
            "engagement_review_status",
            "fit_score",
            "priority",
            "status",
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
        ]:
            self.assertIn(column, PROSPECT_COLUMNS)

    def test_prebuilt_queries_cover_target_markets(self):
        all_queries = " ".join(query.lower() for queries in PREBUILT_SEARCH_QUERIES.values() for query in queries)

        for term in ["nurse business coach", "nurse career coach", "aba business coach", "bcba business coach"]:
            self.assertIn(term, all_queries)


if __name__ == "__main__":
    unittest.main()

