#!/usr/bin/env python3
"""
Manual integration test for pyvikunja label and bucket APIs against a live Vikunja instance.

Usage:
    uv pip install -e .   # from repo root, once
    uv run python scripts/integration_test.py

You will be prompted for an API token (input is hidden).
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys
from typing import Dict, List, Optional, Sequence

from pyvikunja.api import APIError, VikunjaAPI
from pyvikunja.models.bucket import Bucket
from pyvikunja.models.label import Label
from pyvikunja.models.project import Project
from pyvikunja.models.project_view import ProjectView
from pyvikunja.models.task import Task

DEFAULT_BASE_URL = "https://test.solroshus.com"
DEFAULT_PROJECT_TITLE = "Finances"
TARGET_BUCKET_TITLE = "Backlog"


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def ok(message: str) -> None:
    print(f"  PASS: {message}")


def fail(message: str) -> None:
    print(f"  FAIL: {message}")


def info(message: str) -> None:
    print(f"  {message}")


def label_ids(labels: Sequence[Label]) -> List[int]:
    return sorted(label.id for label in labels if label.id is not None)


def format_labels(labels: Sequence[Label]) -> str:
    if not labels:
        return "(none)"
    return ", ".join(f"{label.id}:{label.title}" for label in labels)


def bucket_title(bucket_map: Dict[int, str], bucket_id: Optional[int]) -> str:
    if bucket_id is None:
        return "(none)"
    return bucket_map.get(bucket_id, f"unknown id {bucket_id}")


async def assert_label_ids(
    api: VikunjaAPI,
    task_id: int,
    expected: List[int],
    step: str,
) -> Task:
    task = await api.get_task(task_id)
    api_labels = await api.get_task_labels(task_id)
    actual_task = label_ids(task.labels)
    actual_api = label_ids(api_labels)
    expected_sorted = sorted(expected)
    if actual_task != expected_sorted or actual_api != expected_sorted:
        fail(
            f"{step}: expected label ids {expected_sorted}, "
            f"task.labels={actual_task}, get_task_labels={actual_api}"
        )
        raise RuntimeError(step)
    ok(f"{step}: labels are {expected_sorted or '[]'}")
    return task


async def discover(
    api: VikunjaAPI,
    project_title: str,
) -> tuple[Project, Task, List[Label], Dict[int, str], Optional[ProjectView], Dict[int, str]]:
    section("Discovery")

    if not await api.ping():
        raise RuntimeError("ping failed")
    ok("ping")

    projects = await api.get_projects()
    project = next(
        (p for p in projects if p.title.strip().lower() == project_title.strip().lower()),
        None,
    )
    if project is None:
        info("Available projects:")
        for p in projects:
            info(f"  id={p.id} title={p.title!r}")
        raise RuntimeError(f"Project {project_title!r} not found")

    ok(f"found project {project.title!r} (id={project.id})")
    if project.id != 1:
        info(f"note: project id is {project.id}, not 1")

    project = await api.get_project(project.id)
    if not project.views:
        info("project.views empty on get_project; views may be unavailable")

    tasks = await api.get_tasks(project.id)
    if not tasks:
        raise RuntimeError(f"No tasks in project {project.title!r}")

    info("Tasks in project (pick by index):")
    for index, task in enumerate(tasks):
        labels_on_task = format_labels(task.labels)
        bucket = task.bucket_id if task.bucket_id is not None else "—"
        info(f"  [{index}] task_id={task.id} title={task.title!r} bucket_id={bucket} labels={labels_on_task}")

    while True:
        raw = input("\nTask index to use for tests: ").strip()
        if not raw.isdigit():
            print("Enter a non-negative integer index.")
            continue
        index = int(raw)
        if 0 <= index < len(tasks):
            break
        print(f"Index must be between 0 and {len(tasks) - 1}.")

    task = await api.get_task(tasks[index].id)
    ok(f"selected task id={task.id} title={task.title!r} project_id={task.project_id}")

    account_labels = await api.get_labels()
    ok(f"account has {len(account_labels)} label(s)")
    for label in account_labels[:20]:
        info(f"  label id={label.id} title={label.title!r}")
    if len(account_labels) > 20:
        info(f"  ... and {len(account_labels) - 20} more")

    task_labels_api = await api.get_task_labels(task.id)
    info(f"get_task_labels: {format_labels(task_labels_api)}")
    info(f"task.labels (embedded): {format_labels(task.labels)}")

    bucket_map: Dict[int, str] = {}
    kanban_view: Optional[ProjectView] = None
    if hasattr(api, "get_project_buckets"):
        kanban_view = project.get_default_kanban_view()
        if kanban_view is None:
            info("no kanban view on project — bucket tests will be skipped")
        else:
            ok(f"kanban view id={kanban_view.id} title={kanban_view.title!r}")
            buckets = await api.get_project_buckets(project.id, kanban_view.id)
            bucket_map = {b.id: b.title for b in buckets if b.id is not None}
            info("buckets:")
            for bid, title in sorted(bucket_map.items(), key=lambda item: item[1].lower()):
                info(f"  id={bid} title={title!r}")
            info(
                f"current bucket: id={task.bucket_id} "
                f"title={bucket_title(bucket_map, task.bucket_id)!r}"
            )
    else:
        info("get_project_buckets not available — install merged main with bucket support")

    return project, task, account_labels, bucket_map, kanban_view, {label.id: label.title for label in account_labels}


def pick_test_labels(
    account_labels: List[Label],
    exclude: List[int],
    count: int = 2,
) -> List[int]:
    exclude_set = set(exclude)
    candidates = [label.id for label in account_labels if label.id not in exclude_set]
    if len(candidates) < count:
        raise RuntimeError(
            f"Need at least {count} account labels not on the task; "
            f"only {len(candidates)} available."
        )
    return candidates[:count]


async def run_label_tests(
    api: VikunjaAPI,
    task: Task,
    account_labels: List[Label],
    initial_label_ids: List[int],
) -> None:
    section("Label tests")

    label_a, label_b = pick_test_labels(account_labels, initial_label_ids, 2)
    info(f"using test labels A={label_a} B={label_b}")

    # L1 — clear
    await task.set_labels([])
    task = await assert_label_ids(api, task.id, [], "L1 clear via task.set_labels")

    # L2 — add via API then task (idempotent on task.add_label)
    await api.add_task_label(task.id, label_a)
    await task.add_label(label_a)
    task = await assert_label_ids(api, task.id, [label_a], "L2 add label A")

    # L3 — add B via task.add_labels
    await task.add_labels([label_b])
    task = await assert_label_ids(api, task.id, [label_a, label_b], "L3 add label B")

    # L4 — remove A
    await task.remove_label(label_a)
    task = await assert_label_ids(api, task.id, [label_b], "L4 remove label A")

    # L5 — bulk replace
    await api.set_task_labels(task.id, [label_a, label_b])
    task = await assert_label_ids(api, task.id, [label_a, label_b], "L5 bulk replace A+B")

    # L6 — clear again
    await task.set_labels([])
    await assert_label_ids(api, task.id, [], "L6 clear again")


async def restore_labels(api: VikunjaAPI, task: Task, initial_label_ids: List[int]) -> None:
    section("Restore labels")
    await task.set_labels(initial_label_ids)
    await assert_label_ids(api, task.id, initial_label_ids, "restore labels")
    ok(f"restored labels to {sorted(initial_label_ids) or '[]'}")


async def run_bucket_tests(
    api: VikunjaAPI,
    project: Project,
    task: Task,
    bucket_map: Dict[int, str],
    kanban_view: ProjectView,
    target_bucket_title: str,
) -> None:
    section("Bucket tests")

    backlog_id = next(
        (bid for bid, title in bucket_map.items() if title.strip().lower() == target_bucket_title.lower()),
        None,
    )
    if backlog_id is None:
        raise RuntimeError(
            f"Bucket {target_bucket_title!r} not found. Available: {list(bucket_map.values())}"
        )
    ok(f"resolved {target_bucket_title!r} -> bucket id {backlog_id}")

    task = await api.get_task(task.id)
    info(
        f"before move: bucket_id={task.bucket_id} "
        f"title={bucket_title(bucket_map, task.bucket_id)!r}"
    )

    await task.set_bucket(backlog_id)
    task = await api.get_task(task.id)
    if task.bucket_id != backlog_id:
        info("set_bucket via task update did not stick; trying move_task_to_bucket")
        task = await api.move_task_to_bucket(
            project.id, kanban_view.id, backlog_id, task.id
        )

    if task.bucket_id != backlog_id:
        fail(f"bucket_id is {task.bucket_id}, expected {backlog_id}")
        raise RuntimeError("bucket move failed")

    ok(
        f"task is in bucket {backlog_id} "
        f"({bucket_title(bucket_map, task.bucket_id)!r})"
    )


async def restore_bucket(
    api: VikunjaAPI,
    project: Project,
    task: Task,
    kanban_view: ProjectView,
    initial_bucket_id: Optional[int],
    bucket_map: Dict[int, str],
) -> None:
    section("Restore bucket")
    task = await api.get_task(task.id)

    if initial_bucket_id is None:
        info("initial bucket was unset — leaving task in Backlog (no restore)")
        return

    if initial_bucket_id == task.bucket_id:
        ok("bucket unchanged, nothing to restore")
        return

    await task.set_bucket(initial_bucket_id)
    task = await api.get_task(task.id)
    if task.bucket_id != initial_bucket_id:
        task = await api.move_task_to_bucket(
            project.id, kanban_view.id, initial_bucket_id, task.id
        )

    if task.bucket_id != initial_bucket_id:
        fail(f"could not restore bucket to {initial_bucket_id}")
        raise RuntimeError("restore bucket failed")

    ok(
        f"restored bucket to id={initial_bucket_id} "
        f"({bucket_title(bucket_map, initial_bucket_id)!r})"
    )


async def main_async(args: argparse.Namespace) -> int:
    token = os.environ.get("VIKUNJA_TOKEN") or getpass.getpass("Vikunja API token: ").strip()
    if not token:
        print("No token provided.", file=sys.stderr)
        return 1

    api = VikunjaAPI(args.base_url, token, strict_ssl=args.strict_ssl)

    try:
        project, task, account_labels, bucket_map, kanban_view, _ = await discover(
            api, args.project
        )

        if args.discovery_only:
            print("\nDiscovery only — exiting.")
            return 0

        if not args.yes:
            confirm = input("\nProceed with label/bucket mutations on this task? [yes/N]: ").strip().lower()
            if confirm != "yes":
                print("Aborted.")
                return 0

        initial_label_ids = label_ids((await api.get_task_labels(task.id)))
        initial_bucket_id = (await api.get_task(task.id)).bucket_id
        info(f"snapshot labels={initial_label_ids} bucket_id={initial_bucket_id}")

        task = await api.get_task(task.id)

        try:
            await run_label_tests(api, task, account_labels, initial_label_ids)
            task = await api.get_task(task.id)

            if kanban_view is not None and bucket_map and hasattr(api, "get_project_buckets"):
                await run_bucket_tests(
                    api, project, task, bucket_map, kanban_view, args.bucket
                )
            else:
                info("skipping bucket tests")

        finally:
            if not args.no_restore:
                task = await api.get_task(task.id)
                await restore_labels(api, task, initial_label_ids)
                if kanban_view is not None and bucket_map:
                    await restore_bucket(
                        api, project, task, kanban_view, initial_bucket_id, bucket_map
                    )
            else:
                info("--no-restore: leaving task as-is")

        section("Done")
        ok("all integration steps completed")
        return 0

    except APIError as exc:
        print(f"\nAPI error {exc.status_code}: {exc.message}", file=sys.stderr)
        return 1
    except (RuntimeError, KeyboardInterrupt) as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 1
    finally:
        await api.client.aclose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="pyvikunja live integration test")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Vikunja instance URL")
    parser.add_argument("--project", default=DEFAULT_PROJECT_TITLE, help="Project title to find")
    parser.add_argument("--bucket", default=TARGET_BUCKET_TITLE, help="Target bucket title for move test")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--no-restore", action="store_true", help="Do not restore original labels/bucket")
    parser.add_argument("--discovery-only", action="store_true", help="Discovery phase only")
    parser.add_argument(
        "--strict-ssl",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Verify TLS certificates (default: true)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sys.exit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
