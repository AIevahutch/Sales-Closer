import unittest

from closer_app.scoring import classify_category, priority_for_score, score_prospect


class ScoringTests(unittest.TestCase):
    def test_scores_very_high_target_fit(self):
        prospect = {
            "brand": "RN Business Coach",
            "bio_notes": "Nurse entrepreneur mastermind with testimonials and cohort enrollment.",
            "instagram_url": "https://www.instagram.com/rncoachstudio/",
            "website": "https://rncoach.example",
            "email": "hello@rncoach.example",
            "book_call_link": "https://rncoach.example/book-a-call",
            "application_link": "https://rncoach.example/apply",
            "offer_type": "Mastermind",
            "estimated_offer_price": "Unknown",
            "funnel_type": "Application funnel",
            "testimonials_notes": "Client wins listed publicly.",
            "launch_or_cohort_notes": "Spring cohort enrollment open.",
            "why_they_might_need_a_closer": "Warm enrollment leads likely need follow-up.",
            "outreach_angle": "Help with enrollment calls.",
        }

        scored = score_prospect(prospect)

        self.assertEqual(scored["category"], "Nurse business coach")
        self.assertGreaterEqual(scored["fit_score"], 80)
        self.assertEqual(scored["priority"], "Very High")

    def test_not_a_fit_is_capped(self):
        prospect = {
            "brand": "Generic Fitness Store",
            "bio_notes": "Retail fitness equipment and apparel.",
            "website": "https://fitness.example",
            "email": "hi@fitness.example",
        }

        scored = score_prospect(prospect)

        self.assertEqual(scored["category"], "Not a fit")
        self.assertLess(scored["fit_score"], 40)
        self.assertEqual(scored["priority"], "Do Not Contact")

    def test_unverified_engagement_requires_manual_review(self):
        prospect = {
            "brand": "ABA Practice Growth",
            "bio_notes": "ABA clinic growth consulting for BCBA private practice owners.",
            "instagram_url": "https://www.instagram.com/abagrowth/",
            "engagement_notes": "Looks active but not manually checked.",
        }

        scored = score_prospect(prospect)

        self.assertEqual(scored["engagement_review_status"], "Needs Manual Review")
        self.assertNotIn("engagement manually verified", scored["scoring_notes"])

    def test_priority_thresholds(self):
        self.assertEqual(priority_for_score(80), "Very High")
        self.assertEqual(priority_for_score(60), "High")
        self.assertEqual(priority_for_score(40), "Medium")
        self.assertEqual(priority_for_score(39), "Do Not Contact")

    def test_classifies_bcba_before_general_aba(self):
        category, confidence = classify_category({"bio_notes": "BCBA business coach for ABA clinic owners"})

        self.assertEqual(category, "BCBA business coach")
        self.assertGreaterEqual(confidence, 80)


if __name__ == "__main__":
    unittest.main()

