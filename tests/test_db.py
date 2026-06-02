import sqlite3
import unittest

from closer_app.db import daily_instagram_queue, get_prospect, init_db, list_prospects, upsert_prospect


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        init_db(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_upsert_deduplicates_by_instagram_handle(self):
        first_id, first_new = upsert_prospect(
            self.conn,
            {
                "brand": "Nurse Coach Studio",
                "instagram_handle": "@nursecoachstudio",
                "website": "https://nursecoach.example",
            },
        )
        second_id, second_new = upsert_prospect(
            self.conn,
            {
                "brand": "Nurse Coach Studio Updated",
                "instagram_url": "https://www.instagram.com/nursecoachstudio/",
                "email": "hello@nursecoach.example",
            },
        )

        self.assertTrue(first_new)
        self.assertFalse(second_new)
        self.assertEqual(first_id, second_id)
        self.assertEqual(len(list_prospects(self.conn)), 1)
        saved = get_prospect(self.conn, first_id)
        self.assertEqual(saved["email"], "hello@nursecoach.example")

    def test_upsert_deduplicates_by_domain(self):
        first_id, _ = upsert_prospect(self.conn, {"brand": "ABA Growth", "website": "https://www.abagrowth.example/apply"})
        second_id, second_new = upsert_prospect(self.conn, {"brand": "ABA Growth Consulting", "website": "https://abagrowth.example/book"})

        self.assertFalse(second_new)
        self.assertEqual(first_id, second_id)

    def test_daily_queue_uses_medium_only_when_no_high_priority_exists(self):
        upsert_prospect(
            self.conn,
            {
                "brand": "Medium Prospect",
                "instagram_url": "https://www.instagram.com/mediumfit/",
                "priority": "Medium",
                "fit_score": "55",
            },
        )
        high_id, _ = upsert_prospect(
            self.conn,
            {
                "brand": "High Prospect",
                "instagram_url": "https://www.instagram.com/highfit/",
                "priority": "High",
                "fit_score": "75",
            },
        )

        queue = daily_instagram_queue(self.conn, cap=12)

        self.assertEqual([row["prospect_id"] for row in queue], [high_id])

    def test_daily_queue_falls_back_to_medium_when_no_high_priority_exists(self):
        medium_id, _ = upsert_prospect(
            self.conn,
            {
                "brand": "Medium Prospect",
                "instagram_url": "https://www.instagram.com/mediumfit/",
                "priority": "Medium",
                "fit_score": "55",
            },
        )

        queue = daily_instagram_queue(self.conn, cap=12)

        self.assertEqual([row["prospect_id"] for row in queue], [medium_id])


if __name__ == "__main__":
    unittest.main()
