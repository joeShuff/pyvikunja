import unittest
from unittest.mock import AsyncMock, MagicMock

from pyvikunja.api import VikunjaAPI
from pyvikunja.models.label import Label
from pyvikunja.models.task import Task


class TestLabelAPI(unittest.IsolatedAsyncioTestCase):
    async def test_get_task_labels(self):
        api = VikunjaAPI('https://vikunja.example', 'token')
        api.get_paginated_data = AsyncMock(return_value=[
            {'id': 1, 'title': 'Bug', 'hex_color': 'ff0000'},
            {'id': 2, 'title': 'Feature', 'hex_color': '00ff00'},
        ])

        labels = await api.get_task_labels(task_id=7)

        api.get_paginated_data.assert_awaited_once_with('/tasks/7/labels')
        self.assertEqual(len(labels), 2)
        self.assertIsInstance(labels[0], Label)
        self.assertEqual(labels[0].title, 'Bug')

    async def test_add_task_label(self):
        api = VikunjaAPI('https://vikunja.example', 'token')
        api._request = AsyncMock(return_value={'data': {}, 'headers': {}})

        await api.add_task_label(task_id=7, label_id=3)

        api._request.assert_awaited_once_with(
            'PUT',
            '/tasks/7/labels',
            data={'label_id': 3},
        )

    async def test_remove_task_label(self):
        api = VikunjaAPI('https://vikunja.example', 'token')
        api._request = AsyncMock(return_value={'data': {}, 'headers': {}})

        await api.remove_task_label(task_id=7, label_id=3)

        api._request.assert_awaited_once_with(
            'DELETE',
            '/tasks/7/labels/3',
        )

    async def test_set_task_labels_bulk(self):
        api = VikunjaAPI('https://vikunja.example', 'token')
        api._request = AsyncMock(return_value={'data': {}, 'headers': {}})
        api.get_task_labels = AsyncMock(return_value=[
            Label({'id': 1, 'title': 'Bug'}),
            Label({'id': 5, 'title': 'Urgent'}),
        ])

        labels = await api.set_task_labels(task_id=7, label_ids=[1, 5])

        api._request.assert_awaited_once_with(
            'POST',
            '/tasks/7/labels/bulk',
            data={'labels': [{'id': 1}, {'id': 5}]},
        )
        api.get_task_labels.assert_awaited_once_with(7)
        self.assertEqual([label.id for label in labels], [1, 5])


class TestTaskLabelMethods(unittest.IsolatedAsyncioTestCase):
    # Checks to ensure the broken task_update method of label introduce is not reintroduced
    async def test_add_label_does_not_use_task_update(self):
        api = MagicMock()
        api.add_task_label = AsyncMock()
        api.get_task = AsyncMock(return_value=Task(api, {
            'id': 7,
            'title': 'Task',
            'labels': [{'id': 3, 'title': 'Bug'}],
        }))
        task = Task(api, {'id': 7, 'title': 'Task', 'labels': []})

        await task.add_label(3)

        api.add_task_label.assert_awaited_once_with(7, 3)
        api.update_task.assert_not_called()
        self.assertEqual(len(task.labels), 1)
        self.assertEqual(task.labels[0].id, 3)

    async def test_add_labels_skips_existing(self):
        api = MagicMock()
        api.add_task_label = AsyncMock()
        api.get_task = AsyncMock(return_value=Task(api, {
            'id': 7,
            'title': 'Task',
            'labels': [
                {'id': 1, 'title': 'Bug'},
                {'id': 2, 'title': 'Feature'},
            ],
        }))
        task = Task(api, {
            'id': 7,
            'title': 'Task',
            'labels': [{'id': 1, 'title': 'Bug'}],
        })

        await task.add_labels([1, 2])

        api.add_task_label.assert_awaited_once_with(7, 2)
        self.assertEqual({label.id for label in task.labels}, {1, 2})

    async def test_remove_label(self):
        api = MagicMock()
        api.remove_task_label = AsyncMock()
        api.get_task = AsyncMock(return_value=Task(api, {
            'id': 7,
            'title': 'Task',
            'labels': [],
        }))
        task = Task(api, {
            'id': 7,
            'title': 'Task',
            'labels': [{'id': 3, 'title': 'Bug'}],
        })

        await task.remove_label(3)

        api.remove_task_label.assert_awaited_once_with(7, 3)
        api.update_task.assert_not_called()
        self.assertEqual(task.labels, [])

    async def test_set_labels_replaces_via_bulk(self):
        api = MagicMock()
        api.set_task_labels = AsyncMock(return_value=[
            Label({'id': 5, 'title': 'Urgent'}),
        ])
        api.get_task = AsyncMock(return_value=Task(api, {
            'id': 7,
            'title': 'Task',
            'labels': [{'id': 5, 'title': 'Urgent'}],
        }))
        task = Task(api, {
            'id': 7,
            'title': 'Task',
            'labels': [{'id': 1, 'title': 'Bug'}],
        })

        await task.set_labels([5])

        api.set_task_labels.assert_awaited_once_with(7, [5])
        api.update_task.assert_not_called()
        self.assertEqual([label.id for label in task.labels], [5])


if __name__ == '__main__':
    unittest.main()
