import unittest
from unittest.mock import AsyncMock, MagicMock

from pyvikunja.api import APIError, VikunjaAPI
from pyvikunja.models.task import Task
from pyvikunja.models.user import User


class TestAssigneeAPI(unittest.IsolatedAsyncioTestCase):
    async def test_get_task_assignees(self):
        api = VikunjaAPI('https://vikunja.example', 'token')
        api.get_paginated_data = AsyncMock(return_value=[
            {'id': 1, 'username': 'alice', 'name': 'Alice'},
            {'id': 2, 'username': 'bob', 'name': 'Bob'},
        ])

        assignees = await api.get_task_assignees(task_id=7)

        api.get_paginated_data.assert_awaited_once_with('/tasks/7/assignees')
        self.assertEqual(len(assignees), 2)
        self.assertIsInstance(assignees[0], User)
        self.assertEqual(assignees[0].username, 'alice')

    async def test_add_task_assignee(self):
        api = VikunjaAPI('https://vikunja.example', 'token')
        api._request = AsyncMock(return_value={'data': {}, 'headers': {}})

        await api.add_task_assignee(task_id=7, user_id=3)

        api._request.assert_awaited_once_with(
            'PUT',
            '/tasks/7/assignees',
            data={'user_id': 3},
        )

    async def test_add_task_assignee_treats_already_assigned_as_success(self):
        api = VikunjaAPI('https://vikunja.example', 'token')
        api._request = AsyncMock(
            side_effect=APIError(
                400,
                'HTTP error: {"code":4021,"message":"This user is already assigned to that task."}',
            )
        )

        # Should not raise
        await api.add_task_assignee(task_id=7, user_id=3)

    async def test_add_task_assignee_reraises_other_errors(self):
        api = VikunjaAPI('https://vikunja.example', 'token')
        api._request = AsyncMock(
            side_effect=APIError(
                403,
                'HTTP error: {"code":4005,"message":"You don\'t have the permission to see this task."}',
            )
        )

        with self.assertRaises(APIError):
            await api.add_task_assignee(task_id=7, user_id=3)

    async def test_remove_task_assignee(self):
        api = VikunjaAPI('https://vikunja.example', 'token')
        api._request = AsyncMock(return_value={'data': {}, 'headers': {}})

        await api.remove_task_assignee(task_id=7, user_id=3)

        api._request.assert_awaited_once_with(
            'DELETE',
            '/tasks/7/assignees/3',
        )

    async def test_set_task_assignees_bulk(self):
        api = VikunjaAPI('https://vikunja.example', 'token')
        api._request = AsyncMock(return_value={'data': {}, 'headers': {}})
        api.get_task_assignees = AsyncMock(return_value=[
            User({'id': 1, 'username': 'alice'}),
            User({'id': 5, 'username': 'eve'}),
        ])

        assignees = await api.set_task_assignees(task_id=7, user_ids=[1, 5])

        api._request.assert_awaited_once_with(
            'POST',
            '/tasks/7/assignees/bulk',
            data={'assignees': [{'id': 1}, {'id': 5}]},
        )
        api.get_task_assignees.assert_awaited_once_with(7)
        self.assertEqual([user.id for user in assignees], [1, 5])


class TestTaskAssigneeMethods(unittest.IsolatedAsyncioTestCase):
    async def test_add_assignee_does_not_use_task_update(self):
        # Assignees are read-only on task update, so the assignee endpoint must be used
        api = MagicMock()
        api.add_task_assignee = AsyncMock()
        api.get_task = AsyncMock(return_value=Task(api, {
            'id': 7,
            'title': 'Task',
            'assignees': [{'id': 3, 'username': 'carol'}],
        }))
        task = Task(api, {'id': 7, 'title': 'Task', 'assignees': []})

        await task.add_assignee(3)

        api.add_task_assignee.assert_awaited_once_with(7, 3)
        api.update_task.assert_not_called()
        self.assertEqual(len(task.assignees), 1)
        self.assertEqual(task.assignees[0].id, 3)

    async def test_add_assignee_skips_existing(self):
        api = MagicMock()
        api.add_task_assignee = AsyncMock()
        api.get_task = AsyncMock(return_value=Task(api, {
            'id': 7,
            'title': 'Task',
            'assignees': [{'id': 3, 'username': 'carol'}],
        }))
        task = Task(api, {
            'id': 7,
            'title': 'Task',
            'assignees': [{'id': 3, 'username': 'carol'}],
        })

        await task.add_assignee(3)

        api.add_task_assignee.assert_not_awaited()
        api.get_task.assert_awaited_once_with(7)

    async def test_add_assignees_skips_existing(self):
        api = MagicMock()
        api.add_task_assignee = AsyncMock()
        api.get_task = AsyncMock(return_value=Task(api, {
            'id': 7,
            'title': 'Task',
            'assignees': [
                {'id': 1, 'username': 'alice'},
                {'id': 2, 'username': 'bob'},
            ],
        }))
        task = Task(api, {
            'id': 7,
            'title': 'Task',
            'assignees': [{'id': 1, 'username': 'alice'}],
        })

        await task.add_assignees([1, 2])

        api.add_task_assignee.assert_awaited_once_with(7, 2)
        self.assertEqual({user.id for user in task.assignees}, {1, 2})

    async def test_remove_assignee(self):
        api = MagicMock()
        api.remove_task_assignee = AsyncMock()
        api.get_task = AsyncMock(return_value=Task(api, {
            'id': 7,
            'title': 'Task',
            'assignees': [],
        }))
        task = Task(api, {
            'id': 7,
            'title': 'Task',
            'assignees': [{'id': 3, 'username': 'carol'}],
        })

        await task.remove_assignee(3)

        api.remove_task_assignee.assert_awaited_once_with(7, 3)
        api.update_task.assert_not_called()
        self.assertEqual(task.assignees, [])

    async def test_set_assignees_replaces_via_bulk(self):
        api = MagicMock()
        api.set_task_assignees = AsyncMock(return_value=[
            User({'id': 5, 'username': 'eve'}),
        ])
        api.get_task = AsyncMock(return_value=Task(api, {
            'id': 7,
            'title': 'Task',
            'assignees': [{'id': 5, 'username': 'eve'}],
        }))
        task = Task(api, {
            'id': 7,
            'title': 'Task',
            'assignees': [{'id': 1, 'username': 'alice'}],
        })

        await task.set_assignees([5])

        api.set_task_assignees.assert_awaited_once_with(7, [5])
        api.update_task.assert_not_called()
        self.assertEqual([user.id for user in task.assignees], [5])

    async def test_assign_to_user_is_deprecated_alias_of_add_assignee(self):
        api = MagicMock()
        api.add_task_assignee = AsyncMock()
        api.get_task = AsyncMock(return_value=Task(api, {
            'id': 7,
            'title': 'Task',
            'assignees': [
                {'id': 1, 'username': 'alice'},
                {'id': 3, 'username': 'carol'},
            ],
        }))
        task = Task(api, {
            'id': 7,
            'title': 'Task',
            'assignees': [{'id': 1, 'username': 'alice'}],
        })

        with self.assertWarns(DeprecationWarning):
            await task.assign_to_user(3)

        api.add_task_assignee.assert_awaited_once_with(7, 3)
        api.update_task.assert_not_called()
        # Existing assignees are kept, not replaced
        self.assertEqual({user.id for user in task.assignees}, {1, 3})


if __name__ == '__main__':
    unittest.main()
