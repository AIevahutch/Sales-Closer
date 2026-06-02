import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from closer_app.db import daily_instagram_queue, get_connection, get_prospect, init_db, list_prospects, upsert_prospect


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

    def test_upsert_canonicalizes_instagram_url(self):
        prospect_id, _ = upsert_prospect(
            self.conn,
            {
                "brand": "RN Business Coach",
                "instagram_url": "https://www.instagram.com/rncoachstudio./",
            },
        )

        saved = get_prospect(self.conn, prospect_id)

        self.assertEqual(saved["instagram_handle"], "rncoachstudio")
        self.assertEqual(saved["instagram_url"], "https://www.instagram.com/rncoachstudio/")

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

    def test_default_connection_falls_back_to_temp_db_on_disk_io_error(self):
        original_connect = sqlite3.connect
        previous_env_path = os.environ.pop("CLOSER_DB_PATH", None)
        calls = []
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                fallback_path = Path(tmpdir) / "closer_acquisition.sqlite3"

                def fake_connect(path):
                    calls.append(path)
                    if len(calls) == 1:
                        raise sqlite3.OperationalError("disk I/O error")
                    return original_connect(path)

                with mock.patch("closer_app.db.DEFAULT_DB_PATH", str(Path(tmpdir) / "broken" / "app.sqlite3")):
                    with mock.patch("closer_app.db.tempfile.gettempdir", return_value=tmpdir):
                        with mock.patch("closer_app.db.sqlite3.connect", side_effect=fake_connect):
                            conn = get_connection()
                try:
                    self.assertEqual(calls[1], str(fallback_path))
                    self.assertEqual(
                        conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'prospects'").fetchone()["name"],
                        "prospects",
                    )
                finally:
                    conn.close()
        finally:
            if previous_env_path is not None:
                os.environ["CLOSER_DB_PATH"] = previous_env_path


if __name__ == "__main__":
    unittest.main()
