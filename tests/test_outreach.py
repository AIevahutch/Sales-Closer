import unittest

from closer_app.gmail_service import send_approved_email
from closer_app.outreach import generate_instagram_dm, generate_response_script


class OutreachTests(unittest.TestCase):
    def test_dm_uses_transferable_experience_and_commission_trial(self):
        dm = generate_instagram_dm(
            {
                "name": "Avery Smith",
                "category": "Nurse business coach",
                "bio_notes": "nurse entrepreneur mastermind with application-only enrollment",
                "engagement_review_status": "Needs Manual Review",
            }
        )

        self.assertIn("former RN", dm)
        self.assertIn("commission-only trial", dm)
        self.assertIn("AI/Codex", dm)
        self.assertNotIn("engagement", dm.lower())

    def test_response_script_does_not_claim_closing_experience(self):
        script = generate_response_script("Do you have closing experience?", {})

        self.assertIn("would not position myself", script)
        self.assertIn("commission-only trial", script)

    def test_gmail_requires_approval(self):
        result = send_approved_email(
            {
                "email_status": "Needs Review",
                "email": "person@example.com",
                "email_subject": "Hello",
                "email_body": "Body",
            },
            sender_email="eva@example.com",
            credentials_file="missing.json",
        )

        self.assertEqual(result["ok"], "false")
        self.assertIn("approved", result["message"])


if __name__ == "__main__":
    unittest.main()

