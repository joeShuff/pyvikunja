import unittest
from unittest.mock import AsyncMock, MagicMock

from pyvikunja.api import VikunjaAPI
from pyvikunja.models.bucket import Bucket
from pyvikunja.models.project import Project
from pyvikunja.models.project_view import ProjectView
from pyvikunja.models.task import Task


class TestBucketModel(unittest.TestCase):
    def test_parses_bucket_fields(self):
        bucket = Bucket({
            'id': 15,
            'title': 'In Progress',
            'project_view_id': 3,
            'limit': 0,
            'position': 1.5,
            'count': 4,
            'created': '2024-01-01T00:00:00Z',
            'updated': '2024-01-02T00:00:00Z',
        })

        self.assertEqual(bucket.id, 15)
        self.assertEqual(bucket.title, 'In Progress')
        self.assertEqual(bucket.project_view_id, 3)
        self.assertEqual(bucket.limit, 0)
        self.assertEqual(bucket.position, 1.5)
        self.assertEqual(bucket.count, 4)


class TestProjectKanbanView(unittest.TestCase):
    def _project(self, views):
        return Project(MagicMock(), {'id': 1, 'title': 'Test', 'views': views})

    def test_returns_first_kanban_view_by_position(self):
        project = self._project([
            {'id': 10, 'title': 'Board B', 'view_kind': 'kanban', 'position': 2.0},
            {'id': 11, 'title': 'Board A', 'view_kind': 'kanban', 'position': 1.0},
            {'id': 12, 'title': 'List', 'view_kind': 'list', 'position': 0.0},
        ])

        view = project.get_default_kanban_view()

        self.assertIsNotNone(view)
        self.assertEqual(view.id, 11)
        self.assertEqual(view.title, 'Board A')

    def test_returns_none_when_no_kanban_view(self):
        project = self._project([
            {'id': 12, 'title': 'List', 'view_kind': 'list', 'position': 0.0},
        ])

        self.assertIsNone(project.get_default_kanban_view())

    def test_returns_none_when_views_missing(self):
        project = Project(MagicMock(), {'id': 1, 'title': 'Test'})

        self.assertEqual(project.views, [])
        self.assertIsNone(project.get_default_kanban_view())


class TestTaskBucketParsing(unittest.TestCase):
    def test_parses_bucket_id(self):
        task = Task(MagicMock(), {'id': 1, 'title': 'Task', 'bucket_id': 15})

        self.assertEqual(task.bucket_id, 15)

    def test_treats_zero_bucket_id_as_none(self):
        task = Task(MagicMock(), {'id': 1, 'title': 'Task', 'bucket_id': 0})

        self.assertIsNone(task.bucket_id)

    def test_parses_expanded_buckets(self):
        task = Task(MagicMock(), {
            'id': 1,
            'title': 'Task',
            'bucket_id': 15,
            'buckets': [
                {'id': 15, 'title': 'Doing', 'project_view_id': 3, 'position': 1.0},
                {'id': 16, 'title': 'Done', 'project_view_id': 3, 'position': 2.0},
            ],
        })

        self.assertEqual(len(task.buckets), 2)
        self.assertEqual(task.buckets[0].title, 'Doing')
        self.assertEqual(task.buckets[1].id, 16)


class TestBucketAPI(unittest.IsolatedAsyncioTestCase):
    async def test_get_project_buckets(self):
        api = VikunjaAPI('https://vikunja.example', 'token')
        api._request = AsyncMock(return_value={
            'data': [
                {'id': 1, 'title': 'Todo', 'project_view_id': 3, 'position': 1.0},
                {'id': 2, 'title': 'Done', 'project_view_id': 3, 'position': 2.0},
            ],
            'headers': {},
        })

        buckets = await api.get_project_buckets(project_id=9, view_id=3)

        api._request.assert_awaited_once_with('GET', '/projects/9/views/3/buckets')
        self.assertEqual(len(buckets), 2)
        self.assertIsInstance(buckets[0], Bucket)
        self.assertEqual(buckets[0].title, 'Todo')

    async def test_set_bucket_uses_task_update(self):
        api = MagicMock()
        api.update_task = AsyncMock(return_value={'id': 7, 'title': 'Task', 'bucket_id': 2})
        task = Task(api, {'id': 7, 'title': 'Task', 'bucket_id': 1})

        updated = await task.set_bucket(2)

        api.update_task.assert_awaited_once()
        self.assertEqual(updated.bucket_id, 2)

    async def test_move_task_to_bucket(self):
        api = VikunjaAPI('https://vikunja.example', 'token')
        api._request = AsyncMock(return_value={
            'data': {'task_id': 7, 'bucket_id': 2, 'task': {'id': 7, 'title': 'Task', 'bucket_id': 2}},
            'headers': {},
        })

        task = await api.move_task_to_bucket(project_id=9, view_id=3, bucket_id=2, task_id=7)

        api._request.assert_awaited_once_with(
            'POST',
            '/projects/9/views/3/buckets/2/tasks',
            data={'task_id': 7},
        )
        self.assertEqual(task.id, 7)
        self.assertEqual(task.bucket_id, 2)

    async def test_get_tasks_passes_expand_parameter(self):
        api = VikunjaAPI('https://vikunja.example', 'token')
        api.get_paginated_data = AsyncMock(return_value=[
            {'id': 1, 'title': 'Task', 'bucket_id': 15},
        ])

        tasks = await api.get_tasks(project_id=9, expand='buckets')

        api.get_paginated_data.assert_awaited_once_with(
            '/projects/9/tasks',
            extra_params={'expand': 'buckets'},
        )
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].bucket_id, 15)


if __name__ == '__main__':
    unittest.main()
