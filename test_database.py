import os
import tempfile
import unittest

import database


class TestGetLogsForDate(unittest.TestCase):
    def setUp(self):
        self._orig_db = database.DB_FILE
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database.DB_FILE = self._tmp.name
        self._tmp.close()
        database.init_db()

    def tearDown(self):
        database.DB_FILE = self._orig_db
        os.unlink(self._tmp.name)

    def test_filters_correctly(self):
        database.add_log("2026-03-10T08:00:00")
        database.add_log("2026-03-10T14:30:00")
        database.add_log("2026-03-11T09:00:00")

        results = database.get_logs_for_date("2026-03-10")
        dates = [r["timestamp"].split("T")[0] for r in results]
        self.assertEqual(dates, ["2026-03-10", "2026-03-10"])

    def test_returns_id_and_timestamp(self):
        database.add_log("2026-03-10T08:00:00")
        results = database.get_logs_for_date("2026-03-10")
        self.assertEqual(len(results), 1)
        self.assertIn("id", results[0])
        self.assertIn("timestamp", results[0])
        self.assertIsInstance(results[0]["id"], int)
        self.assertIsInstance(results[0]["timestamp"], str)

    def test_empty_returns_empty_list(self):
        results = database.get_logs_for_date("2026-03-10")
        self.assertEqual(results, [])


class TestDeleteLog(unittest.TestCase):
    def setUp(self):
        self._orig_db = database.DB_FILE
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database.DB_FILE = self._tmp.name
        self._tmp.close()
        database.init_db()

    def tearDown(self):
        database.DB_FILE = self._orig_db
        os.unlink(self._tmp.name)

    def test_removes_entry(self):
        database.add_log("2026-03-10T08:00:00")
        logs = database.get_logs_for_date("2026-03-10")
        log_id = logs[0]["id"]

        result = database.delete_log(log_id)
        self.assertTrue(result)
        self.assertEqual(database.get_logs_for_date("2026-03-10"), [])

    def test_nonexistent_returns_false(self):
        result = database.delete_log(99999)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
