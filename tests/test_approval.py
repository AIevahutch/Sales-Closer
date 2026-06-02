import unittest

from closer_app.approval import require_current_approved_dm, require_current_approved_email


class ApprovalGateTests(unittest.TestCase):
    def test_dm_must_be_approved_before_ready_or_sent(self):
        ok, message = require_current_approved_dm(
            {"dm_status": "Needs Review", "dm_draft": "Hi there"},
            "Hi there",
        )

        self.assertFalse(ok)
        self.assertIn("Approve", message)

    def test_dm_text_changes_after_approval_require_reapproval(self):
        ok, message = require_current_approved_dm(
            {"dm_status": "Approved", "dm_draft": "Approved message"},
            "Edited message",
        )

        self.assertFalse(ok)
        self.assertIn("changed after approval", message)

    def test_ready_dm_with_matching_text_passes(self):
        ok, message = require_current_approved_dm(
            {"dm_status": "Ready to Send", "dm_draft": "Approved message"},
            "Approved message",
        )

        self.assertTrue(ok)
        self.assertEqual(message, "")

    def test_email_must_match_approved_subject_and_body(self):
        ok, message = require_current_approved_email(
            {
                "email_status": "Approved",
                "email_subject": "Approved subject",
                "email_body": "Approved body",
            },
            "Approved subject",
            "Edited body",
        )

        self.assertFalse(ok)
        self.assertIn("changed after approval", message)

    def test_approved_email_with_matching_text_passes(self):
        ok, message = require_current_approved_email(
            {
                "email_status": "Approved",
                "email_subject": "Approved subject",
                "email_body": "Approved body",
            },
            "Approved subject",
            "Approved body",
        )

        self.assertTrue(ok)
        self.assertEqual(message, "")


if __name__ == "__main__":
    unittest.main()
