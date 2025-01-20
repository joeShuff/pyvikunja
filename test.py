import asyncio
import os

from api import VikunjaAPI

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
    await test_task.mark_done()

    # Get all labels
    labels = await api.get_labels()
    for label in labels:
        print(f"Label: {label.title}")

    # Get all teams
    teams = await api.get_teams()
    for team in teams:
        print(f"Team: {team.name}")

# Usage example
if __name__ == "__main__":
    asyncio.run(main())
