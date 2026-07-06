#!/usr/bin/env python3
"""
Manual integration test for pyvikunja label and bucket APIs against a live Vikunja instance.

Usage:
    uv venv && uv pip install -e .
    uv run python scripts/integration_test.py --base-url https://your-vikunja-host
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import logging
import os
import sys
import unicodedata
from typing import Awaitable, Callable, Dict, List, Optional, Sequence, TypeVar

import httpx

from pyvikunja.api import APIError, VikunjaAPI
from pyvikunja.models.label import Label
from pyvikunja.models.project import Project
from pyvikunja.models.project_view import ProjectView
from pyvikunja.models.task import Task

T = TypeVar("T")

DEFAULT_BASE_URL = "https://changeme.test.home"
DEFAULT_PROJECT_TITLE = "test"
TARGET_BUCKET_TITLE = "To-Do"

# Set by run_step() when a step fails
FAILED_STEP: Optional[str] = None


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")
    for name in ("httpx", "httpcore", "hpack"):
        logging.getLogger(name).setLevel(level)


def section(title: str) -> None:
    print(f"\n{'─' * 72}\n  {title}\n{'─' * 72}")


def ok(message: str) -> None:
    print(f"  ✓ {message}")


def fail(message: str) -> None:
    print(f"  ✗ {message}")


def info(message: str) -> None:
    print(f"    {message}")


def warn(message: str) -> None:
    print(f"  ! {message}")


def normalize_bucket_title(title: str) -> str:
    return unicodedata.normalize("NFKC", title).strip().casefold()


def label_ids(labels: Sequence[Label]) -> List[int]:
    return sorted(label.id for label in labels if label.id is not None)


def format_labels(labels: Sequence[Label]) -> str:
    if not labels:
        return "—"
    return ", ".join(f"{label.id}:{label.title}" for label in labels)


def bucket_title(bucket_map: Dict[int, str], bucket_id: Optional[int]) -> str:
    if bucket_id is None:
        return "—"
    return bucket_map.get(bucket_id, f"?id={bucket_id}")


def truncate_cell(text: str, max_len: int) -> str:
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def prompt_yes(prompt: str, default_no: bool = True) -> bool:
    suffix = " [y/N]: " if default_no else " [Y/n]: "
    answer = input(prompt + suffix).strip().lower()
    if not answer:
        return not default_no
    return answer in ("y", "yes")


async def run_step(step_id: str, description: str, action: Callable[[], Awaitable[T]]) -> T:
    global FAILED_STEP
    print(f"\n  ▶ {step_id}: {description}")
    try:
        result = await action()
        ok(f"{step_id} completed")
        return result
    except APIError as exc:
        FAILED_STEP = step_id
        fail(f"{step_id} failed — HTTP {exc.status_code}")
        info(f"message: {exc.message}")
        _print_api_error_body(exc.message)
        raise
    except Exception:
        FAILED_STEP = step_id
        fail(f"{step_id} failed — unexpected error")
        raise


def _print_api_error_body(message: str) -> None:
    try:
        body = json.loads(message.replace("HTTP error: ", "", 1))
        if isinstance(body, dict):
            for key in ("code", "message"):
                if key in body:
                    info(f"{key}: {body[key]}")
    except (json.JSONDecodeError, TypeError):
        pass


def print_discovery_summary(
    base_url: str,
    project: Project,
    tasks: List[Task],
    task_bucket_map: Dict[int, int],
    bucket_map: Dict[int, str],
    kanban_view: Optional[ProjectView],
    account_labels: List[Label],
) -> None:
    section("Discovery summary")
    info(f"Base URL:     {base_url}")
    info(f"Project:      {project.title!r} (id={project.id})")
    if project.id != 1:
        warn(f"project id is {project.id}, not 1")
    if kanban_view:
        info(f"Kanban view:  {kanban_view.title!r} (id={kanban_view.id})")
    else:
        warn("no kanban view — bucket tests unavailable")

    print()
    print(f"  {'Idx':<4} {'TaskId':<8} {'Title':<34} {'Bucket':<14} {'Labels'}")
    print(f"  {'-'*4} {'-'*8} {'-'*34} {'-'*14} {'-'*30}")
    for index, task in enumerate(tasks):
        bid = task_bucket_map.get(task.id, task.bucket_id)
        bucket_cell = bucket_title(bucket_map, bid)
        title_cell = truncate_cell(task.title, 34)
        print(
            f"  {index:<4} {task.id:<8} {title_cell:<34} {bucket_cell:<14} "
            f"{format_labels(task.labels)}"
        )

    print()
    info(f"Account labels ({len(account_labels)}): " + ", ".join(
        f"{label.id}:{label.title}" for label in account_labels[:15]
    ) + (" …" if len(account_labels) > 15 else ""))

    if bucket_map:
        print()
        info("Kanban buckets:")
        for bid, title in sorted(bucket_map.items(), key=lambda item: normalize_bucket_title(item[1])):
            display = repr(title) if title != title.strip() else title
            info(f"  {bid:>4}  {display}")


async def get_kanban_bucket_id(
    api: VikunjaAPI,
    project_id: int,
    kanban_view: ProjectView,
    task_id: int,
) -> Optional[int]:
    """Bucket column for a task from the kanban view (authoritative for placement)."""
    kanban_map = await api.get_kanban_task_bucket_map(project_id, kanban_view.id)
    return kanban_map.get(task_id)


async def resolve_task_bucket_id(
    api: VikunjaAPI,
    project_id: int,
    kanban_view: Optional[ProjectView],
    task_id: int,
    task_bucket_map: Optional[Dict[int, int]] = None,
) -> Optional[int]:
    """
    Resolve bucket_id for display/snapshot.

    Uses the kanban task→bucket map only. GET /tasks/{id} often omits bucket_id on Vikunja,
    so it is not used here.
    """
    if task_bucket_map is not None and task_id in task_bucket_map:
        return task_bucket_map[task_id]

    if kanban_view is not None:
        bucket_id = await get_kanban_bucket_id(api, project_id, kanban_view, task_id)
        if bucket_id is not None:
            return bucket_id

    for expanded_task in await api.get_tasks(project_id, expand="buckets"):
        if expanded_task.id != task_id:
            continue
        for bucket in expanded_task.buckets:
            if bucket.id is not None:
                return bucket.id

    return None


async def assert_bucket_placement(
    api: VikunjaAPI,
    project_id: int,
    kanban_view: ProjectView,
    task_id: int,
    expected_bucket_id: int,
    bucket_map: Dict[int, str],
    context: str,
) -> None:
    kanban_bucket_id = await get_kanban_bucket_id(api, project_id, kanban_view, task_id)
    if kanban_bucket_id != expected_bucket_id:
        fail(
            f"{context}: expected bucket {expected_bucket_id} "
            f"({bucket_title(bucket_map, expected_bucket_id)}), "
            f"kanban_map={kanban_bucket_id}"
        )
        raise RuntimeError(f"{context}: bucket verification failed")

    ok(
        f"{context}: bucket {expected_bucket_id} "
        f"({bucket_title(bucket_map, expected_bucket_id)}) per kanban map"
    )


async def discover(
    api: VikunjaAPI,
    base_url: str,
    project_title: str,
) -> tuple[
    Project,
    List[Task],
    Dict[int, int],
    Dict[int, str],
    Optional[ProjectView],
    List[Label],
]:
    section("Discovery")

    await run_step("D0", "ping API", api.ping)

    projects = await run_step("D1", "list projects", api.get_projects)
    project = next(
        (p for p in projects if p.title.strip().lower() == project_title.strip().lower()),
        None,
    )
    if project is None:
        info("Available projects:")
        for p in projects:
            info(f"  id={p.id}  {p.title!r}")
        raise RuntimeError(f"Project {project_title!r} not found")
    ok(f"matched project {project.title!r} (id={project.id})")

    project = await run_step("D2", f"load project {project.id}", lambda: api.get_project(project.id))

    tasks = await run_step("D3", f"list tasks in project {project.id}", lambda: api.get_tasks(project.id))
    if not tasks:
        raise RuntimeError(f"No tasks in project {project.title!r}")

    kanban_view = project.get_default_kanban_view()
    bucket_map: Dict[int, str] = {}
    task_bucket_map: Dict[int, int] = {}

    if kanban_view is not None:
        buckets = await run_step(
            "D4",
            f"list buckets for kanban view {kanban_view.id}",
            lambda: api.get_project_buckets(project.id, kanban_view.id),
        )
        bucket_map = {b.id: b.title for b in buckets if b.id is not None}
        task_bucket_map = await run_step(
            "D5",
            "build task→bucket map from kanban view",
            lambda: api.get_kanban_task_bucket_map(project.id, kanban_view.id),
        )
        if task_bucket_map:
            ok(f"kanban map has {len(task_bucket_map)} task(s) with bucket assignments")
        else:
            warn(
                "kanban view returned no task→bucket entries "
                "(tasks may only appear in list view, or board is empty)"
            )
    else:
        warn("no kanban view on project")

    print_discovery_summary(
        base_url, project, tasks, task_bucket_map, bucket_map, kanban_view,
        await api.get_labels(),
    )

    return project, tasks, task_bucket_map, bucket_map, kanban_view, await api.get_labels()


async def assert_label_ids(
    api: VikunjaAPI,
    task_id: int,
    expected: List[int],
    step: str,
) -> Task:
    task = await api.get_task(task_id)
    api_labels = await api.get_task_labels(task_id)
    expected_sorted = sorted(expected)
    actual_task = label_ids(task.labels)
    actual_api = label_ids(api_labels)
    if actual_task != expected_sorted or actual_api != expected_sorted:
        fail(
            f"{step} verify: expected {expected_sorted}, "
            f"task.labels={actual_task}, get_task_labels={actual_api}"
        )
        raise RuntimeError(f"{step} verification failed")
    info(f"labels now: {format_labels(api_labels)}")
    return task


def pick_test_labels(
    account_labels: List[Label],
    exclude: List[int],
    count: int = 2,
) -> List[int]:
    exclude_set = set(exclude)
    candidates = [label.id for label in account_labels if label.id not in exclude_set]
    if len(candidates) < count:
        raise RuntimeError(
            f"Need {count} account labels not on the task; only {len(candidates)} available."
        )
    return candidates[:count]


async def run_label_tests(
    api: VikunjaAPI,
    task: Task,
    account_labels: List[Label],
    initial_label_ids: List[int],
    auto_yes: bool,
) -> None:
    section("Label mutation tests")

    label_a, label_b = pick_test_labels(account_labels, initial_label_ids, 2)
    info(f"test labels: A={label_a}, B={label_b}")

    if not auto_yes and not prompt_yes("Run label mutation tests?"):
        warn("skipping label mutations")
        return

    async def l1():
        await task.set_labels([])
        return await assert_label_ids(api, task.id, [], "L1")

    if auto_yes or prompt_yes("L1: clear all labels on task?"):
        task = await run_step("L1", "clear labels (set_labels [])", l1)

    async def l2():
        await api.add_task_label(task.id, label_a)
        return await assert_label_ids(api, task.id, [label_a], "L2")

    if auto_yes or prompt_yes(f"L2: add label A (id={label_a}) via API?"):
        task = await run_step("L2", f"add_task_label({label_a})", l2)

    async def l3():
        await task.add_label(label_b)
        return await assert_label_ids(api, task.id, [label_a, label_b], "L3")

    if auto_yes or prompt_yes(f"L3: add label B (id={label_b}) via task.add_label?"):
        task = await run_step("L3", f"task.add_label({label_b})", l3)

    async def l4():
        await task.remove_label(label_a)
        return await assert_label_ids(api, task.id, [label_b], "L4")

    if auto_yes or prompt_yes(f"L4: remove label A (id={label_a})?"):
        task = await run_step("L4", f"remove_label({label_a})", l4)

    async def l5():
        await api.set_task_labels(task.id, [label_a, label_b])
        return await assert_label_ids(api, task.id, [label_a, label_b], "L5")

    if auto_yes or prompt_yes("L5: bulk replace with labels A+B?"):
        task = await run_step("L5", "set_task_labels bulk [A, B]", l5)

    async def l6():
        await task.set_labels([])
        return await assert_label_ids(api, task.id, [], "L6")

    if auto_yes or prompt_yes("L6: clear all labels again?"):
        await run_step("L6", "clear labels again", l6)


async def restore_labels(
    api: VikunjaAPI,
    task: Task,
    initial_label_ids: List[int],
    auto_yes: bool,
) -> None:
    section("Restore labels")
    if not auto_yes and not prompt_yes(f"Restore labels to {initial_label_ids or '[]'}?"):
        warn("skipped label restore")
        return

    async def action():
        await task.set_labels(initial_label_ids)
        return await assert_label_ids(api, task.id, initial_label_ids, "restore")

    await run_step("R-L", f"restore labels {initial_label_ids or '[]'}", action)


async def run_bucket_tests(
    api: VikunjaAPI,
    project: Project,
    task: Task,
    bucket_map: Dict[int, str],
    kanban_view: ProjectView,
    target_bucket_title: str,
    auto_yes: bool,
) -> Optional[int]:
    section("Bucket mutation tests")

    backlog_id = next(
        (
            bid for bid, title in bucket_map.items()
            if normalize_bucket_title(title) == normalize_bucket_title(target_bucket_title)
        ),
        None,
    )
    if backlog_id is None:
        raise RuntimeError(
            f"Bucket {target_bucket_title!r} not found. Available: {list(bucket_map.values())}"
        )
    ok(f"target {target_bucket_title!r} → bucket id {backlog_id}")

    kanban_before = await get_kanban_bucket_id(api, project.id, kanban_view, task.id)
    info(f"before: {bucket_title(bucket_map, kanban_before)} (kanban map id={kanban_before})")

    if not auto_yes and not prompt_yes(f"Move task {task.id} to {target_bucket_title!r} (id={backlog_id})?"):
        warn("skipped bucket move")
        return None

    async def move():
        await task.set_bucket(backlog_id)
        kanban_after = await get_kanban_bucket_id(api, project.id, kanban_view, task.id)
        if kanban_after != backlog_id:
            info("set_bucket not reflected on kanban map yet; trying move_task_to_bucket")
            await api.move_task_to_bucket(
                project.id, kanban_view.id, backlog_id, task.id
            )
        await assert_bucket_placement(
            api,
            project.id,
            kanban_view,
            task.id,
            backlog_id,
            bucket_map,
            "after move",
        )

    await run_step("B1", f"move to {target_bucket_title!r}", move)
    return backlog_id


async def restore_bucket(
    api: VikunjaAPI,
    project: Project,
    task: Task,
    kanban_view: ProjectView,
    initial_bucket_id: Optional[int],
    bucket_map: Dict[int, str],
    moved_to_backlog: bool,
    auto_yes: bool,
) -> None:
    section("Restore bucket")

    if initial_bucket_id is None:
        if moved_to_backlog:
            warn(
                "task had no bucket before tests but was moved to Backlog — "
                "not auto-restoring (use Vikunja UI or --no-restore was not set)"
            )
        else:
            info("initial bucket was unset — nothing to restore")
        return

    kanban_current = await get_kanban_bucket_id(api, project.id, kanban_view, task.id)
    if kanban_current == initial_bucket_id:
        ok("bucket already at initial value (per kanban map)")
        return

    if not auto_yes and not prompt_yes(
        f"Restore bucket to id={initial_bucket_id} ({bucket_title(bucket_map, initial_bucket_id)})?"
    ):
        warn("skipped bucket restore")
        return

    async def action():
        await task.set_bucket(initial_bucket_id)
        kanban_after = await get_kanban_bucket_id(api, project.id, kanban_view, task.id)
        if kanban_after != initial_bucket_id:
            info("set_bucket not reflected on kanban map yet; trying move_task_to_bucket")
            await api.move_task_to_bucket(
                project.id, kanban_view.id, initial_bucket_id, task.id
            )
        await assert_bucket_placement(
            api,
            project.id,
            kanban_view,
            task.id,
            initial_bucket_id,
            bucket_map,
            "after restore",
        )

    await run_step(
        "R-B",
        f"restore bucket to {initial_bucket_id}",
        action,
    )


def pick_task_index(tasks: List[Task]) -> int:
    while True:
        raw = input("\nTask index from table above: ").strip()
        if not raw.isdigit():
            print("    Enter a non-negative integer.")
            continue
        index = int(raw)
        if 0 <= index < len(tasks):
            return index
        print(f"    Index must be 0–{len(tasks) - 1}.")


async def main_async(args: argparse.Namespace) -> int:
    configure_logging(args.verbose)
    global FAILED_STEP

    print(f"\n  pyvikunja integration test")
    print(f"  Target: {args.base_url}\n")

    token = os.environ.get("VIKUNJA_TOKEN") or getpass.getpass("Vikunja API token: ").strip()
    if not token:
        print("No token provided.", file=sys.stderr)
        return 1

    api = VikunjaAPI(args.base_url, token, strict_ssl=args.strict_ssl)

    try:
        project, tasks, task_bucket_map, bucket_map, kanban_view, account_labels = await discover(
            api, args.base_url, args.project
        )

        if args.discovery_only:
            print("\n  Discovery only — exiting.\n")
            return 0

        task_index = pick_task_index(tasks)
        selected = tasks[task_index]
        task = await api.get_task(selected.id)
        ok(f"selected [{task_index}] task_id={task.id} title={task.title!r}")

        resolved_bucket = await resolve_task_bucket_id(
            api, project.id, kanban_view, task.id, task_bucket_map
        )
        section("Selected task detail")
        info(f"task_id:        {task.id}")
        info(f"title:          {task.title!r}")
        info(f"project_id:     {task.project_id}")
        info(
            f"bucket (kanban): {resolved_bucket} "
            f"({bucket_title(bucket_map, resolved_bucket)}) — used for bucket tests"
        )
        if task.bucket_id is not None and task.bucket_id != resolved_bucket:
            warn(f"get_task.bucket_id={task.bucket_id} differs from kanban map (ignored)")
        info(f"labels (embedded):      {format_labels(task.labels)}")
        task_labels = await api.get_task_labels(task.id)
        info(f"get_task_labels:        {format_labels(task_labels)}")

        if resolved_bucket is None and kanban_view is not None:
            warn("task not found in kanban map — bucket move/restore may not apply")

        auto_yes = args.yes
        if not auto_yes and not prompt_yes(
            f"Proceed with mutations on task {task.id} ({task.title!r})?"
        ):
            print("Aborted.")
            return 0

        initial_label_ids = label_ids(await api.get_task_labels(task.id))
        initial_bucket_id = resolved_bucket
        section("Snapshot")
        info(f"labels:  {initial_label_ids or '[]'}")
        info(f"bucket:  {initial_bucket_id} ({bucket_title(bucket_map, initial_bucket_id)})")

        task = await api.get_task(task.id)
        moved_to_backlog = False

        try:
            await run_label_tests(api, task, account_labels, initial_label_ids, auto_yes)
            task = await api.get_task(task.id)

            if kanban_view is not None and bucket_map:
                if auto_yes or prompt_yes("Run bucket mutation tests?"):
                    moved = await run_bucket_tests(
                        api, project, task, bucket_map, kanban_view, args.bucket, auto_yes
                    )
                    moved_to_backlog = moved is not None
                else:
                    warn("bucket tests skipped by user")
            else:
                warn("bucket tests skipped (no kanban view or no buckets)")

        finally:
            if not args.no_restore:
                task = await api.get_task(task.id)
                await restore_labels(api, task, initial_label_ids, auto_yes)
                if kanban_view is not None and bucket_map:
                    await restore_bucket(
                        api,
                        project,
                        task,
                        kanban_view,
                        initial_bucket_id,
                        bucket_map,
                        moved_to_backlog,
                        auto_yes,
                    )
            else:
                warn("--no-restore: task may differ from snapshot")

        section("Done")
        ok("integration run finished")
        return 0

    except httpx.ConnectError as exc:
        print("\n  Connection failed — could not reach the Vikunja host.\n", file=sys.stderr)
        print(f"  URL: {args.base_url}", file=sys.stderr)
        print(f"  Error: {exc}\n", file=sys.stderr)
        print("  Typical causes:", file=sys.stderr)
        print("    • DNS cannot resolve the hostname (wrong or internal-only host)", file=sys.stderr)
        print("    • Instance is down or blocked from this network\n", file=sys.stderr)
        print("  Try:", file=sys.stderr)
        print('    uv run python scripts/integration_test.py --base-url "https://your-host.example"\n', file=sys.stderr)
        if FAILED_STEP:
            print(f"  Last step: {FAILED_STEP}", file=sys.stderr)
        return 1
    except APIError:
        print(f"\n  Stopped at step: {FAILED_STEP or 'unknown'}\n", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"\n  {exc}", file=sys.stderr)
        if FAILED_STEP:
            print(f"  Last step: {FAILED_STEP}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n  Interrupted.", file=sys.stderr)
        if FAILED_STEP:
            print(f"  Last step: {FAILED_STEP}", file=sys.stderr)
        return 1
    finally:
        await api.client.aclose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="pyvikunja live integration test")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Vikunja instance URL")
    parser.add_argument("--project", default=DEFAULT_PROJECT_TITLE, help="Project title to find")
    parser.add_argument("--bucket", default=TARGET_BUCKET_TITLE, help="Target bucket title for move test")
    parser.add_argument("--yes", action="store_true", help="Auto-confirm all prompts")
    parser.add_argument("--verbose", action="store_true", help="Show httpx request logs")
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
    sys.exit(asyncio.run(main_async(parse_args())))


if __name__ == "__main__":
    main()
