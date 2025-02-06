import asyncio
import datetime
import os

from pyvikunja.api import VikunjaAPI
from pyvikunja.models.enum.repeat_mode import RepeatMode
from pyvikunja.models.enum.task_priority import Priority

base_url = os.getenv("VIKUNJA_BASEURL")
token = os.getenv("VIKUNJA_TOKEN")


async def main():
    api = VikunjaAPI(base_url, token)

    # Get all projects
    projects = await api.get_projects()
    for project in projects:
        print(f"Project: {project.title}")

        # Get tasks for each project
        tasks = await project.get_tasks()
        for task in tasks:
            full_details = await api.get_task(task_id=task.id)
            print(f"  Task: {task.title} - {full_details}")

    test_task = await api.get_task(12)

    # await test_task.set_priority(3)
    await test_task.set_color("ffff00")
    await test_task.set_progress(40)
    await test_task.set_due_date(datetime.datetime.now() + datetime.timedelta(days=4))
    await test_task.set_end_date(datetime.datetime.now() + datetime.timedelta(weeks=52))
    await test_task.set_start_date(datetime.datetime.now() - datetime.timedelta(weeks=1))
    await test_task.set_is_favorite(True)
    await test_task.set_priority(Priority.DO_IT_NOW)
    await test_task.set_repeating_interval(datetime.timedelta(days=4), mode=RepeatMode.FROM_CURRENT_DATE)


# Usage example
if __name__ == "__main__":
    asyncio.run(main())
