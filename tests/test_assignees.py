import unittest
from unittest.mock import AsyncMock

from pyvikunja.api import APIError, VikunjaAPI
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


if __name__ == '__main__':
    unittest.main()
