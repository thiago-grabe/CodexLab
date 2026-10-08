import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from app import service, store


class TaskServiceTests(unittest.TestCase):
    def setUp(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.data_file = Path(temporary_directory.name) / "tasks.json"
        self.original_tasks = json.loads(store.DATA_FILE.read_text(encoding="utf-8"))
        self.data_file.write_text(json.dumps(self.original_tasks), encoding="utf-8")
        data_file_patch = patch.object(store, "DATA_FILE", self.data_file)
        data_file_patch.start()
        self.addCleanup(data_file_patch.stop)

    def test_list_without_status_returns_all_tasks(self):
        self.assertEqual(service.list_tasks(), self.original_tasks)

    def test_status_filters_return_only_matching_tasks(self):
        for status in ("open", "done"):
            with self.subTest(status=status):
                expected = [task for task in self.original_tasks if task["status"] == status]
                self.assertTrue(expected)
                self.assertEqual(service.list_tasks(status=status), expected)

    def test_completion_persists_status_and_timestamp(self):
        completed = service.complete_task(1)
        self.assertEqual(completed["status"], "done")
        self.assertIsNotNone(datetime.fromisoformat(completed["completed_at"]).tzinfo)
        self.assertEqual(service.get_task(1), completed)
        stored_tasks = json.loads(self.data_file.read_text(encoding="utf-8"))
        self.assertEqual(stored_tasks[0], completed)
        self.assertEqual(stored_tasks[1:], self.original_tasks[1:])
        self.assertNotIn(1, [task["id"] for task in service.list_tasks(status="open")])
        self.assertIn(1, [task["id"] for task in service.list_tasks(status="done")])

    def test_completing_missing_task_does_not_change_storage(self):
        original_bytes = self.data_file.read_bytes()
        self.assertIsNone(service.complete_task(999))
        self.assertEqual(self.data_file.read_bytes(), original_bytes)


class TaskSearchTests(unittest.TestCase):
    def test_search_and_status_combinations(self):
        tasks = [
            {"id": 1, "title": "Launch recap", "description": "Product summary", "status": "open"},
            {"id": 2, "title": "Weekly report", "description": "Review the LAUNCH", "status": "done"},
            {"id": 3, "title": "Workshop", "description": "Partner onboarding", "status": "open"},
        ]
        cases = [
            (None, None, [1, 2, 3]),
            ("open", None, [1, 3]),
            ("done", None, [2]),
            (None, "LaUnCh", [1, 2]),
            (None, "EPORT", [2]),
            (None, "ONBOARD", [3]),
            ("open", "LAUNCH", [1]),
            ("done", "launch", [2]),
            ("done", "workshop", []),
            (None, "no-match", []),
        ]
        with patch.object(service, "load_tasks", return_value=tasks):
            for status, query, expected_ids in cases:
                with self.subTest(status=status, q=query):
                    result = service.list_tasks(status=status, q=query)
                    self.assertEqual([task["id"] for task in result], expected_ids)


if __name__ == "__main__":
    unittest.main()
