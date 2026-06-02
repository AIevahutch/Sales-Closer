import unittest
from unittest import mock

from closer_app.discovery import discover_prospects


class DiscoveryTests(unittest.TestCase):
    def test_sample_discovery_returns_scored_public_prospects(self):
        prospects = discover_prospects(
            provider="sample",
            query="nurse business coach book a call",
            num_results=2,
            target_category="Nurse business coach",
        )

        self.assertEqual(len(prospects), 2)
        self.assertTrue(all(prospect["discovery_source"] == "public search" for prospect in prospects))
        self.assertTrue(all(prospect["fit_score"] for prospect in prospects))
        self.assertTrue(all(prospect["engagement_review_status"] == "Needs Manual Review" for prospect in prospects))
        self.assertEqual(prospects[0]["instagram_url"], "https://www.instagram.com/rncoachstudio/")

    def test_provider_errors_do_not_create_fake_prospects(self):
        with mock.patch("closer_app.discovery._http_json", side_effect=TimeoutError("network timeout")):
            prospects = discover_prospects(
                provider="tavily",
                query="nurse business coach",
                api_key="test-key",
                num_results=5,
                target_category="Nurse business coach",
            )

        self.assertEqual(prospects, [])


if __name__ == "__main__":
    unittest.main()
