import unittest

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


if __name__ == "__main__":
    unittest.main()

