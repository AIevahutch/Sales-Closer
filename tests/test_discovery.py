import unittest
from unittest import mock

from closer_app.discovery import discover_prospects, search_public_web


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

    def test_tavily_uses_bearer_token_auth(self):
        calls = []

        def fake_http_json(url, headers=None, payload=None):
            calls.append({"url": url, "headers": headers or {}, "payload": payload or {}})
            return {"results": [{"title": "Nurse Coach", "url": "https://example.com", "content": "Book a call"}]}

        with mock.patch("closer_app.discovery._http_json", side_effect=fake_http_json):
            results = search_public_web("tavily", "nurse coach", api_key="tvly-test", num_results=3)

        self.assertEqual(len(results), 1)
        self.assertEqual(calls[0]["headers"]["Authorization"], "Bearer tvly-test")
        self.assertNotIn("api_key", calls[0]["payload"])


if __name__ == "__main__":
    unittest.main()
